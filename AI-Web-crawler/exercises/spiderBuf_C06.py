# coding=utf-8

# @Author: spiderbuf

import requests

import time

import random

import hashlib

import json

import re

import base64

import numpy as np

from lxml import etree

from pathlib import Path


base_url = 'https://spiderbuf.cn/challenge/scraper-practice-c06'

# 输出目录固定在脚本旁边，不受启动时工作目录影响；不存在就自动建
outdir = Path(__file__).resolve().parent / 'data' / 'c06'
outdir.mkdir(parents=True, exist_ok=True)


# 用户行为检测及模拟浏览器对抗
# 加载更多按钮
# 配置请求 https://spiderbuf.cn/static/js/c06.min.js
# 请求数据参考（混淆后的原文，只留开头示意，全文见上面的 URL）：
# const _0x3062=['VmhaaE8=','Y29uc3RydWN0b3I=','aW5mbw==', ... ];(function(_0x230a78,_0x3062f0){...}(_0x3062,0xf7));
#
# 关键点：
#
# 1) 反混淆的办法和 C05 那关不同。这里是 javascript-obfuscator 的「字符串数组 +
#    轮转 + base64」套路：数组元素先 base64 编码，运行时再按固定次数左轮转，
#    取值函数 _0xe95a(i) = decodeURIComponent(atob(rotated[i]))。
#    轮转次数不是字面量 0xf7 —— 数组自检那段的 getCookie 里有个
#    _0x89f555(_0xe95a3d, _0x3062f0) 会用 ++0xf7 去调轮转函数，
#    而轮转是 while(--n)，所以实际左移 247 次。照着做就能还原（见 deobfuscate()）。
#
# 2) 还原后 page()（就是「加载更多」按钮 onclick 调的那个）等价于：
#
#        var x_map = new Map();
#        document.addEventListener('mousemove', e => {
#            x_map.set(e.clientX, e.clientX);        // 键是 clientX，重复的横坐标不计数
#        });
#
#        function page() {
#            const btn = document.querySelector('.btn-page');
#            if (btn) btn.parentElement.removeChild(btn);
#            const rnd = Math.floor(Math.random() * 8000 + 2000);   // [2000, 10000)
#            const ts  = Math.round(Date.now() / 1000);
#            const sig = md5(rnd + 'spiderbuf' + ts).toString();
#            fetch('scraper-practice-c06', {
#                method: 'POST',
#                body: JSON.stringify({random: rnd, timestamp: ts, signture: sig})
#            }).then(r => r.json()).then(data => {
#                const itemsDiv = document.querySelector('#items');
#                data.forEach(item => {
#                    const div = document.createElement('div');
#                    div.style.margin = '30px 0';
#                    var rating = item.rating;
#                    if (x_map.size < 2 || navigator.webdriver) {
#                        rating = Math.floor(Math.random() * 20 + 70) / 10;   // 投毒：7.0 ~ 8.9
#                    }
#                    div.innerHTML = `<h2>${item.title}</h2>... 豆瓣评分：${rating} ...`;
#                    itemsDiv.appendChild(div);
#                });
#                x_map.clear();          // 每次渲染完清空，下一次点击要重新攒鼠标轨迹
#            });
#        }
#
#    这一关的「用户行为检测」全在最后那个 if 里：鼠标没在两个以上的横坐标上动过，
#    或者 navigator.webdriver 为真，页面上显示的评分就被换成 7.0~8.9 的随机数。
#    注意接口返回的仍然是真数据 —— 投毒只发生在渲染这一步。所以拿 requests
#    直接打接口反而绕开了整套检测，selenium 不做对抗才会中招。
#    另外 signture 是 signature 的笔误，别拼对了。
#
# 3) 接口就是页面自己这个 URL，POST 过去返回 JSON。实测：
#      · 裸 POST 返回 400 Bad request，必须先 GET 一次页面拿到会话 cookie
#        （_asd2sdf99），带着它再 POST 才有数据 —— 所以用 Session 串起来。
#      · 服务端并不校验 signture，签名算错照样返回数据。但按 JS 复刻一遍才是
#        这一关的正经解法，也免得哪天服务端补上校验。
#      · 返回固定是第 2 页那 10 条，点几次都一样，没有真正的翻页。
#    合计 10（页面静态渲染）+ 10（接口）= 20 条，评分总和 182.8。
#
# 4) 页面上那个按钮现在长这样，没有 .btn-page 这个类：
#        <div class="py-2 px-4 ... cursor-pointer" onclick="page();">加载更多>></div>
#    也就是说 querySelector('.btn-page') 恒为 null，按钮点完不会消失。
#    selenium 定位它别指望 class，按 onclick 里的 page() 找最稳。
#
# 另外尝试用 selenium 自动化脚本，模拟浏览器点击按钮行为，获取js渲染数据


