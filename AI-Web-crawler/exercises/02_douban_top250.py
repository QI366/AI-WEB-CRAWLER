"""
爬取豆瓣电影 Top250: https://movie.douban.com/top250

需求（对照练习要求实现）：
    1. 处理分页（Top250 一共 250 部电影）
    2. 每次请求之间加延迟 time.sleep(1)，不要访问太频繁
    3. 处理异常（网络请求失败 / 页面结构解析失败）
    4. 用 tqdm 显示抓取进度条
    5. 结果保存成 CSV

运行方式（建议在项目根目录执行，这样相对路径 DATA_PATH 才是对的）：
    python exercises/02_douban_top250.py
"""

import csv
import os
import re
import time

import requests
from bs4 import BeautifulSoup
from tqdm import tqdm

BASE_URL = "https://movie.douban.com/top250"

# 豆瓣一页显示 25 部电影，Top250 一共 250 部。
# 每页的请求参数 start 依次是 0, 25, 50 ... 225。
PAGE_SIZE = 25
TOTAL_MOVIES = 250

DATA_PATH = "data/douban_top250.csv"

# 只带 User-Agent（伪装成浏览器）和 Referer，不带 Cookie。
# Cookie 里通常包含你个人的登录/会话信息，写死在代码里一旦提交到 git 就会泄露，
# 而 Top250 这种公开列表页不登录也能正常访问，所以这里先不用它。
# 以后如果要抓需要登录才能看到的内容，再把 Cookie 放进 .env 之类不会被提交的地方。
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36 Edg/150.0.0.0"
    ),
    "Referer": BASE_URL,
}


def fetch_page(start: int) -> str | None:
    """请求 Top250 中的某一页，返回 HTML 文本；请求失败则返回 None（不让程序崩溃）。"""
    params = {"start": start, "filter": ""}
    try:
        response = requests.get(BASE_URL, headers=HEADERS, params=params, timeout=10)
        response.raise_for_status()  # 状态码不是 2xx（比如被拦截返回 418）时会抛出异常
    except requests.RequestException as exc:
        print(f"[警告] start={start} 请求失败：{exc}")
        return None
    return response.text


def _clean_alt_text(text: str) -> str:
    """
    豆瓣页面里像 "&nbsp;/&nbsp;The Shawshank Redemption" 这样的文本，
    BeautifulSoup 解析后 &nbsp; 会变成不可见的空格字符 \\xa0，
    这个函数把这种前缀 "/" 和多余空白都去掉，只留下真正的文字内容。
    """
    return text.replace("\xa0", " ").strip(" /")


