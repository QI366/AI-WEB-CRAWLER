# coding=utf-8

# @Author: spiderbuf

import requests

from lxml import etree

import time

import random

import base64

import json

import re

import numpy as np

from pathlib import Path

from urllib.parse import urljoin


base_url = 'https://spiderbuf.cn/challenge/scraper-practice-c04'

# 输出目录固定在脚本旁边，不受启动时工作目录影响；不存在就自动建
outdir = Path(__file__).resolve().parent / 'data' / 'c04'
outdir.mkdir(parents=True, exist_ok=True)


# 关键点：
# 接口请求：获取<script src="/static/js/lhY3nm7.min.js"></script>
# 请求：https://spiderbuf.cn/static/js/lhY3nm7.min.js
# 获取其中的  const _0x4b9a75
# function _0xc4fa() {
#     const _0x4b9a75 = [...];
#     _0xc4fa = function() {
#         return _0x4b9a75;
#     }
#     ;
#     return _0xc4fa();
# }
#
# 再走base64解码，得到一个数组
#
# 实测补充（反混淆后读出来的真实逻辑）：
#
# 1) 那串 base64 末尾有 2 个垃圾字符，直接 b64decode 会在 JSON 尾部多出 '\x0bd'。
#    JS 自己也要削掉再补回填充：
#        decode(a.slice(0, -2) + '==')
#    所以 Python 这边必须同样 payload[:-2] + '=='，否则 json.loads 报错。
#
# 2) 验证码是纯前端的，checkCaptcha() 只做两件事：
#        if (navigator.webdriver) -> 报错
#        if (记录到的鼠标坐标数 < 10) -> 报错
#    数据在 JS 文件里已经是完整的，不点勾选框也拿得到 —— 验证码只是障眼法。
#
# 3) 渲染出来的模板是：
#        <div class="stats">
#            <span>阅读数: {reads}</span>
#            <span>点赞数: {likes}</span>
#            <span>转发数: {shares}</span>
#            <span>评论数: <span class="comments">
#                <span class="digit">5</span><span class="digit">0</span>
#            </span></span>
#        </div>
#    评论数被拆成「一位数字一个 span」，所以走 DOM 解析时要把 digit 拼回来。
#    直接读 JSON 就没这个麻烦。