myheaders = {

    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36 Edg/151.0.0.0'}


# 混淆器生成的字符串数组：const _0x3062=[ ... ];
ARRAY_RE = re.compile(r'const\s+_0x\w+\s*=\s*\[(.*?)\];', re.S)

# 数组里的单引号字符串
STRING_RE = re.compile(r"'([^']*)'")

# 左轮转次数，来自 while(--n) 里的 ++0xf7
ROTATE = 0xf7


def deobfuscate(js):
    '''把 c06.min.js 里的字符串数组轮转、解码，返回 {下标: 明文}。
    平时用不到，是留着站点换了混淆参数时对照用的'''

    m = ARRAY_RE.search(js)

    if m is None:

        raise ValueError('没找到混淆字符串数组，站点结构可能变了')

    items = STRING_RE.findall(m.group(1))

    # 左轮转：push(shift()) 重复 ROTATE 次
    rotated = items[ROTATE % len(items):] + items[:ROTATE % len(items)]

    plain = {}

    for i, s in enumerate(rotated):

        try:

            # JS 那边是 decodeURIComponent(escape(atob(s)))，等价于按 UTF-8 解字节
            plain[hex(i)] = base64.b64decode(s).decode('utf-8')

        except Exception:

            continue

    return plain


def newSession():
    '''先 GET 一次页面换会话 cookie —— 不带 cookie 直接 POST 会吃 400 Bad request'''

    session = requests.Session()

    session.headers.update(myheaders)

    resp = session.get(base_url, timeout=15)

    resp.raise_for_status()

    return session, resp.text


def signPayload():
    '''复刻 JS 里的取参和签名：md5(random + 'spiderbuf' + timestamp)'''

    random_value = int(random.random() * 8000 + 2000)

    timestamp = round(time.time())

    md5_hash = hashlib.md5()

    md5_hash.update(f'{random_value}spiderbuf{timestamp}'.encode('utf-8'))

    return {

        'random': random_value,

        'timestamp': timestamp,

        'signture': md5_hash.hexdigest(),      # 站点自己拼错的，照抄

    }


def parseHTML(html):
    '''从 #items 里取 (标题, 评分)。
    静态 HTML 和 selenium 渲染后的 DOM 结构一致，两边都能用这一套 xpath'''

    root = etree.HTML(html)

    movies = []

    for div in root.xpath('//div[@id="items"]/div'):

        title = div.xpath('.//h2/text()')

        rating = div.xpath('.//div[@class="detail"]/p[1]/span[2]/text()')

        if title and rating:

            movies.append({'title': title[0].strip(), 'rating': rating[0].strip()})

    return movies


def loadMore(session):
    '''打「加载更多」背后的接口，拿到第 2 页那 10 条真数据'''

    resp = session.post(base_url, json=signPayload(), timeout=15)

    resp.raise_for_status()

    return json.loads(resp.text)


def loadMovies(file_name=''):
    '''不开浏览器：页面静态那 10 条 + 接口那 10 条，合起来就是全部'''

    session, html = newSession()

    movies = parseHTML(html)

    print('页面静态条目：', len(movies))

    more = loadMore(session)

    print('接口返回条目：', len(more))

    # 接口每次都返回同一批，重复点也只是重复渲染，按标题去重
    seen = {m['title'] for m in movies}

    for item in more:

        if item['title'] in seen:

            continue

        seen.add(item['title'])

        movies.append({'title': item['title'], 'rating': item['rating']})

    if file_name != '':

        with open(file_name, 'w', encoding='utf-8') as f:

            json.dump(movies, f, ensure_ascii=False, indent=2)

    return movies


def report(movies):

    ratings = [float(m['rating']) for m in movies]

    print('电影数量：', len(ratings))

    print('评分总和：', round(sum(ratings), 1))

    print('评分平均值：', round(np.mean(ratings), 2))


# 抢在页面脚本之前把 navigator.webdriver 抹掉。
# 只加 --disable-blink-features=AutomationControlled 在新版 Chrome 上不一定够，
# CDP 注入这一段是在每个新文档的最开始执行的，c06.min.js 读到的就是 undefined
HIDE_WEBDRIVER_JS = "Object.defineProperty(navigator, 'webdriver', {get: () => undefined});"

# 按钮没有稳定的 class，只有 onclick="page();" 是不变的
BTN_XPATH = '//*[contains(@onclick, "page()")]'

# 渲染后的条目数，用来判断「加载更多」到底加载出来没有
COUNT_JS = "return document.querySelectorAll('#items > div').length;"


def getHTMLBySelenium(url, file_name=''):
    '''备用方案：真的开浏览器点按钮，等 JS 渲染完再取 page_source。

    要过两道检测，缺一道拿到的评分就是 7.0~8.9 的随机数：
      · navigator.webdriver 必须为假 —— 用 CDP 在文档加载前改掉
      · x_map.size 必须 >= 2 —— 鼠标得在至少两个不同的 clientX 上动过，
        而且 x_map 在每次渲染后会被 clear()，所以轨迹要在点击之前现攒'''

    # 延迟导入：主流程不需要 selenium，没装也不影响脚本运行
    from selenium import webdriver

    from selenium.webdriver import ActionChains

    from selenium.webdriver.common.by import By

    from selenium.webdriver.support.ui import WebDriverWait

    options = webdriver.ChromeOptions()

    options.add_argument('--disable-blink-features=AutomationControlled')

    options.add_experimental_option('excludeSwitches', ['enable-automation'])

    options.add_experimental_option('useAutomationExtension', False)

    client = webdriver.Chrome(options=options)

    client.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument',

                           {'source': HIDE_WEBDRIVER_JS})

    print('Getting page...')

    client.get(url)

    time.sleep(2)

    print('navigator.webdriver =', client.execute_script('return navigator.webdriver;'))

    before = client.execute_script(COUNT_JS)

    print('点击前条目数：', before)

    btn = client.find_element(By.XPATH, BTN_XPATH)

    # 先把鼠标挪到按钮上，再左右晃几下 —— 每个新的横坐标都会往 x_map 里塞一个键。
    # 别用同一个 dx 来回蹭，clientX 撞上了 Map 不会增长
    ActionChains(client).move_to_element(btn).perform()

    for dx in (-60, 25, -40, 70):

        ActionChains(client).move_by_offset(dx, 0).perform()

        time.sleep(0.2)

    size = client.execute_script('return window.x_map ? window.x_map.size : -1;')

    print(f'点击前 x_map.size = {size}（需要 >= 2，否则评分会被换成随机数）')

    if size < 2:

        client.quit()

        raise RuntimeError(f'鼠标轨迹只攒到 {size} 个横坐标，这次点下去拿到的是假数据')

    btn.click()

    print('Button clicked...')

    WebDriverWait(client, 15).until(

        lambda c: c.execute_script(COUNT_JS) > before)

    time.sleep(1)

    print('点击后条目数：', client.execute_script(COUNT_JS))

    html = client.page_source

    client.quit()

    if file_name != '':

        with open(file_name, 'w', encoding='utf-8') as f:

            f.write(html)

    return html


def verify(rendered, movies):
    '''拿浏览器渲染出来的评分对一遍接口的真数据。
    对不上就说明上面那两道检测没绕干净，页面给的是投毒后的随机评分'''

    truth = {m['title']: m['rating'] for m in movies}

    bad = [r for r in rendered

           if r['title'] in truth and float(r['rating']) != float(truth[r['title']])]

    if bad:

        print('评分被投毒的条目：')

        for r in bad:

            print(f"  {r['title'][:24]}  页面 {r['rating']}  实际 {truth[r['title']]}")

    else:

        print('渲染结果与接口数据一致，反检测生效')

    return not bad


if __name__ == '__main__':

    movies = loadMovies(outdir / 'c06.json')

    for m in movies:

        print(m['rating'], m['title'])

    report(movies)

    # 备用方案：走浏览器点「加载更多」，再从渲染后的 DOM 里取评分
    html = getHTMLBySelenium(base_url, outdir / 'c06.html')

    rendered = parseHTML(html)

    report(rendered)

    verify(rendered, movies)


# 来源：https://spiderbuf.cn/code/scraper-practice-c06
# 爬虫练习网站：Spiderbuf
