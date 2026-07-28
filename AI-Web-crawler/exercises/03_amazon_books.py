"""
从 Amazon 图书详情页提取书籍信息：https://www.amazon.com/dp/<ASIN>

需求（对照练习要求实现）：
    1. 随机延迟：每次请求之间等待一个随机时长，而不是固定的 sleep(1)，行为更接近真实用户
    2. 轮换 User-Agent：每次请求从多个 User-Agent 里随机选一个，
       降低被识别成"同一个脚本在批量访问"的概率
    3. 处理异常：单本书请求/解析失败不影响其他书
    4. 结果保存成 CSV

这份实现针对的是"图书详情页"（比如 https://www.amazon.com/dp/1954118813），
不是搜索结果列表页——如果你想抓的是搜索结果那种一页多本书的列表，
把那个页面的 HTML 参考贴给我，选择器需要重新对着写。

运行方式（建议在项目根目录执行，这样相对路径 DATA_PATH 才是对的）：
    python exercises/03_amazon_books.py
"""

import csv
import os
import random
import re
import time

import requests
from bs4 import BeautifulSoup

# 要抓取的书，用 ASIN（Amazon 给每个商品的唯一编号）标识。
# 详情页地址统一是 https://www.amazon.com/dp/<ASIN>
BOOK_ASINS = [
    "1954118813",  # The Calamity Club: A Novel
    # 在这里继续加你想抓的书的 ASIN ...
]

DATA_PATH = "data/amazon_books.csv"

# 轮换 User-Agent：每次请求都从这个池子里随机挑一个
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36 Edg/150.0.0.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:130.0) Gecko/20100101 Firefox/130.0",
]


def random_headers() -> dict:
    """每次调用都随机返回一组请求头（重点是随机 User-Agent）。"""
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Referer": "https://www.amazon.com/amz-books/store",
        "Accept-Language": "en-US,en;q=0.9",
    }


def fetch_book_page(asin: str) -> str | None:
    """请求某本书的详情页，返回 HTML 文本；请求失败则返回 None（不让程序崩溃）。"""
    url = f"https://www.amazon.com/dp/{asin}"
    try:
        response = requests.get(url, headers=random_headers(), timeout=10)
        response.raise_for_status()
    except requests.RequestException as exc:
        print(f"[警告] {asin} 请求失败：{exc}")
        return None
    return response.text


def _text_or_default(tag, default: str = "") -> str:
    """BeautifulSoup 里经常要先判断标签存不存在再取文字，这个小工具统一处理。"""
    return tag.get_text(strip=True) if tag else default


def extract_price(price_tag) -> str:
    """
    从 Amazon 的价格结构里提取纯数字价格（比如 "24.01"）。
    Amazon 页面里价格至少有三种写法，按优先级依次尝试：
        1. <span class="a-offscreen">$24.01</span>
           —— 专门给读屏器用的完整价格文字，最省事，但这个字段不一定有值
        2. a-price-whole + a-price-fraction 拼接，比如 "24" + "." + "01"
           —— 现价通常是这种被拆成整数/小数分别显示的结构
        3. 价格容器自己的纯文本，比如有些"划线原价"没有拆分成整数/小数，直接就是 "$35.00"
    """
    if price_tag is None:
        return ""

    offscreen = price_tag.select_one(".a-offscreen")
    if offscreen and offscreen.get_text(strip=True):
        return offscreen.get_text(strip=True).lstrip("$")

    whole = price_tag.select_one(".a-price-whole")
    if whole:
        fraction = price_tag.select_one(".a-price-fraction")
        whole_text = whole.get_text(strip=True).rstrip(".")
        fraction_text = fraction.get_text(strip=True) if fraction else "00"
        return f"{whole_text}.{fraction_text}"

    text = price_tag.get_text(strip=True)
    return text.lstrip("$") if text else ""