myheaders = {

    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36 Edg/151.0.0.0'}


# 站内脚本（排除 google/统计等外链），文件名以后可能变，所以从页面里现取
SCRIPT_RE = re.compile(r'<script[^>]+src="((?:/|https://spiderbuf\.cn/)static/js/[^"]+)"')

# 混淆器生成的字符串数组：function _0xc4fa(){const _0x4b9a75=[ ... ];
ARRAY_RE = re.compile(r'function\s+_0x\w+\(\)\s*\{\s*const\s+_0x\w+\s*=\s*\[(.*?)\];', re.S)

# 数组里的单引号字符串，容忍 \' 和 \x41 这类转义
STRING_RE = re.compile(r"'((?:[^'\\]|\\.)*)'")


def scriptURLs(session):
    '''页面里所有站内脚本地址。除了关卡脚本还有站点公共脚本 site.v3.min.js，
    所以不按文件名猜，全部列出来逐个试'''

    resp = session.get(base_url, timeout=15)

    resp.raise_for_status()

    urls = [urljoin(base_url, src) for src in SCRIPT_RE.findall(resp.text)]

    if not urls:

        raise ValueError('页面里没找到 /static/js/ 下的脚本，站点结构可能变了')

    return urls


def extractPayload(js):
    '''取出字符串数组里那串 base64（它是数组中最长的元素）。
    脚本里没有混淆数组就返回 None'''

    m = ARRAY_RE.search(js)

    if m is None:

        return None

    items = STRING_RE.findall(m.group(1))

    return max(items, key=len) if items else None


def decode(b64):
    '''对应 JS 里的 decode()：atob 之后按 UTF-8 解码。
    调用方负责先把末尾 2 个垃圾字符削掉、补上 == 填充'''

    return base64.b64decode(b64).decode('utf-8')


def loadPosts(file_name=''):
    '''不开浏览器，直接从混淆 JS 里把微博数据抠出来'''

    session = requests.Session()

    session.headers.update(myheaders)

    posts = None

    for js_url in scriptURLs(session):

        resp = session.get(js_url, timeout=15)

        resp.raise_for_status()

        payload = extractPayload(resp.text)

        if payload is None:

            continue

        try:

            # JS 原文就是 decode(a.slice(0, -2) + '==')，末尾 2 位是干扰
            posts = json.loads(decode(payload[:-2] + '=='))

        except (ValueError, UnicodeDecodeError):

            # 这个脚本的最长字符串不是数据，换下一个
            continue

        print('数据来自：', js_url)

        break

    if posts is None:

        raise ValueError('所有站内脚本都没解出数据，站点结构可能变了')

    if file_name != '':

        with open(file_name, 'w', encoding='utf-8') as f:

            json.dump(posts, f, ensure_ascii=False, indent=2)

    return posts


def report(posts):

    print('微博条数：', len(posts))

    for key, label in [('reads', '阅读数'), ('likes', '点赞数'),
                       ('shares', '转发数'), ('comments', '评论数')]:

        values = [p[key] for p in posts]

        print(f'  {label}  总和={sum(values):<8} 平均={np.mean(values)}')

    # 原题要的是「阅读数 + 评论数」的平均值
    results = [p['reads'] + p['comments'] for p in posts]

    print('阅读数+评论数 的平均值：', np.average(results))


def parseHTML(html):
    '''从渲染后的 DOM 取「阅读数 + 评论数」。
    只对 selenium 拿到的源码有效，requests 取到的静态 HTML 里 #posts 是空的'''

    root = etree.HTML(html)

    items = root.xpath('//div[@class="stats"]')

    results = []

    for item in items:

        spans = item.xpath('.//span')

        # spans[0]=阅读数 spans[1]=点赞数 spans[2]=转发数 spans[3]=评论数
        reads = int(re.findall(r'\d+', spans[0].text)[0])

        # 评论数被拆成一位一个 <span class="digit">，取整段文本再把数字拼回来
        text = spans[3].xpath('string(.)')

        comments = int(''.join(re.findall(r'\d+', text)))

        results.append(reads + comments)

    return results


def getHTMLBySelenium(url, file_name=''):
    '''备用方案：真的去过一遍验证码。
    要点是绕开 checkCaptcha() 的两道前端检查 ——
      navigator.webdriver 必须为假，且鼠标要在框内走够 10 个不同坐标'''

    # 延迟导入：主流程不需要 selenium，没装也不影响脚本运行
    from selenium import webdriver

    from selenium.webdriver import ActionChains

    from selenium.webdriver.common.by import By

    options = webdriver.ChromeOptions()

    options.add_argument('disable-infobars')

    options.set_capability('goog:loggingPrefs', {'browser': 'ALL'})

    # 改变navigator.webdriver 属性值
    options.add_argument('--disable-blink-features=AutomationControlled')

    client = webdriver.Chrome(options=options)

    print('Getting page...')

    client.get(url)

    time.sleep(3)

    # 模拟用户在页面上滑动光标：mousemove 监听挂在 #captcha_container 上，
    # 必须在框内走动，且累计 ≥10 个不同坐标才算数
    actionChains = ActionChains(client)

    actionChains.move_by_offset(430, 330)

    for i in range(20):

        step = random.randint(1, 10)

        actionChains.move_by_offset(step, step).perform()

    checkbox = client.find_element(By.ID, 'captcha')

    checkbox.click()

    print('Checkbox clicked...')

    time.sleep(3)

    html = client.page_source

    client.quit()

    if file_name != '':

        with open(file_name, 'w', encoding='utf-8') as f:

            f.write(html)

    return html


if __name__ == '__main__':

    posts = loadPosts(outdir / 'c04.json')

    for p in posts:

        print(p['title'], p['reads'], p['likes'], p['shares'], p['comments'])

    report(posts)

    # 备用：走浏览器过验证码，再从渲染后的表格里算
    # html = getHTMLBySelenium(base_url, outdir / 'c04.html')
    # print(np.average(parseHTML(html)))


# 来源：https://spiderbuf.cn/code/scraper-practice-c04
# 爬虫练习网站：Spiderbuf
