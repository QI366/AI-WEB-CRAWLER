"""
抓取 PoodleGuru 的长文正文，按"标题 + 正文"拆成一行行数据存成 CSV。

目标页面：https://poodleguru.com/poodle-grooming-cost/

页面是 WordPress 输出的静态 HTML（不需要浏览器渲染），正文整体包在 .pg-post 里，
作者用一套 pg- 前缀的 class 把内容切成了不同类型的块，所以抓取时也按块的类型分别处理：

    pg-hero      顶部标题区：pg-kicker（栏目名）+ h1（大标题）+ pg-lede（导语）+ pg-meta（作者/更新时间）
    pg-qa        开头的"快速回答"
    pg-cards     速览卡片组，每张 pg-card 是 h3 + p
    pg-table     数据表格，转成 "单元格 | 单元格" 的纯文本
    pg-steps     操作步骤组，每个 pg-step 是 序号 + h4 + p
    pg-tips      专家提示
    pg-faq       一问一答，h3 是问题，p 是答案（每个问答一行）
    pg-summary   结尾总结，里面的 pg-takeaways 是要点列表
    pg-author    作者简介
    其余的 h2/h3 + 后面跟着的段落/列表/表格，按"一个小节"合并成一行

不是正文的一律跳过：目录（pg-toc）、配图（figure）、广告位（code-block，里面是
AdSense 脚本）、联盟免责声明（pg-disclosure）、"相关阅读"导流卡片（pg-related）。
另外正文里混着的推广文案（"点我试用"这类 CTA）按行过滤，见 AD_PATTERNS。

输出：data/poodleguru/<url 末尾的 slug>.csv，两列
    title        VarChar(512)
    description  VarChar(32000)
超出上限的会被截断（结尾补 "…"），保证结果可以直接入库。

运行方式：
    python exercises/poodleguru/poodle-grooming-cost.py
输出目录是相对项目根目录算出来的，在哪个目录下执行都不影响结果。
"""

import csv
import random
import re
import time
from pathlib import Path
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

# 想抓的文章，往列表里加同一站点的其它 URL 就能一起抓（每篇存成单独的 CSV）
ARTICLE_URLS = [
    "https://poodleguru.com/poodle-grooming-cost/",
]

# exercises/poodleguru/xxx.py -> parents[2] 就是项目根目录
OUTPUT_DIR = Path(__file__).resolve().parents[2] / "data" / "poodleguru"

# 入库字段长度上限，超了就截断
TITLE_MAX_LEN = 512
DESCRIPTION_MAX_LEN = 32000

# 照抄浏览器实际发出的请求头：带上 Referer 和 sec-ch-ua 系列，
# 让请求看起来是从站内点进来的正常访问，而不是裸奔的脚本
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36 Edg/151.0.0.0"
    ),
    "Referer": "https://poodleguru.com/",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "sec-ch-ua": '"Not=A?Brand";v="99", "Microsoft Edge";v="151", "Chromium";v="151"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',
    "Upgrade-Insecure-Requests": "1",
}

# 这些标签/class 不属于正文，遍历时直接跳过：
#   pg-toc          目录
#   pg-disclosure   "本文含联盟链接，可能获得佣金"的免责声明
#   code-block      广告位（里面是 Google AdSense 的 script）
#   pg-related      "相关阅读"推广卡片，只是站内导流，不是文章内容
#   pg-author-label "Written by" 这种纯标签文字
#   figure          配图
SKIP_TAGS = {"figure", "script", "style", "noscript", "nav"}
SKIP_CLASSES = {"pg-toc", "pg-disclosure", "code-block", "pg-related", "pg-author-label"}

# 广告/推广文案：免责声明、"点我试用"这类纯 CTA，命中的整行丢掉。
# 写得尽量收紧，别误伤正文（比如 "groomers who advertise poodle experience" 不该被当广告）
AD_PATTERNS = [
    re.compile(r"\baffiliate\s+links?\b", re.I),           # This article contains affiliate links
    re.compile(r"\bearn\s+(a\s+)?(small\s+)?commission\b", re.I),
    re.compile(r"\b(sponsored\s+(content|post|by)|advertisement)\b", re.I),
    re.compile(r"^[👉👇🔥⬇️➡️]"),                            # 以指路 emoji 开头的行基本都是按钮文案
    re.compile(r"^(try|shop|buy|order|download|subscribe)\b.{0,60}\b(now|today|here|free)\b", re.I),
]


