# https://spiderbuf.cn/challenge/javascript-confuse-encrypt-reverse
# js加密混淆及简单反调试

# # 需要爬取的数据元素参考
# <main>
# <div>
# <div class="container">
# <div class="row"style="margin-top: 30px">
# <h2>由NordPass发布的2022年全球最常用密码列表</h2>
# <h2>Top 200 most common passwords.</h2>
# <p>以下是2022年最常见的200个密码。</p>
# <p>我们了解到,尽管网络安全意识不断增强,但旧习惯很难改掉。研究表明,人们仍然使用弱密码来保护自己的账户。</p>
# <p>今年,我们研究了文化如何影响密码。</p>
# <table id="dataContent" class="table"
# <thead>
# <tr>
# <th>排名</th>
# <th>密码</th>
# <th>破解耗时</th>
# <th>使用数</th>
# </tr>
# </thead>
# <tbody>
# <tr>
# <td>1</td>
# <td>password</td>
# <td>< 1 Second</td>
# <td>4929113</td>
# </tr>
# <tr></tr>
# <tr></tr>
# <tr></tr>
# <tr></tr>


# # 请求体参考
# User-Agent
# Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36

# # 思路
# 1. 页面上 <tbody> 是空的，表格是 /static/js/xxx.min.js 里的 JS 塞进去的，
#    所以直接解析 HTML 拿不到任何一行，得去抓那个 js。
# 2. js 被混淆过，但只是“换了个写法”，没有真加密：
#    key 和字符串写成 pa... 和 '<\x201\x20Second'，数字写成 0x4b3659，
#    还有 document['querySelector']("tnetnoCatad#".split("").reverse().join("")) 这种倒着写的选择器。
#    把转义还原、十六进制转十进制，var data=[...] 就是一个普通的 JSON 数组。
# 3. 页面里那段 setInterval(function(){debugger;},500) 是反调试，
#    只在浏览器开着开发者工具时碍事；requests 不执行 JS，对我们没有影响。

import re
import json
from pathlib import Path
from urllib.parse import urljoin

import requests
from lxml import etree


# 输出目录固定在脚本旁边，不受启动时工作目录影响；不存在就自动建
outdir = Path(__file__).resolve().parent / 'data' / 'h04'
outdir.mkdir(parents=True, exist_ok=True)


base_url = 'https://spiderbuf.cn/challenge/javascript-confuse-encrypt-reverse'

myheaders = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36'}

# \uXXXX、\xNN 和 \n 这类转义
ESCAPE = re.compile(r'\\u([0-9a-fA-F]{4})|\\x([0-9a-fA-F]{2})|\\(.)')
SIMPLE_ESCAPES = {'n': '\n', 't': '\t', 'r': '\r', 'b': '\b', 'f': '\f', 'v': '\v', '0': '\0'}


def getHTML(url, file_name=''):
    resp = requests.get(url, headers=myheaders, timeout=10)
    resp.raise_for_status()
    # 响应头未必带 charset，按页面实际编码解码，避免中文乱码
    resp.encoding = resp.apparent_encoding or 'utf-8'
    html = resp.text

    if file_name != '':
        with open(file_name, 'w', encoding='utf-8') as f:
            f.write(html)

    return html


def findDataScript(html):
    """
    页面里的 js 有两类：站点公共的 https://spiderbuf.cn/static/js/site.v3.min.js，
    以及塞表格数据的那个相对路径 /static/js/udSL29.min.js。
    按相对路径找，文件名换了也不用改代码。
    """
    root = etree.HTML(html)
    srcs = root.xpath('//script[starts-with(@src, "/static/js/")]/@src')
    print(srcs)

    # 只要第一个就行，后面可能还有 site.v3.min.js
    for src in srcs:
        if 'site.' not in src:
            # 获取到的 src 是相对路径，拼成完整 URL
            return urljoin(base_url, src)

    return ''


def unescape(text):
    """把 \\u0070 \\x20 这类转义还原成真正的字符"""
    def replace(m):
        if m.group(1):
            return chr(int(m.group(1), 16))
        if m.group(2):
            return chr(int(m.group(2), 16))
        return SIMPLE_ESCAPES.get(m.group(3), m.group(3))

    return ESCAPE.sub(replace, text)


def js_to_json(text):
    """
    JS 对象字面量转合法 JSON：单引号字符串换成双引号并还原转义，0x 十六进制转十进制。
    逐字符扫描而不是直接正则全局替换，是为了只动字符串内部，不误伤结构里的引号。
    """
    out = []
    i = 0
    n = len(text)

    while i < n:
        ch = text[i]

        if ch == '"' or ch == "'":
            quote = ch
            i += 1
            buf = []
            while i < n and text[i] != quote:
                if text[i] == '\\':      # 转义序列整体收进来，别被 \' 骗着提前结束
                    buf.append(text[i:i + 2])
                    i += 2
                else:
                    buf.append(text[i])
                    i += 1
            i += 1                       # 跳过结束引号
            out.append(json.dumps(unescape(''.join(buf)), ensure_ascii=False))

        elif ch == '0' and i + 1 < n and text[i + 1] in 'xX':
            j = i + 2
            while j < n and text[j] in '0123456789abcdefABCDEF':
                j += 1
            out.append(str(int(text[i:j], 16)))
            i = j

        else:
            out.append(ch)
            i += 1

    # 兜底：混淆器可能留下没加引号的 key，如 {id:1}
    return re.sub(r'([{,])\s*([A-Za-z_$][\w$]*)\s*:', r'\1"\2":', ''.join(out))


def parseJS(js):
    """从混淆过的 js 里取出 var data=[...] 并解析成字典列表"""
    m = re.search(r'var\s+data\s*=\s*(\[.*?\])\s*;', js, re.S)
    if m is None:
        return []

    return json.loads(js_to_json(m.group(1)))


if __name__ == '__main__':

    # 获取主页面
    html = getHTML(base_url, str(outdir / 'h04.html'))

    js_url = findDataScript(html)
    print(js_url)

    js = getHTML(js_url, str(outdir / js_url.split('/').pop()))
    rows = parseJS(js)

    # 表头对应 ranking / passwd / time_to_crack_it / used_count
    print('排名\t密码\t\t破解耗时\t使用数')
    for row in rows:
        print('%s\t%s\t%s\t%s' % (
            row.get('ranking', ''),
            row.get('passwd', '').ljust(16),
            row.get('time_to_crack_it', '').ljust(12),
            row.get('used_count', '')))

    print('共 %d 条' % len(rows))
