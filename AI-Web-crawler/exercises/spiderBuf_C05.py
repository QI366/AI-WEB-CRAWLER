# coding=utf-8

# @Author: spiderbuf

import requests

from lxml import etree

import time

import base64

import hashlib

import json

import re

import numpy as np

from pathlib import Path

from urllib.parse import urljoin

from Crypto.Cipher import AES     # pip 包名是 pycryptodome，不是 crypto/pycrypto


base_url = 'https://spiderbuf.cn/challenge/scraper-practice-c05'

# 输出目录固定在脚本旁边，不受启动时工作目录影响；不存在就自动建
outdir = Path(__file__).resolve().parent / 'data' / 'c05'
outdir.mkdir(parents=True, exist_ok=True)


# 关键点：
# 接口请求：获取形如<script src="/static/js/c05.min.js"></script>
# 请求：https://spiderbuf.cn/static/js/c05.min.js
# 获取其中的
# function _0x2d8e() {
#     const _0x1f7dc0 = [..., 'mySecretKey123', 'Utf8', ..., 'U2FsdGVkX19Ria8/...', ...];
#     _0x2d8e = function() {
#         return _0x1f7dc0;
#     }
#     ;
#     return _0x2d8e();
# }
#
# 实测更正：这一关不是 base64，是 AES。
#
# 1) 载荷以 U2FsdGVkX1 开头 —— 那是 ASCII 'Salted__' 的 base64，是
#    CryptoJS / OpenSSL 的加密容器格式。base64 解码只能得到二进制，解不出 JSON。
#    JS 原文（反混淆后）是：
#        CryptoJS.AES.decrypt(载荷, 'mySecretKey123').toString(CryptoJS.enc.Utf8)
#
# 2) 容器布局：
#        [0:8]   固定字面量 b'Salted__'
#        [8:16]  8 字节随机盐
#        [16:]   AES-256-CBC 密文
#    密钥和 IV 不是口令本身，要用 OpenSSL 的 EVP_BytesToKey 从「口令 + 盐」
#    反复 MD5 派生出 48 字节，前 32 当密钥、后 16 当 IV。这就是 evpBytesToKey()。
#
# 3) 这关的密文解出来是干净 JSON，没有 C04 那种末尾干扰字符，不用切片。
#
# 4) 滑块同样是纯前端障眼法。反混淆后的 mouseup 校验是：
#        if (left < 207 || left == 217)              -> 重置，失败
#        if (Date.now()/1000 - start < 2)            -> 重置，失败
#        if (x_map.size < 2)                         -> 直接 return，不渲染
#    换算过来：
#      · left 落在 [207, 360] 且不等于 217 就算过（maxX = 容器400 - 滑块40 = 360）
#        —— 217 正是视觉缺口的位置，「拖得分毫不差」反而判失败，是反机器的小心机
#      · start 是页面加载时就设的，不是 mousedown，所以打开页面等 2 秒就已满足
#      · x_map 累积的是每次 mousemove 的 clientX，分几步拖就够
#    但数据早就完整躺在 JS 文件里了，不拖滑块照样拿得到。

