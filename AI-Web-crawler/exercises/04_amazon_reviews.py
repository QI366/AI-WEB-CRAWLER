"""
抓取亚马逊商品评论

需求（对照练习要求实现）：
    1. 分页抓取评论，直到没有下一页或达到 MAX_PAGES 上限
    2. 控制请求速率：页与页之间随机延迟，sleep 是下限不是上限
       （被限流时会自动把延迟拉长，也就是"退避"）
    3. 关注状态码：出现 503 / 429、人机验证页、或被重定向到登录页时，
       说明当前速率或 IP 已经不够用，重试几次仍然不行就停下来，而不是继续硬爬
    4. 从每个评论区块提取：评论者姓名 / 评分 / 标题 / 正文 / 日期
    5. 结果保存成 data/amazon_reviews.csv

两个数据源（脚本会自动选）：
    A. 商品详情页 https://www.amazon.com/dp/<ASIN>
       匿名就能访问，页面里内嵌了最靠前的十几条评论。默认走这条路。
    B. 全部评论页 https://www.amazon.com/product-reviews/<ASIN>?pageNumber=N
       能翻页拿到全部评论，但 2024 年之后 Amazon 要求登录：
       匿名请求会被 302 到 /ap/signin 登录页（状态码仍然是 200，所以必须看最终 URL）。
       想走这条路，把你浏览器里已登录的 Cookie 放到项目根目录的 .env：

           AMAZON_COOKIE="session-id=...; ubid-main=...; x-main=...; at-main=..."

       检测到这个变量时脚本会自动改用全部评论页并开始翻页。
       .env 不要提交到 git，避免会话信息泄露。

关于选择器：
    练习里给的 data-hook 是老版页面的（review-title / review-body），
    现在的详情页换成了 reviewTitle / reviewText，两套都写上了，哪套在就用哪套。

运行方式：
    python exercises/04_amazon_reviews.py
"""

import csv
import json
import os
import random
import re
import time

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

# 读取项目根目录的 .env（如果有的话），这样 AMAZON_COOKIE 才能被 os.getenv 拿到
load_dotenv()

# 要抓的商品，用 ASIN（Amazon 给每个商品的唯一编号）标识。
ASIN = "B096VP4L1W"

DETAIL_URL = f"https://www.amazon.com/dp/{ASIN}"
REVIEWS_URL = f"https://www.amazon.com/product-reviews/{ASIN}"
# 新版「全部评论」页，就是详情页上 "See more reviews" 按钮指向的地址
PORTAL_URL = f"https://www.amazon.com/portal/customer-reviews/{ASIN}/ref=cm_cr_dp_d_show_all_top"
# 「加载更多评论」按钮背后的 AJAX 接口（抓包抓到的那个 POST，见文件末尾的请求头参考）
AJAX_URL = "https://www.amazon.com/portal/customer-reviews/ajax/request-more-reviews/submit/ref=cm_cr_arp_d_rvw_sm"

# 用一个 Session 发所有请求：Amazon 会在第一次访问时下发 session-id 之类的 Cookie，
# 后续请求带着它更像正常浏览行为（每次都新开连接、不带任何 Cookie 反而可疑）。
SESSION = requests.Session()

DATA_PATH = "data/amazon_reviews.csv"

# 最多翻多少页。Amazon 一页 10 条评论，10 页就是 100 条，
# 先设一个上限，避免脚本不小心一直跑下去。
MAX_PAGES = 10

# 每页之间的随机延迟区间（秒）。注意这是"下限不是上限"：
# 一旦被限流，等待时间会在 polite_sleep 里被退避倍数放大。
MIN_DELAY, MAX_DELAY = 3.0, 6.0

# 同一页最多请求几次（遇到 503 / 429 / 验证页时会退避后重试）
MAX_RETRIES = 3

# 轮换 User-Agent：每次请求都从这个池子里随机挑一个，
# 降低被识别成"同一个脚本在批量访问"的概率
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36 Edg/150.0.0.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:130.0) Gecko/20100101 Firefox/130.0",
]

# Amazon 的人机验证页里一定会出现的特征文字，用来判断"这页不是评论，是验证码"。
# 注意验证页的状态码常常还是 200，光看 status_code 是发现不了的。
CHALLENGE_MARKERS = [
    "api-services-support@amazon.com",  # 验证页底部的联系邮箱
    "Enter the characters you see below",
    "Type the characters you see in this image",
    "To discuss automated access to Amazon data",
]


