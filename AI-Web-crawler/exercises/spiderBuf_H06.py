# coding=utf-8

# <script type="text/javascript" src="/static/js/md5.min.js"></script>
# <script type="text/javascript" src="/static/js/HfPro9C.min.js"></script>

# https://spiderbuf.cn/static/js/HfPro9C.min.js
# var user_agent = navigator.userAgent;
# if ((!navigator.webdriver) & (navigator.plugins.length > 0) & (user_agent.indexOf('headless') < 0)) {    
# console.log(navigator.webdriver);    
# console.log(navigator.plugins.length);    
# console.log(user_agent.indexOf('headless'));    
# var timeStamp = Math.trunc(new Date().getTime() / 1000);    
# var _md5 = md5(timeStamp);    
# var s = btoa(`${timeStamp},${_md5}`);
#     fetch("/challenge/selenium-fingerprint-anti-scraper/api/" + s).then(function (response) {        
# return response.json();
#     }).then(function (data) {        
# var dataContent = document.querySelector('#dataContent > tbody');        
# data.forEach((value, index) => {            
# var row = dataContent.insertRow();            
# var rankingCell = row.insertCell();            
# rankingCell.innerText = value.ranking;
#             var passwdCell = row.insertCell();            
# passwdCell.innerText = value.passwd;
#             var time_to_crackItCell = row.insertCell();            
# time_to_crackItCell.innerText = value.time_to_crack_it;
#             var used_countCell = row.insertCell();            
# used_countCell.innerText = value.used_count;
#         })
#     });
# }

# 浏览器模拟
# https://spiderbuf.cn/challenge/selenium-fingerprint-anti-scraper/api/MTc4NTk4MzY5NCxjNzcxNGUwYWFhNzM3ZDk1ODY4NWFmYzI3MzYwN2Y5YQ==
# 请求爬取数据

import base64

import hashlib

import json

import time

from pathlib import Path



import requests

from lxml import etree

# selenium 只在方案二里用，放到函数里再 import，没装也不影响方案一


# # 思路
# 这题的门槛在 HfPro9C.min.js 开头那个 if：
#     if ((!navigator.webdriver) & (navigator.plugins.length > 0) & (user_agent.indexOf('headless') < 0))
# 三个条件全是浏览器指纹 —— webdriver 标志位、插件数量、UA 里有没有 headless，
# 合起来就是一句话：你是不是被 selenium 开的、是不是无头模式。
#
# 但这个 if 只决定"浏览器要不要发那个 fetch"，它跑在客户端，服务端并不知道它跑没跑过。
# requests 根本不执行 js，这道指纹墙对它不存在 —— 直接照 H05 的算法签名调接口就行，
# 签名一模一样：base64('秒级时间戳,md5(秒级时间戳)')。
#
# 实测服务端只卡两样：
#   1. 签名要对、时间戳要新（和 H05 一样，差 30 秒就 400）
#   2. User-Agent 要像浏览器 —— 用 requests 默认 UA 直接 403，
#      返回"您已经被识别为爬虫程序…… 识别项目：User Agent 不是浏览器类型"
# 反过来，UA 里明写 HeadlessChrome 照样返回 200，
# 说明 headless 那一条纯粹是客户端自己拦自己，服务端不看。


# 输出目录固定在脚本旁边，不受启动时工作目录影响；不存在就自动建
outdir = Path(__file__).resolve().parent / 'data' / 'h06'
outdir.mkdir(parents=True, exist_ok=True)


base_url = 'https://spiderbuf.cn/challenge/selenium-fingerprint-anti-scraper'

api_url = base_url + '/api/'

# 这个 UA 不是摆设：换成 requests 默认的 python-requests/x.x 会被直接 403
myheaders = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.164 Safari/537.36'}