def parse_detail_bullets(soup: BeautifulSoup) -> dict:
    """
    解析"Product details"里的信息列表（出版社/页数/ISBN 等），结构大致是：

        <div id="detailBullets_feature_div">
            <ul class="detail-bullet-list">
                <li>
                    <span class="a-list-item">
                        <span class="a-text-bold">Publisher&rlm;:&lrm;</span>
                        <span>Spiegel & Grau</span>
                    </span>
                </li>
                ...
            </ul>
        </div>

    把 "Publisher" 这种标签文字当 key，后面 <span> 的文字当 value，整理成一个 dict，
    这样后面取值时可以直接写 bullets.get("Publisher", "")。
    """
    bullets = {}
    container = soup.select_one("#detailBullets_feature_div ul.detail-bullet-list")
    if not container:
        return bullets

    for item_span in container.select("li > span.a-list-item"):
        # 只处理"标签 + 值"这种正好两个 <span> 的情况；
        # "Best Sellers Rank" "Customer Reviews" 这两项结构不一样（值不是纯 <span>），
        # 这里用不到，直接跳过
        spans = item_span.find_all("span", recursive=False)
        if len(spans) < 2:
            continue

        # 标签文字里混了 U+200E / U+200F 这种从右到左书写标记（肉眼看不见）和冒号，
        # 用正则把这些和空白统一当分隔符去掉，只留下 "Publisher" 这样的纯文字
        key = re.sub(r"[\s‎‏:]+", " ", spans[0].get_text()).strip()
        value = spans[1].get_text(strip=True)
        bullets[key] = value

    return bullets


def parse_book_page(html: str, asin: str) -> dict:
    """把一本书详情页的 HTML 解析成一个 dict。"""
    soup = BeautifulSoup(html, "html.parser")

    title = _text_or_default(soup.select_one("#productTitle"))

    author = _text_or_default(soup.select_one("#bylineInfo .author a"))

    # "Format: Hardcover" 这种文字前面还有作者名，直接按整段文字用正则找 "Format:" 更稳
    byline = soup.select_one("#bylineInfo")
    byline_text = byline.get_text(" ", strip=True) if byline else ""
    format_match = re.search(r"Format:\s*([A-Za-z ]+)", byline_text)
    book_format = format_match.group(1).strip() if format_match else ""

    # 评分数字在 title 属性里，形如 "4.7 out of 5 stars"，用正则只取数字部分
    rating_tag = soup.select_one("#acrPopover")
    rating_match = re.search(r"[\d.]+", rating_tag.get("title", "")) if rating_tag else None
    rating = rating_match.group() if rating_match else ""

    # 评价数在 aria-label 里，形如 "32,889 Reviews"，同样用正则取数字，再去掉千分位逗号
    review_tag = soup.select_one("#acrCustomerReviewText")
    review_match = re.search(r"[\d,]+", review_tag.get("aria-label", "")) if review_tag else None
    review_count = review_match.group().replace(",", "") if review_match else ""

    price_container = soup.select_one("#corePriceDisplay_desktop_feature_div .priceToPay")
    price = extract_price(price_container)

    list_price_container = soup.select_one("#corePriceDisplay_desktop_feature_div .basisPrice .a-price")
    list_price = extract_price(list_price_container)

    bullets = parse_detail_bullets(soup)

    return {
        "asin": asin,
        "title": title,
        "author": author,
        "format": book_format,
        "rating": rating,
        "review_count": review_count,
        "price": price,
        "list_price": list_price,
        "publisher": bullets.get("Publisher", ""),
        "publication_date": bullets.get("Publication date", ""),
        "language": bullets.get("Language", ""),
        "print_length": bullets.get("Print length", ""),
        "isbn_10": bullets.get("ISBN-10", ""),
        "isbn_13": bullets.get("ISBN-13", ""),
        "item_weight": bullets.get("Item Weight", ""),
        "dimensions": bullets.get("Dimensions", ""),
    }


def scrape_books(asins: list[str]) -> list[dict]:
    """依次抓取每本书，返回解析结果列表。"""
    books = []
    for asin in asins:
        html = fetch_book_page(asin)
        if html is not None:
            try:
                books.append(parse_book_page(html, asin))
            except (AttributeError, IndexError, TypeError) as exc:
                # Amazon 页面结构复杂，某本书解析出错不该让整个程序崩溃，跳过并打印警告
                print(f"[警告] {asin} 解析失败，已跳过：{exc}")

        # 随机延迟 1~3 秒，而不是固定 sleep(1)，行为更接近真实用户，也不那么容易被限流
        time.sleep(random.uniform(1, 3))

    return books


def save_to_csv(books: list[dict], path: str) -> None:
    """把书籍列表保存为 CSV 文件。"""
    if not books:
        print("没有抓到任何数据，不写入文件。")
        return

    os.makedirs(os.path.dirname(path), exist_ok=True)

    # encoding="utf-8-sig" 带 BOM 头，用 Excel 直接打开这个 CSV 时中文不会变成乱码
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=list(books[0].keys()))
        writer.writeheader()
        writer.writerows(books)


if __name__ == "__main__":
    books = scrape_books(BOOK_ASINS)
    save_to_csv(books, DATA_PATH)
    print(f"共抓取 {len(books)} 本书，已保存到 {DATA_PATH}")