def random_headers() -> dict:
    """每次调用都随机返回一组请求头（重点是随机 User-Agent）。"""
    headers = {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": DETAIL_URL,
    }

    # Cookie 只从环境变量 / .env 读取，绝不写死在代码里（写死一旦提交 git 就泄露了）
    cookie = os.getenv("AMAZON_COOKIE")
    if cookie:
        headers["Cookie"] = cookie

    return headers


def polite_sleep(backoff: int = 0) -> None:
    """
    请求之间的延迟。基础是 MIN_DELAY~MAX_DELAY 的随机值，
    backoff 每加 1 等待时间翻一倍（1、2、4 倍……），也就是被限流时越等越久。
    """
    delay = random.uniform(MIN_DELAY, MAX_DELAY) * (2**backoff)
    time.sleep(delay)


def looks_like_challenge(html: str) -> bool:
    """判断返回的是不是人机验证页（状态码可能还是 200，所以必须看内容）。"""
    head = html[:4000]  # 特征文字都在页面靠前的位置，不用扫全文
    return any(marker in head for marker in CHALLENGE_MARKERS)


def fetch(url: str, params: dict | None = None, label: str = "") -> str | None:
    """
    发一次请求并把各种"没拿到正常页面"的情况区分开：

        • 网络异常 / 503 / 429 / 403 —— 退避后重试
        • 200 但内容是人机验证页 —— 同样按被拦截处理，退避后重试
        • 被重定向到 /ap/signin —— 需要登录，重试再多次也没用，直接放弃
        • 其他 4xx / 5xx —— 直接放弃这一页

    重试都失败则返回 None，由调用方决定要不要停下来。
    """
    for attempt in range(MAX_RETRIES):
        try:
            response = SESSION.get(url, headers=random_headers(), params=params, timeout=15)
        except requests.RequestException as exc:
            print(f"[警告] {label} 请求失败：{exc}")
            polite_sleep(backoff=attempt + 1)
            continue

        # requests 默认会跟随 302，所以要看 response.url 才知道最后落在哪个页面
        if "/ap/signin" in response.url:
            print(f"[停止] {label} 被重定向到登录页，说明这个页面匿名访问不了。")
            print("       在 .env 里配置 AMAZON_COOKIE 后再试（见文件顶部说明）。")
            return None

        if response.status_code in (429, 503, 403):
            print(f"[警告] {label} 返回 {response.status_code}，当前速率或 IP 已经不够用，退避后重试")
            polite_sleep(backoff=attempt + 1)
            continue

        if response.status_code != 200:
            print(f"[警告] {label} 返回 {response.status_code}，跳过")
            return None

        if looks_like_challenge(response.text):
            print(f"[警告] {label} 返回人机验证页，退避后重试")
            polite_sleep(backoff=attempt + 1)
            continue

        return response.text

    print(f"[警告] {label} 试了 {MAX_RETRIES} 次仍未拿到内容")
    return None


def _text_or_default(tag, default: str = "") -> str:
    """BeautifulSoup 里经常要先判断标签存不存在再取文字，这个小工具统一处理。"""
    return tag.get_text(strip=True) if tag else default