def _sentence(text: str) -> re.Pattern:
    """
    把一句原文编译成正则：单词之间允许多个空白，撇号不区分直的 ' 和弯的 ’。
    这样原站以后微调排版（多个空格、换一种引号），规则也还能命中。
    """
    pattern = r"\s+".join(re.escape(word) for word in text.split())
    # 一次性把两种撇号都换成字符组；分两次 replace 会把刚插进去的 ' 再替换一遍，正则就废了
    return re.compile(re.sub(r"['’]", "['’]", pattern))


# 原文里带推销/导购口吻的句子，逐句改写成中性表述。
# 只动语气：价格区间、频率、做法这些事实信息原样保留。
# 这一篇整体比较克制，主要是结尾那个 "Buyer Tip" 小节在劝人买工具。
REWRITES = [
    (_sentence("Buyer Tip: The Tool Investment That Pays Back Fastest"),
     "Which Grooming Tool Matters Most"),
    (_sentence("If you buy one piece of equipment for home grooming, make it a high-quality slicker brush "
               "and a metal greyhound comb — not clippers."),
     "Among home grooming equipment, a slicker brush and a metal greyhound comb matter more than clippers."),
    (_sentence("Expect to spend $25–$50 on a good brush and comb set. "
               "It pays for itself in one avoided dematting fee."),
     "A decent brush and comb set costs about $25–$50, roughly the same as a single dematting fee."),
    (_sentence("That pays for itself within a year for most Standard Poodle owners."),
     "For most Standard Poodle owners that outlay is recovered within a year "
     "compared with professional grooming."),
]


# ---------------------------------------------------------------- 抓取

def fetch_html(url: str, retries: int = 3) -> str | None:
    """请求页面，返回 HTML 文本；重试若干次后仍失败则返回 None（不让程序崩溃）。"""
    for attempt in range(1, retries + 1):
        try:
            response = requests.get(url, headers=HEADERS, timeout=15)
            response.raise_for_status()
        except requests.RequestException as exc:
            print(f"[警告] 第 {attempt}/{retries} 次请求 {url} 失败：{exc}")
            if attempt < retries:
                # 退避重试：等的时间一次比一次长，别一失败就马上再撞上去
                time.sleep(attempt * 2 + random.uniform(0, 1))
            continue

        # 响应头里写了 charset=UTF-8，requests 能正确识别；
        # 万一遇到没声明编码的页面，requests 会退回 ISO-8859-1，这里用探测结果兜底
        if not response.encoding or response.encoding.lower() == "iso-8859-1":
            response.encoding = response.apparent_encoding
        return response.text

    return None


# ---------------------------------------------------------------- 文本清洗

def clean_text(node) -> str:
    """把一个标签里的文字取出来，压掉换行和连续空格；标签不存在时返回空串。"""
    if node is None:
        return ""
    text = node.get_text(" ", strip=True)
    # \xa0 是 HTML 里的 &nbsp;（不换行空格），看着像空格但不是，统一换成普通空格
    text = re.sub(r"\s+", " ", text.replace("\xa0", " ")).strip()
    # 取文字时给标签之间补了空格，遇上 <strong>xxx</strong>, 这种写法会留下 "xxx ," ，去掉
    return re.sub(r"\s+([,.;:!?])", r"\1", text)


def table_to_text(table) -> str:
    """把表格拍平成纯文本：一行一行，单元格之间用 " | " 隔开。"""
    lines = []
    for row in table.find_all("tr"):
        cells = [clean_text(cell) for cell in row.find_all(["th", "td"])]
        if any(cells):
            lines.append(" | ".join(cells))
    return "\n".join(lines)


def list_to_text(node) -> str:
    """把 ul/ol 转成一行一条的文本。"""
    items = [clean_text(li) for li in node.find_all("li")]
    return "\n".join(f"- {item}" for item in items if item)


def node_to_text(node) -> str:
    """按标签类型把一个块转成文本：表格拍平、列表逐条列出、其余直接取文字。"""
    if node.name == "table":
        return table_to_text(node)

    # div.pg-table-wrap 这种外面套了一层的，取里面的表格
    tables = node.find_all("table")
    if tables:
        return "\n".join(table_to_text(table) for table in tables)

    if node.name in {"ul", "ol"}:
        return list_to_text(node)

    # "When to Ask a Professional Groomer" 那个 div.pg-note 里是"小标题 + 清单"，
    # 整块直接取文字会把标题和每一条挤成一行，所以按子块拆开
    if node.find(["ul", "ol"]) is not None:
        parts = [
            list_to_text(child) if child.name in {"ul", "ol"} else clean_text(child)
            for child in node.find_all(recursive=False)
        ]
        return "\n".join(part for part in parts if part)

    return clean_text(node)


