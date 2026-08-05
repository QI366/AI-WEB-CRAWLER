"""
抓取 PoodleGuru 的训练费用估算页正文，按"标题 + 正文"拆成一行行数据存成 CSV。

目标页面：https://poodleguru.com/poodle-training-cost-estimator/

这一篇和 poodles-nutrition.py 是同一套 WordPress 模板（正文在 .entry-content 里，
h2/h3 + p + ul/ol + figure.wp-block-table），但多了两个要单独处理的地方：

    1. 页面顶部的 div#pte-root 是一个纯前端的费用计算器（style + 表单 + script），
       它的文字全是"选项名/按钮"这类界面元素，不是文章内容，整块跳过。
       计算结果是点完选项后由 JS 现算出来的，requests 抓到的静态 HTML 里也没有。
    2. 结尾的 FAQ 不是 h3 + p，而是一个 <ol>，每个 <li> 长这样：
           <li><strong>问题？</strong><br>答案……</li>
       这种列表按"一问一行"拆开，而不是整个列表挤成一条记录。

按注释要求跳过作者简介（pg-author）：这一篇的作者信息在 .entry-header 里，
本来就不在 .entry-content 中，规则保留着以防同模板的其它文章正文里塞了作者块。
广告位（code-block，里面是 Google AdSense 脚本）、联盟免责声明、结构化数据
（JSON-LD script）、配图同样跳过；正文里混着的推广文案（"👉 Try the Tool Now"
这类 CTA）按行过滤，"Related Poodle Tools" 这种整节导流的小节整块丢掉，
见 AD_PATTERNS / PROMO_SECTION。

输出：data/poodleguru/<url 末尾的 slug>.csv，两列
    title        VarChar(512)
    description  VarChar(32000)
超出上限的会被截断（结尾补 "…"），保证结果可以直接入库。

运行方式：
    python exercises/poodleguru/poodle-training-cost-estimator.py
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

# 想抓的文章，往列表里加同模板的其它 URL 就能一起抓（每篇存成单独的 CSV）
ARTICLE_URLS = [
    "https://poodleguru.com/poodle-training-cost-estimator/",
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

# 这些标签/class/id 不属于正文，遍历时直接跳过：
# 脚本样式、广告位（code-block，里面是 Google AdSense 的 script）、联盟免责声明
# （pg-disclosure）、作者简介（pg-author，按注释要求跳过）、配图、计算器控件
SKIP_TAGS = {"script", "style", "noscript", "nav", "form"}
SKIP_CLASSES = {"code-block", "pg-disclosure", "pg-author", "pg-toc", "wp-block-image"}
SKIP_ID_PREFIX = "pte-"  # 费用计算器控件用的都是 pte- 前缀

# 整节都是站内导流的推广小节（这篇结尾的 "Related Poodle Tools" 就是一串站内工具链接），
# 标题命中就整节丢掉
PROMO_SECTION = re.compile(r"^(related|more|you may also|recommended)\b", re.I)

# 广告/推广文案：免责声明、"👉 Try the Tool Now"这类纯 CTA，命中的整行丢掉。
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


# 原文里带推销语气的句子，逐句改写成中性表述。
# 这一篇的推销集中在"推自家的估算器工具"和"Best…"这类营销措辞上，
# 只动语气：价格区间、影响因素这些事实信息原样保留。
REWRITES = [
    (_sentence("Best Poodle Training Cost Estimator Tool 2026"),
     "Poodle Training Costs 2026"),
    (_sentence("Poodle Training Cost Estimator — use this free interactive tool to instantly calculate "
               "what poodle training will cost you based on your location, your dog’s age, "
               "and the type of training program you choose."),
     "Poodle training costs depend mainly on location, the dog’s age, "
     "and the type of training program chosen."),
    (_sentence("Whether you’re starting with a new puppy or working on advanced obedience with an adult poodle, "
               "professional training is one of the best investments you can make."),
     "Professional training is a common step both for new puppies and for adult poodles "
     "working on advanced obedience."),
    (_sentence("so getting a personalized estimate before you commit to a trainer can save you real money"),
     "so it is worth comparing local quotes before committing to a trainer"),
    (_sentence("Training your poodle is a rewarding investment that enhances their behavior "
               "and strengthens your bond. But how much will it cost?"),
     "Training improves a poodle’s behavior and strengthens the owner-dog relationship. "
     "The cost varies widely."),
    (_sentence("Our Poodle Training Cost Estimator Tool helps you calculate tailored costs "
               "for obedience, tricks, or socialization classes."),
     "Obedience, trick, and socialization classes are each priced differently."),
    (_sentence("Training your poodle is a lifelong gift that fosters good behavior and confidence. "
               "Use our Poodle Training Cost Estimator Tool to plan your budget "
               "and start your poodle’s training journey today!"),
     "Training supports good behavior and confidence throughout a poodle’s life. "
     "Working out the budget in advance keeps the cost predictable."),
    # 原站把链接从单词中间断开（the A<a>merican Kennel Club…</a>），取文字后成了 "A merican"
    (_sentence("visit the A merican Kennel Club training resources"),
     "see the American Kennel Club training resources"),
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
    """把 ul/ol 转成一行一条的文本；整条就是一个链接的条目把地址也记下来。"""
    lines = []
    for item in node.find_all("li"):
        text = clean_text(item)
        if not text:
            continue
        # "Related Poodle Tools" 那种整条是一个链接的列表项，光留文字就丢了目标地址
        link = item.find("a")
        if link is not None and clean_text(link) == text and link.get("href"):
            text = f"{text}（{link['href']}）"
        lines.append(f"- {text}")
    return "\n".join(lines)


def node_to_text(node) -> str:
    """按标签类型把一个块转成文本：表格拍平、列表逐条列出、其余直接取文字。"""
    # figure 既可能是表格（wp-block-table）也可能是配图，有表格的才要
    table = node if node.name == "table" else node.find("table")
    if table is not None:
        return table_to_text(table)

    if node.name in {"ul", "ol"}:
        return list_to_text(node)

    if node.name == "figure":
        return ""  # 不含表格的 figure 就是配图，不要

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


def join_title(section: str, sub: str) -> str:
    """把大标题和小标题拼起来，比如 "FAQs About Poodle Training Costs | 具体某个问题"。"""
    if section and sub:
        return f"{section} | {sub}"
    return sub or section


# ---------------------------------------------------------------- FAQ 列表

def is_qa_list(node) -> bool:
    """
    判断一个列表是不是"问答列表"：每个 li 都以 <strong> 开头（问题），后面跟答案。
    页面结尾的 FAQ 用的就是这种写法，需要一问一行地拆开。
    """
    items = node.find_all("li")
    if not items:
        return False
    return all(item.find("strong") is not None for item in items)


def qa_list_blocks(node, section: str) -> list[tuple[str, str]]:
    """把问答列表拆成一条条 (问题, 答案)。"""
    blocks = []
    for item in node.find_all("li"):
        question = clean_text(item.find("strong"))
        full_text = clean_text(item)
        # 问题在最前面，从整条文字里切掉问题就剩答案
        answer = full_text[len(question):].strip() if full_text.startswith(question) else full_text
        blocks.append((join_title(section, question), answer))
    return blocks


# ---------------------------------------------------------------- 正文遍历

def extract_blocks(html: str) -> list[dict]:
    """把一篇文章的 HTML 拆成若干条 {"title": ..., "description": ...}。"""
    soup = BeautifulSoup(html, "html.parser")
    content = soup.select_one(".entry-content") or soup.find("article") or soup.body
    if content is None:
        return []

    # 开头那几段在任何标题之前，用文章大标题兜底
    page_title = clean_text(soup.select_one("h1.entry-title")) or clean_text(soup.find("h1"))

    blocks: list[tuple[str, str]] = []
    section = ""                # 当前 h2 大标题
    sub = ""                    # 当前 h3/h4 小标题
    paragraphs: list[str] = []  # 当前小节攒下的正文
    in_promo = False            # 当前是不是在 "Related Poodle Tools" 这类推广小节里

    def flush() -> None:
        """把攒着的"标题 + 后面几段"结算成一条记录。"""
        nonlocal paragraphs
        if paragraphs:
            blocks.append((join_title(section, sub) or page_title, "\n".join(paragraphs)))
        paragraphs = []

    # 只遍历正文的直接子节点：WordPress 输出的是平铺结构，标题和段落一个挨一个
    for node in content.find_all(recursive=False):
        classes = set(node.get("class", []))
        node_id = node.get("id", "")
        if node.name in SKIP_TAGS or classes & SKIP_CLASSES or node_id.startswith(SKIP_ID_PREFIX):
            continue

        # 遇到新标题，先把上一节结算掉；h2 会把 h3 的小标题清空
        if node.name == "h2":
            flush()
            section, sub = clean_text(node), ""
            in_promo = bool(PROMO_SECTION.match(section))
            continue

        # "Related Poodle Tools" 这类小节整节跳过，直到下一个 h2
        if in_promo:
            continue

        if node.name in {"h3", "h4"}:
            flush()
            sub = clean_text(node)
            continue

        # FAQ 那种"<strong>问题</strong><br>答案"的列表，一问一条单独存
        if node.name in {"ul", "ol"} and is_qa_list(node):
            flush()
            blocks.extend(qa_list_blocks(node, join_title(section, sub)))
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
    """从 URL 里取最后一段当文件名，比如 .../poodle-training-cost-estimator/ -> poodle-training-cost-estimator。"""
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