def parse_one_review(review) -> dict:
    """
    解析单条评论（对应一个 <div data-hook="review">）。现在详情页的结构大致是：

        <div data-hook="review" id="R1KEX51WJPYR4T">
            <div class="a-profile-content"><span class="a-profile-name">Sheryl Fenton</span></div>
            <i data-hook="review-star-rating" class="a-icon-star a-star-5">
                <span class="a-icon-alt">5 out of 5 stars</span>
            </i>
            <h5 data-hook="reviewTitle">Best Grooming Kit I've Used</h5>
            <span data-hook="review-date">Reviewed in the United States on June 2, 2026</span>
            <div data-hook="reviewText">
                <div class="a-teaser-describedby-collapsed a-hidden">Brief content visible...</div>
                <div data-hook="reviewRichContentContainer"><p><span>正文...</span></p></div>
            </div>
        </div>

    老版全部评论页用的是 review-title / review-body，所以下面每个字段都写了两套选择器。
    """
    # 评论者姓名
    reviewer = _text_or_default(review.select_one("span.a-profile-name"))

    # 评分：文字是 "5 out of 5 stars"，不同布局下 data-hook 有两种写法，都试一遍。
    # 星级挂在 <i> 上，真正的文字藏在里面的 span.a-icon-alt 里。
    rating_tag = review.select_one(
        '[data-hook="review-star-rating"], [data-hook="review-star-rating-view-point"]'
    )
    rating_text = ""
    if rating_tag:
        alt = rating_tag.select_one(".a-icon-alt")
        rating_text = (alt or rating_tag).get_text(strip=True)
    # 既保留原文（"5 out of 5 stars"），也单独抽出数字方便后续统计
    rating_match = re.search(r"[\d.]+", rating_text)
    rating = rating_match.group() if rating_match else ""

    # 标题：老版是 <a data-hook="review-title">，里面第一个 span 是给读屏器的星级文字、
    # 最后一个才是真正的标题；新版是 <h5 data-hook="reviewTitle">，直接就是标题文字。
    title_tag = review.select_one('[data-hook="review-title"], [data-hook="reviewTitle"]')
    title = ""
    if title_tag:
        spans = title_tag.find_all("span", recursive=False)
        title = spans[-1].get_text(strip=True) if spans else title_tag.get_text(strip=True)
        # 有些布局下星级和标题挤在同一段文字里（"5.0 out of 5 stars\n标题"），把星级那段去掉
        title = re.sub(r"^[\d.]+ out of 5 stars\s*", "", title).strip()

    # 正文：优先用只装正文的容器；reviewText 里还混着"双击展开"之类的提示文字，
    # 这些提示都带 a-hidden 类（页面上不显示），取文字前先删掉。
    body_tag = review.select_one(
        '[data-hook="review-body"], [data-hook="reviewRichContentContainer"], [data-hook="reviewText"]'
    )
    body = ""
    if body_tag:
        for hidden in body_tag.select(".a-hidden"):
            hidden.decompose()
        # 用空格连接内部换行，避免一条评论在 CSV 里被拆成多行
        body = body_tag.get_text(" ", strip=True)
        body = re.sub(r"\s*Read more$", "", body)  # 末尾的展开按钮文字不属于评论内容

    # 日期：整行是 "Reviewed in the United States on June 2, 2026"，
    # 原文保留一份，同时把国家和日期拆开
    date_text = _text_or_default(review.select_one('[data-hook="review-date"]'))
    date_match = re.search(r"Reviewed in (?:the )?(.+?) on (.+)", date_text)
    country = date_match.group(1).strip() if date_match else ""
    date = date_match.group(2).strip() if date_match else date_text

    return {
        "review_id": review.get("id", ""),
        "reviewer": reviewer,
        "rating": rating,
        "rating_text": rating_text,
        "title": title,
        "body": body,
        "country": country,
        "date": date,
        "date_text": date_text,
    }


def parse_review_page(html: str) -> list[dict]:
    """把一页 HTML 解析成评论列表。单条解析失败不影响其他条。"""
    soup = BeautifulSoup(html, "html.parser")
    blocks = soup.select('[data-hook="review"]')

    reviews = []
    for block in blocks:
        try:
            reviews.append(parse_one_review(block))
        except (AttributeError, IndexError, TypeError) as exc:
            # 页面结构和预期不一致（比如 Amazon 改版）时，跳过这一条，不要让整个程序崩溃
            print(f"[警告] 解析某条评论失败，已跳过：{exc}")
    return reviews


def has_next_page(html: str) -> bool:
    """
    判断还有没有下一页：分页条里的 "Next page" 如果带 a-disabled 类，说明已经是最后一页。
    详情页压根没有分页条，找不到时按"没有下一页"处理，避免空转。
    """
    soup = BeautifulSoup(html, "html.parser")
    next_li = soup.select_one("li.a-last")
    if next_li is None:
        return False
    return "a-disabled" not in next_li.get("class", [])


# ---------------------------------------------------------------------------
# 「加载更多评论」AJAX 接口
#
# 新版全部评论页不是靠 ?pageNumber= 翻页，而是点"加载更多"时发一个 POST
# （文件末尾贴了抓到的请求头）。要用这条路需要两样东西：
#     1. AMAZON_COOKIE —— 这个接口和页面一样要登录态
#     2. 下面的 AJAX_PAYLOAD_TEMPLATE —— 请求体，抓包里 Content-Length 是 101 字节
#
# 请求体怎么拿：F12 → Network → 点"加载更多" → 找到 request-more-reviews/submit
# 这条请求 → 「载荷 / Payload」标签 → 点 "view source" 复制成一整行原始文本，
# 粘到下面，然后把里面表示页码/游标的那个值换成 {page}。形如：
#
#     AJAX_PAYLOAD_TEMPLATE = "asin=B096VP4L1W&pageNumber={page}&reviewerType=all_reviews"
#
# 留空表示没配置，脚本会退回用 REVIEWS_URL 的 ?pageNumber= 方式翻页。
# ---------------------------------------------------------------------------
AJAX_PAYLOAD_TEMPLATE = ""