def is_ad_text(text: str) -> bool:
    """这一行是不是广告/推广文案。"""
    return any(pattern.search(text) for pattern in AD_PATTERNS)


def strip_ads(text: str) -> str:
    """逐行过滤掉广告/推广文案，剩下的正文原样拼回去。"""
    return "\n".join(line for line in text.split("\n") if not is_ad_text(line))


def apply_rewrites(text: str, used: set[int]) -> str:
    """把 REWRITES 里的推销句换成中性写法，顺便记下哪几条规则命中了。"""
    for index, (pattern, replacement) in enumerate(REWRITES):
        text, count = pattern.subn(replacement, text)
        if count:
            used.add(index)
    return text


def join_title(parent: str, child: str) -> str:
    """把"区块标题"和"小标题"拼成一个标题，比如 "速览 | 单次价格区间"。"""
    if parent and child:
        return f"{parent} | {child}"
    return child or parent


# ---------------------------------------------------------------- 各类区块的解析

def parse_hero(node) -> list[tuple[str, str]]:
    """顶部标题区：h1 当标题，导语 + 作者/更新时间当正文。"""
    title = clean_text(node.select_one("h1")) or clean_text(node.select_one(".pg-kicker"))
    lede = clean_text(node.select_one(".pg-lede"))
    meta = " · ".join(clean_text(span) for span in node.select(".pg-meta > span"))
    description = "\n".join(part for part in (lede, meta) if part)
    return [(title, description)]


def parse_titled_block(node) -> list[tuple[str, str]]:
    """
    "自带标题的整块"（pg-qa / pg-summary / pg-tips / pg-author / 单个 pg-faq）：
    第一个 h2~h4 当标题，块里其余的段落、列表项、表格拼成正文。
    """
    heading = node.find(["h2", "h3", "h4"])
    title = clean_text(heading)

    parts = []
    for element in node.find_all(["p", "li", "table"]):
        if element is heading or set(element.get("class", [])) & SKIP_CLASSES:
            continue
        text = clean_text(element) if element.name != "table" else table_to_text(element)
        if not text:
            continue
        parts.append(f"- {text}" if element.name == "li" else text)

    return [(title, "\n".join(parts))]


def parse_cards(node) -> list[tuple[str, str]]:
    """卡片组 pg-cards：每张 pg-card（h3 + p）单独存一行。"""
    section_title = clean_text(node.find(["h2", "h3"], recursive=False))

    blocks = []
    for card in node.select(".pg-card"):
        card_title = clean_text(card.find(["h3", "h4"]))
        body = "\n".join(clean_text(p) for p in card.find_all("p"))
        blocks.append((join_title(section_title, card_title), body))
    return blocks


def parse_steps(node) -> list[tuple[str, str]]:
    """步骤组 pg-steps：每个 pg-step（序号 strong + h4 + p）单独存一行。"""
    section_title = clean_text(node.find(["h2", "h3"], recursive=False))

    blocks = []
    for step in node.select(".pg-step"):
        number = clean_text(step.find("strong"))
        step_title = clean_text(step.find(["h4", "h3"]))
        body = "\n".join(clean_text(p) for p in step.find_all("p"))
        label = f"{number}. {step_title}" if number else step_title
        blocks.append((join_title(section_title, label), body))
    return blocks


# class -> 解析函数。遍历正文时命中哪个 class 就交给哪个函数处理
BLOCK_PARSERS = {
    "pg-hero": parse_hero,
    "pg-cards": parse_cards,
    "pg-steps": parse_steps,
    "pg-qa": parse_titled_block,
    "pg-tips": parse_titled_block,
    "pg-faq": parse_titled_block,
    "pg-summary": parse_titled_block,
    "pg-author": parse_titled_block,
}


# ---------------------------------------------------------------- 正文遍历