myheaders = {

    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36 Edg/151.0.0.0'}


# 站内脚本（排除 google/统计等外链），文件名以后可能变，所以从页面里现取
SCRIPT_RE = re.compile(r'<script[^>]+src="((?:/|https://spiderbuf\.cn/)static/js/[^"]+)"')

# 混淆器生成的字符串数组：function _0x2d8e(){const _0x1f7dc0=[ ... ];
ARRAY_RE = re.compile(r'function\s+_0x\w+\(\)\s*\{\s*const\s+_0x\w+\s*=\s*\[(.*?)\];', re.S)

# 数组里的单引号字符串，容忍 \' 和 \x41 这类转义
STRING_RE = re.compile(r"'((?:[^'\\]|\\.)*)'")

# CryptoJS/OpenSSL 容器的 base64 开头，即 b'Salted__'
SALTED_PREFIX = 'U2FsdGVkX1'


def evpBytesToKey(passphrase, salt, key_len=32, iv_len=16):
    '''OpenSSL 的 EVP_BytesToKey（MD5、单轮），CryptoJS 用口令加密时就是这套。
    反复 MD5(上一段 + 口令 + 盐) 拼够 48 字节，前 32 是密钥，后 16 是 IV'''

    material = b''

    prev = b''

    while len(material) < key_len + iv_len:

        prev = hashlib.md5(prev + passphrase + salt).digest()

        material += prev

    return material[:key_len], material[key_len:key_len + iv_len]


def cryptoJSDecrypt(b64, passphrase):
    '''等价于 JS 的 CryptoJS.AES.decrypt(b64, passphrase).toString(CryptoJS.enc.Utf8)'''

    raw = base64.b64decode(b64)

    if raw[:8] != b'Salted__':

        raise ValueError('不是 CryptoJS/OpenSSL 的加密容器')

    salt, ciphertext = raw[8:16], raw[16:]

    key, iv = evpBytesToKey(passphrase.encode('utf-8'), salt)

    plain = AES.new(key, AES.MODE_CBC, iv).decrypt(ciphertext)

    # 去掉 PKCS7 填充：最后一个字节的值就是填充长度
    return plain[:-plain[-1]].decode('utf-8')


def findObfuscatedArray(session):
    '''逐个站内脚本找那个含加密载荷的混淆字符串数组，返回数组元素列表'''

    resp = session.get(base_url, timeout=15)

    resp.raise_for_status()

    for src in SCRIPT_RE.findall(resp.text):

        js_url = urljoin(base_url, src)

        body = session.get(js_url, timeout=15).text

        if SALTED_PREFIX not in body:

            continue

        m = ARRAY_RE.search(body)

        if m is None:

            continue

        print('载荷脚本：', js_url)

        return STRING_RE.findall(m.group(1))

    raise ValueError('没找到含加密载荷的脚本，站点结构可能变了')


def loadFlights(file_name=''):
    '''不开浏览器、不拖滑块，直接从混淆 JS 里解出航班数据'''

    session = requests.Session()

    session.headers.update(myheaders)

    items = findObfuscatedArray(session)

    payload = next((s for s in items if s.startswith(SALTED_PREFIX)), None)

    if payload is None:

        raise ValueError('数组里没有 Salted__ 载荷')

    # 口令也在同一个数组里。与其硬写 'mySecretKey123'，不如拿每个元素挨个试 ——
    # 解错的口令过不了 PKCS7 填充和 UTF-8 解码，能解出合法 JSON 的就是它
    for candidate in items:

        try:

            data = json.loads(cryptoJSDecrypt(payload, candidate))

        except Exception:

            continue

        print('口令：', candidate)

        break

    else:

        raise ValueError('数组里所有元素都当不了口令，加密方式可能变了')

    flights = data['flights']

    if file_name != '':

        with open(file_name, 'w', encoding='utf-8') as f:

            json.dump(flights, f, ensure_ascii=False, indent=2)

    return flights


def report(flights):

    prices = [int(f['price']) for f in flights]

    print('航班数量：', len(prices))

    print('票价总和：', sum(prices))

    print('票价平均值：', round(np.mean(prices), 2))


def parseHTML(html):
    '''从渲染后的 DOM 取票价（第 3 列）。
    只对 selenium 拿到的源码有效，requests 取到的静态 HTML 里表格是空的'''

    root = etree.HTML(html)

    prices = []

    for tr in root.xpath('//tr'):

        tds = tr.xpath('./td')

        if len(tds) > 2:

            prices.append(int(tds[2].text))

    return prices


# 合法区间是 [207, 360]，瞄准中段，两边各留约 80px 余量。
# 别瞄 217：那是视觉缺口位置，恰好等于 217 会被判失败
TARGET_LEFT = 290

# 读回滑块当前的 style.left；还没拖过时是空字符串，按 0 算
READ_LEFT_JS = "return parseInt(document.getElementById('slider').style.left, 10) || 0;"


def getHTMLBySelenium(url, file_name=''):
    '''备用方案 2：真的去拖滑块，等 JS 渲染出表格再取 page_source。

    坑在于 move_by_offset 的位移和最终 style.left 不是一一对应的 ——
    Selenium 会在两点之间插值、指针坐标还要取整，实测同样的位移量
    落点会在几个像素之间浮动。所以不能「算好距离一把拖过去」，
    而要边拖边把 style.left 读回来按差值收敛，确认落在安全区再松手'''

    # 延迟导入：主流程不需要 selenium，没装也不影响脚本运行
    from selenium import webdriver

    from selenium.webdriver import ActionChains

    from selenium.webdriver.common.by import By

    client = webdriver.Chrome()

    print('Getting page...')

    client.get(url)

    # 这 3 秒同时也把 start 那道「距页面加载 >= 2 秒」的校验垫过去了
    time.sleep(3)

    slider = client.find_element(By.ID, 'slider')

    ActionChains(client).click_and_hold(slider).perform()

    # 先分三段粗拖：制造多个不同的 clientX，喂饱 x_map
    for _ in range(3):

        ActionChains(client).move_by_offset(TARGET_LEFT // 3, 0).perform()

        time.sleep(0.3)

    # 再按实际读数收敛到目标位置
    for _ in range(5):

        left = client.execute_script(READ_LEFT_JS)

        delta = TARGET_LEFT - left

        if delta == 0:

            break

        ActionChains(client).move_by_offset(delta, 0).perform()

        time.sleep(0.2)

    left = client.execute_script(READ_LEFT_JS)

    print(f'松手前 slider.style.left = {left}px（需要 [207, 360] 且 != 217）')

    if left < 207 or left == 217 or left > 360:

        client.quit()

        raise RuntimeError(f'滑块停在 {left}px，不在安全区，本次会被判失败')

    ActionChains(client).release().perform()

    print('Slider released...')

    time.sleep(3)

    rows = client.execute_script(

        "return document.querySelectorAll('#flightTable tbody tr').length;")

    print('渲染出的行数：', rows)

    html = client.page_source

    client.quit()

    if file_name != '':

        with open(file_name, 'w', encoding='utf-8') as f:

            f.write(html)

    return html


def decryptInBrowser(url, payload, passphrase):
    '''备用方案 3：懒得复刻 EVP_BytesToKey 的话，可以直接借页面自带的 CryptoJS。
    注意别去引用 _0x2d8e() 这种混淆出来的函数名和下标 —— 它们每次重新混淆都会变，
    把载荷和口令当参数传进去才稳'''

    from selenium import webdriver

    client = webdriver.Chrome()

    client.get(url)

    time.sleep(3)

    # 获取浏览器 console.log 里 CryptoJS 的报错信息，方便调试
    result = client.execute_script(

        'return CryptoJS.AES.decrypt(arguments[0], arguments[1])'

        '.toString(CryptoJS.enc.Utf8);',

        payload, passphrase)

    client.quit()

    return json.loads(result)['flights']


if __name__ == '__main__':

    flights = loadFlights(outdir / 'c05.json')

    for f in flights:

        print(f['from'], '->', f['to'], f['price'])

    report(flights)

    # 备用方案 2：走浏览器拖滑块，再从渲染后的表格里取第 3 列
    html = getHTMLBySelenium(base_url, outdir / 'c05.html')
    prices = parseHTML(html)
    print('票价平均值：', round(np.mean(prices), 2))


# 来源：https://spiderbuf.cn/code/scraper-practice-c05
# 爬虫练习网站：Spiderbuf