def extract_flow_closure_id(html: str) -> str | None:
    """
    从页面里找 flowClosureId。抓包时它作为 X-Amzn-Flow-Closure-Id 请求头发出去，
    值是页面加载时生成的，写死没用，得每次从当前页面里取。
    """
    match = re.search(r'flowClosureId["\']?\s*[:=]\s*["\']?(\d+)', html)
    return match.group(1) if match else None


def ajax_html_fragments(text: str) -> str:
    """
    把 AJAX 响应里的 HTML 片段抠出来，拼成一段 HTML 交给 parse_review_page。

    这类接口的返回可能是三种形态之一，都兼容一下：
        1. 直接就是一段 HTML
        2. Amazon 常用的 "&&&" 分隔格式，每段是 ["append", "#选择器", "<div>...</div>"]
        3. 一个 JSON 对象，HTML 藏在某个字段里
    做法是：能当 JSON 解析就递归把所有"看起来像评论 HTML"的字符串收集起来。
    """
    text = text.strip()
    if not text:
        return ""

    fragments: list[str] = []

    def collect(node) -> None:
        if isinstance(node, str):
            if 'data-hook="review"' in node:
                fragments.append(node)
        elif isinstance(node, list):
            for item in node:
                collect(item)
        elif isinstance(node, dict):
            for item in node.values():
                collect(item)

    for chunk in text.split("&&&"):
        chunk = chunk.strip()
        if not chunk:
            continue
        try:
            collect(json.loads(chunk))
        except json.JSONDecodeError:
            # 不是 JSON，那就当它本来就是 HTML
            if 'data-hook="review"' in chunk:
                fragments.append(chunk)

    return "\n".join(fragments)


def fetch_more_reviews_ajax(page_number: int, flow_closure_id: str | None) -> str | None:
    """
    调用"加载更多评论"接口，返回拼好的 HTML 片段。请求头照抄抓包结果里真正起作用的那几个：
    Content-Type / X-Requested-With / Origin / Referer（少了它们 Amazon 会当成非法请求）。
    """
    payload = AJAX_PAYLOAD_TEMPLATE.replace("{page}", str(page_number))

    headers = random_headers()
    headers.update({
        "Accept": "text/html,*/*",
        "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
        "Origin": "https://www.amazon.com",
        "Referer": PORTAL_URL,
        "X-Requested-With": "XMLHttpRequest",
    })
    if flow_closure_id:
        headers["X-Amzn-Flow-Closure-Id"] = flow_closure_id

    label = f"第 {page_number} 页(AJAX)"
    for attempt in range(MAX_RETRIES):
        try:
            response = SESSION.post(AJAX_URL, data=payload, headers=headers, timeout=15)
        except requests.RequestException as exc:
            print(f"[警告] {label} 请求失败：{exc}")
            polite_sleep(backoff=attempt + 1)
            continue

        if response.status_code in (429, 503, 403):
            print(f"[警告] {label} 返回 {response.status_code}，退避后重试")
            polite_sleep(backoff=attempt + 1)
            continue

        if response.status_code == 400:
            # 端点认得这个请求，但参数不对——多半是请求体抄错了，重试多少次都一样
            print(f"[停止] {label} 返回 400，请求体大概率不对，请重新核对 AJAX_PAYLOAD_TEMPLATE。")
            return None

        if response.status_code == 401:
            print(f"[停止] {label} 返回 401，登录态无效（Cookie 过期了？）。")
            return None

        if response.status_code != 200:
            print(f"[警告] {label} 返回 {response.status_code}，跳过")
            return None

        return ajax_html_fragments(response.text)

    print(f"[警告] {label} 试了 {MAX_RETRIES} 次仍未拿到内容")
    return None