def buildPayload(timestamp=0):
    """按 js 的算法生成接口签名：base64('秒级时间戳,md5(秒级时间戳)')，和 H05 相同"""
    if timestamp == 0:
        timestamp = int(time.time())

    md5_hash = hashlib.md5()
    md5_hash.update(str(timestamp).encode('utf-8'))
    md5 = md5_hash.hexdigest()

    s = '%d,%s' % (timestamp, md5)
    return str(base64.b64encode(s.encode('utf-8')), 'utf-8')


def getData(file_name=''):
    """方案一：绕开指纹检测，直接调接口，返回字典列表"""
    resp = requests.get(api_url + buildPayload(), headers=myheaders, timeout=10)
    resp.raise_for_status()   # 签名过期 400，UA 不像浏览器 403，都在这里炸出来
    rows = resp.json()        # 接口返回的就是 JSON，不用 eval 转字典

    if file_name != '':
        with open(file_name, 'w', encoding='utf-8') as f:
            json.dump(rows, f, ensure_ascii=False, indent=2)

    return rows


def getHTMLByBrowser(url, file_name=''):
    """
    方案二：不绕，正面把三个指纹条件都满足，让页面自己去发 fetch。
    需要 pip install selenium 并且本机装了 Chrome。
    """
    from selenium import webdriver

    options = webdriver.ChromeOptions()

    # 条件一：navigator.webdriver 要是 false
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_experimental_option('excludeSwitches', ['enable-automation'])
    options.add_experimental_option('useAutomationExtension', False)

    # 条件二、三：navigator.plugins.length > 0 且 UA 里不能有 headless
    # —— 所以这里绝对不能加 headless，无头模式插件数为 0，UA 里也带 HeadlessChrome，
    #    两条同时不满足，页面的 if 直接不成立，表格永远是空的
    options.add_argument('disable-infobars')

    # 让 js 里那三行 console.log 能读出来，方便确认到底哪一条没过
    options.set_capability('goog:loggingPrefs', {'browser': 'ALL'})

    client = webdriver.Chrome(options=options)

    try:
        client.get(url)
        time.sleep(5)          # 等 fetch 回来把表格填上

        for entry in client.get_log('browser'):
            print(entry['message'])

        html = client.page_source
    finally:
        client.quit()          # 中途出错也要关掉，不然 Chrome 进程会一直留着

    if file_name != '':
        with open(file_name, 'w', encoding='utf-8') as f:
            f.write(html)

    return html


def parseHTML(html, file_name=''):
    """解析浏览器渲染后的表格，配合方案二使用"""
    root = etree.HTML(html)
    trs = root.xpath('//table[@id="dataContent"]//tr')

    lines = []
    for tr in trs:
        tds = tr.xpath('./td')
        if len(tds) == 0:      # 表头那行只有 th，跳过
            continue

        s = ''
        for td in tds:
            s = s + str(td.xpath('string(.)')).strip() + '|'

        print(s)
        lines.append(s)

    # 有内容时才开文件，避免 file_name 为空时 f 没定义就 close
    if file_name != '' and len(lines) > 0:
        with open(file_name, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines) + '\n')

    return lines


if __name__ == '__main__':

    # 方案一：指纹检测在客户端，requests 不执行 js，直接调接口
    rows = getData(str(outdir / 'h06.json'))

    with open(str(outdir / 'h06.txt'), 'w', encoding='utf-8') as f:
        for row in rows:
            s = '%s|%s|%s|%s|' % (
                row['ranking'], row['passwd'], row['time_to_crack_it'], row['used_count'])
            print(s)
            f.write(s + '\n')

    print('共 %d 条' % len(rows))

    # 方案二：正面满足三个指纹条件，让浏览器自己发请求（记住不能开 headless）
    # html = getHTMLByBrowser(base_url, str(outdir / 'h06.html'))
    # parseHTML(html, str(outdir / 'h06.txt'))


# 来源：https://spiderbuf.cn/code/selenium-fingerprint-anti-scraper
# 爬虫练习网站：Spiderbuf