def parse_one_movie(item) -> dict:
    """
    解析单个电影的节点（对应一个 <div class="item">），提取我们关心的字段。
    对照的参考结构大致是：

        <div class="item">
            <div class="pic"><em>1</em><a href="详情页链接">...</a></div>
            <div class="info">
                <div class="hd">
                    <a href="详情页链接">
                        <span class="title">肖申克的救赎</span>
                        <span class="title">&nbsp;/&nbsp;The Shawshank Redemption</span>
                        <span class="other">&nbsp;/&nbsp;月黑高飞(港) / 刺激1995(台)</span>
                    </a>
                </div>
                <div class="bd">
                    <p>导演: XXX&nbsp;&nbsp;&nbsp;主演: YYY /...<br>1994&nbsp;/&nbsp;美国&nbsp;/&nbsp;犯罪 剧情</p>
                    <div><span class="rating_num">9.7</span><span>3308245人评价</span></div>
                    <p class="quote"><span>希望让人自由。</span></p>
                </div>
            </div>
        </div>
    """
    # 排名：<em>1</em>
    rank = item.find("em").get_text(strip=True)

    hd = item.find("div", class_="hd")
    detail_url = hd.find("a")["href"]

    # 标题：中文名一定有，英文名（第二个 .title）不是每部电影都有
    title_spans = hd.select("span.title")
    title_cn = title_spans[0].get_text(strip=True)
    title_en = _clean_alt_text(title_spans[1].get_text()) if len(title_spans) > 1 else ""

    # 别名（港译 / 台译等），也不是每部都有
    other_span = hd.select_one("span.other")
    aka = _clean_alt_text(other_span.get_text()) if other_span else ""

    # 评分
    rating_tag = item.find("span", class_="rating_num")
    rating = rating_tag.get_text(strip=True) if rating_tag else ""

    # 评价人数：跟评分在同一个父节点下，文字类似 "3308245人评价"，只提取数字部分
    rating_count = ""
    if rating_tag:
        for span in rating_tag.parent.find_all("span"):
            text = span.get_text(strip=True)
            if text.endswith("人评价"):
                rating_count = re.sub(r"\D", "", text)
                break

    # 一句话短评：不是每部电影都有，找不到就留空字符串
    quote_tag = item.select_one("p.quote span")
    quote = quote_tag.get_text(strip=True) if quote_tag else ""

    # 导演/主演/年份/国家/类型全部挤在同一个 <p> 标签里，中间用 <br> 分隔成两行，
    # 用 get_text("\n") 把 <br> 换成换行符，再按行拆开处理
    info_p = item.select_one("div.bd p")
    lines = [line.strip() for line in info_p.get_text("\n").split("\n") if line.strip()]

    director, actors = "", ""
    if lines:
        director_actors_line = lines[0].replace("导演:", "").strip()
        if "主演:" in director_actors_line:
            director, actors = director_actors_line.split("主演:", 1)
            director, actors = director.strip(), actors.strip()
        else:
            # 有些电影（比如纪录片）没有主演信息，只有导演
            director = director_actors_line

    year, country, genre = "", "", ""
    if len(lines) > 1:
        parts = [p.strip() for p in lines[1].split("/")]
        year = parts[0] if len(parts) > 0 else ""
        country = parts[1] if len(parts) > 1 else ""
        genre = parts[2] if len(parts) > 2 else ""

    return {
        "rank": rank,
        "title_cn": title_cn,
        "title_en": title_en,
        "aka": aka,
        "rating": rating,
        "rating_count": rating_count,
        "quote": quote,
        "director": director,
        "actors": actors,
        "year": year,
        "country": country,
        "genre": genre,
        "detail_url": detail_url,
    }


def parse_page(html: str) -> list[dict]:
    """把一页的 HTML 解析成电影信息列表。单条数据解析失败不影响其他数据。"""
    soup = BeautifulSoup(html, "html.parser")
    items = soup.select("ol.grid_view li div.item")

    movies = []
    for item in items:
        try:
            movies.append(parse_one_movie(item))
        except (AttributeError, IndexError, TypeError) as exc:
            # 页面结构和预期不一致（比如豆瓣改版）时，跳过这一条，不要让整个程序崩溃
            print(f"[警告] 解析某条数据失败，已跳过：{exc}")
    return movies


def scrape_top250() -> list[dict]:
    """依次抓取 Top250 的每一页，返回全部电影的列表。"""
    all_movies: list[dict] = []
    starts = range(0, TOTAL_MOVIES, PAGE_SIZE)  # 0, 25, 50, ..., 225，共 10 页

    for start in tqdm(list(starts), desc="抓取豆瓣 Top250"):
        html = fetch_page(start)
        if html is not None:
            all_movies.extend(parse_page(html))

        time.sleep(1)  # 每次请求后停顿 1 秒，避免访问过于频繁被豆瓣限制

    return all_movies


def save_to_csv(movies: list[dict], path: str) -> None:
    """把电影列表保存为 CSV 文件。"""
    if not movies:
        print("没有抓到任何数据，不写入文件。")
        return

    os.makedirs(os.path.dirname(path), exist_ok=True)

    # newline="" 是 csv 模块官方推荐的写法，避免 Windows 下每行之间多出空行
    # encoding="utf-8-sig" 带 BOM 头，用 Excel 直接打开这个 CSV 时中文不会变成乱码
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=list(movies[0].keys()))
        writer.writeheader()
        writer.writerows(movies)


if __name__ == "__main__":
    movies = scrape_top250()
    save_to_csv(movies, DATA_PATH)
    print(f"共抓取 {len(movies)} 部电影，已保存到 {DATA_PATH}")