def scrape_reviews() -> list[dict]:
    """
    抓取评论，三条路按可用性从高到低：
        1. 配了 Cookie + AJAX 请求体 —— 走"加载更多"接口，能拿最多
        2. 只配了 Cookie —— 走全部评论页的 ?pageNumber= 翻页
        3. 什么都没配 —— 只抓详情页内嵌的那十几条（匿名唯一能拿到的部分）
    """
    logged_in = bool(os.getenv("AMAZON_COOKIE"))
    if logged_in:
        print("检测到 AMAZON_COOKIE，使用全部评论页并翻页。")
    else:
        print("未配置 AMAZON_COOKIE，只抓商品详情页里内嵌的评论（约十几条）。")

    use_ajax = logged_in and bool(AJAX_PAYLOAD_TEMPLATE.strip())
    flow_closure_id = None
    if use_ajax:
        # AJAX 接口要求 Referer 是全部评论页，所以先正常打开这个页面：
        # 一来拿到 flowClosureId，二来让 Session 里带上这次访问下发的 Cookie，
        # 顺序和真人"先打开页面、再点加载更多"一致。
        print("检测到 AJAX_PAYLOAD_TEMPLATE，使用「加载更多评论」接口。")
        portal_html = fetch(PORTAL_URL, params={"reviewerType": "all_reviews"}, label="全部评论页")
        if portal_html is None:
            print("[停止] 打不开全部评论页，无法继续用 AJAX 接口。")
            return []
        flow_closure_id = extract_flow_closure_id(portal_html)
        print(f"    flowClosureId = {flow_closure_id or '(没找到，请求头里就不带这一项)'}")

    all_reviews: list[dict] = []
    seen_ids: set[str] = set()  # Amazon 有时会把同一页返回两次，用评论 id 去重

    for page_number in range(1, MAX_PAGES + 1):
        if use_ajax:
            label = f"第 {page_number} 页"
            print(f"正在抓取{label} ...")
            html = fetch_more_reviews_ajax(page_number, flow_closure_id)
        elif logged_in:
            label = f"第 {page_number} 页"
            print(f"正在抓取{label} ...")
            html = fetch(
                REVIEWS_URL,
                params={"ie": "UTF8", "reviewerType": "all_reviews", "pageNumber": page_number},
                label=label,
            )
        else:
            label = "商品详情页"
            print(f"正在抓取{label} ...")
            html = fetch(DETAIL_URL, label=label)

        if html is None:
            # 退避重试后仍然拿不到内容，继续硬爬只会让情况更糟，
            # 直接停下来，已经抓到的数据照常保存
            print("[停止] 拿不到页面内容，提前结束抓取。")
            break

        reviews = parse_review_page(html)
        if not reviews:
            print("[停止] 这一页没有解析到评论，可能已经翻到底了。")
            break

        new_count = 0
        for review in reviews:
            review_id = review["review_id"]
            if review_id and review_id in seen_ids:
                continue
            seen_ids.add(review_id)
            all_reviews.append(review)
            new_count += 1
        print(f"    解析到 {len(reviews)} 条，新增 {new_count} 条")

        if not logged_in:
            # 详情页只有内嵌的这一批评论，没有翻页可言。
            # （详情页别处也有 li.a-last，不能拿 has_next_page 判断，否则会把同一页重抓 MAX_PAGES 次）
            print("详情页只内嵌这一批评论，想要更多请配置 AMAZON_COOKIE。")
            break

        if new_count == 0:
            # 这一页全是已经见过的评论，说明翻页参数没生效（Amazon 把第 1 页又返回了一遍）。
            # 再往下翻只会重复请求同一批数据，直接停。
            print("[停止] 这一页全是重复评论，翻页参数没生效。")
            break

        # AJAX 接口的返回是评论片段，没有分页条，只能靠"还有没有新数据"判断是否继续
        if not use_ajax and not has_next_page(html):
            print("没有下一页了。")
            break

        polite_sleep()

    return all_reviews


def save_to_csv(reviews: list[dict], path: str) -> None:
    """把评论列表保存为 CSV 文件。"""
    if not reviews:
        print("没有抓到任何数据，不写入文件。")
        return

    os.makedirs(os.path.dirname(path), exist_ok=True)

    # newline="" 是 csv 模块官方推荐的写法，避免 Windows 下每行之间多出空行
    # encoding="utf-8-sig" 带 BOM 头，用 Excel 直接打开这个 CSV 时中文不会变成乱码
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=list(reviews[0].keys()))
        writer.writeheader()
        writer.writerows(reviews)


if __name__ == "__main__":
    reviews = scrape_reviews()
    save_to_csv(reviews, DATA_PATH)
    print(f"共抓取 {len(reviews)} 条评论，已保存到 {DATA_PATH}")