def extract_blocks(html: str) -> list[dict]:
    """把一篇文章的 HTML 拆成若干条 {"title": ..., "description": ...}。"""
    soup = BeautifulSoup(html, "html.parser")
    post = soup.select_one(".pg-post") or soup.find("article") or soup.body
    if post is None:
        return []

    # 没有小标题的段落（比如开头那段）用文章大标题兜底
    page_title = clean_text(soup.find("h1")) or clean_text(soup.find("title"))

    blocks: list[tuple[str, str]] = []
    heading = ""          # 当前小节的标题
    paragraphs: list[str] = []   # 当前小节已经攒下的正文

    def flush() -> None:
        """把攒着的"h2 + 后面几段"结算成一条记录。"""
        nonlocal heading, paragraphs
        if paragraphs:
            blocks.append((heading or page_title, "\n".join(paragraphs)))
        heading, paragraphs = "", []

    # 只遍历正文的直接子节点：正文是平铺结构（h2、p、div 一个挨一个），
    # 嵌套内容交给各自的解析函数去处理
    for node in post.find_all(recursive=False):
        classes = set(node.get("class", []))
        if node.name in SKIP_TAGS or classes & SKIP_CLASSES:
            continue

        # 遇到新标题，先把上一节结算掉
        if node.name in {"h1", "h2", "h3", "h4"}:
            flush()
            heading = clean_text(node)
            continue

        parser = next((BLOCK_PARSERS[c] for c in classes if c in BLOCK_PARSERS), None)
        if parser is not None:
            flush()
            blocks.extend(parser(node))
            continue

        text = node_to_text(node)
        if text:
            paragraphs.append(text)

    flush()

    # 统一在这里过广告 + 改写推销句：正文逐行过滤，标题本身是推广文案的整条丢掉；
    # 过滤后正文空了的（整块都是广告）也一并丢掉，顺手做长度截断
    used_rewrites: set[int] = set()
    rows = []
    for title, description in blocks:
        description = strip_ads(description)
        if not title or not description or is_ad_text(title):
            continue
        rows.append(
            {
                "title": truncate(apply_rewrites(title, used_rewrites), TITLE_MAX_LEN),
                "description": truncate(apply_rewrites(description, used_rewrites), DESCRIPTION_MAX_LEN),
            }
        )

    # 有规则没命中，多半是原站改了措辞：提示一下，免得改写规则悄悄失效
    missed = [index for index in range(len(REWRITES)) if index not in used_rewrites]
    if missed:
        print(f"[提示] {len(missed)} 条改写规则没匹配到（原文可能改了措辞）：{missed}")

    return rows


def truncate(text: str, limit: int) -> str:
    """超过字段长度上限就截断，末尾补 "…" 表示这里被截过。"""
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


# ---------------------------------------------------------------- 保存

def slug_from_url(url: str) -> str:
    """从 URL 里取最后一段当文件名，比如 .../poodle-grooming-cost/ -> poodle-grooming-cost。"""
    path = urlparse(url).path.strip("/")
    slug = path.split("/")[-1] if path else urlparse(url).netloc
    # 只保留文件名里安全的字符，避免奇怪的 URL 拼出非法路径
    return re.sub(r"[^\w.-]", "_", slug) or "index"


def save_to_csv(rows: list[dict], path: Path) -> None:
    """把结果存成两列的 CSV：title / description。"""
    path.parent.mkdir(parents=True, exist_ok=True)

    # encoding="utf-8-sig" 带 BOM 头，用 Excel 直接打开时不会乱码
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=["title", "description"])
        writer.writeheader()
        writer.writerows(rows)


# ---------------------------------------------------------------- 主流程

def crawl(url: str) -> int:
    """抓一篇文章并存成 CSV，返回写入的条数。"""
    html = fetch_html(url)
    if html is None:
        print(f"[跳过] {url} 抓取失败")
        return 0

    try:
        rows = extract_blocks(html)
    except (AttributeError, IndexError, TypeError) as exc:
        # 页面改版会让选择器落空，单篇解析出错不该拖垮整个任务
        print(f"[跳过] {url} 解析失败：{exc}")
        return 0

    if not rows:
        print(f"[跳过] {url} 没解析出任何内容，不写文件")
        return 0

    path = OUTPUT_DIR / f"{slug_from_url(url)}.csv"
    save_to_csv(rows, path)
    print(f"{url} -> {path}（{len(rows)} 条）")
    return len(rows)


if __name__ == "__main__":
    total = 0
    for index, article_url in enumerate(ARTICLE_URLS):
        if index:
            # 抓多篇时随机等 1~3 秒，别把请求打得太密
            time.sleep(random.uniform(1, 3))
        total += crawl(article_url)

    print(f"共写入 {total} 条数据，输出目录：{OUTPUT_DIR}")
