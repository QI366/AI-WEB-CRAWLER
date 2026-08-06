# coding=utf-8



import requests

from lxml import etree

import time

import base64

import json

import re

import numpy as np

from pathlib import Path

# 输出目录固定在脚本旁边，不受启动时工作目录影响；不存在就自动建
outdir = Path(__file__).resolve().parent / 'data' / 'c02'
outdir.mkdir(parents=True, exist_ok=True)

base_url = 'https://spiderbuf.cn/challenge/scraper-practice-c02'

# 关键 获取 const encryptedData
# base解码
#
# 页面里的表格是 JS 渲染的，静态 HTML 中 tbody 是空的；
# 但 JS 用的原始数据就明文写在同一段 <script> 里：
#     const encryptedData = "ewogICAgICAiZmxpZ2h0cyI6IFsK...";
# 名字叫 encrypted，实际只是 base64 编码（编码 != 加密），直接解开就是 JSON。
# 滑块只是障眼法：不拖它，数据一样在源码里。


myheaders = {

    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36 Edg/151.0.0.0'}


# 匹配 const/var/let encryptedData = "....."，容忍等号两边的空格
ENCRYPTED_RE = re.compile(r'(?:const|var|let)\s+encryptedData\s*=\s*"([^"]+)"')


def getHTML(url, file_name=''):
    '''直接用 requests 取源码，不启动浏览器'''

    resp = requests.get(url, headers=myheaders, timeout=15)

    resp.raise_for_status()

    html = resp.text

    if file_name != '':

        with open(file_name, 'w', encoding='utf-8') as f:

            f.write(html)

    return html


def extractFlights(html):
    '''从源码里抠出 encryptedData，base64 解码后按 JSON 解析'''

    m = ENCRYPTED_RE.search(html)

    if m is None:

        raise ValueError('页面里没找到 encryptedData，站点结构可能变了')

    b64 = m.group(1)

    # b64decode 得到的是 bytes，页面里有中文城市名，按 utf-8 解码
    raw = base64.b64decode(b64).decode('utf-8')

    # 用 json.loads 而不是 eval：eval 会把字符串当代码执行（拿到什么就跑什么，
    # 站点一改内容就可能被注入），而且遇到 JSON 的 true/false/null 会直接报错
    data = json.loads(raw)

    return data['flights']


def parseHTML(html):
    '''从渲染后的 DOM 取价格。注意：只对 selenium 拿到的源码有效，
    requests 取到的静态 HTML 里表格是空的'''

    root = etree.HTML(html)

    trs = root.xpath('//tr')

    prices = []

    for tr in trs:

        tds = tr.xpath('./td')

        if len(tds) > 2:

            prices.append(int(tds[2].text))

    return prices


def report(prices):

    print('航班数量：', len(prices))

    print('票价列表：', prices)

    print('票价总和：', sum(prices))

    print('票价平均值：', round(np.mean(prices), 2))


def getHTMLBySelenium(url, file_name=''):
    '''备用方案：真的去拖滑块，等 JS 把表格渲染出来再取 page_source。
    本关用不上，留作滑块操作的练习'''

    # 延迟导入：主流程不需要 selenium，没装也不影响脚本运行
    from selenium import webdriver

    from selenium.webdriver import ActionChains

    from selenium.webdriver.common.by import By

    client = webdriver.Chrome()

    client.get(url)

    time.sleep(10)

    # 事件参数对象
    actionChains = ActionChains(client)

    # 捕捉滑块元素
    slide_btn = client.find_element(By.ID, 'slider')

    # 观察网站滑块移动的长度和位置
    actionChains.click_and_hold(slide_btn)

    actionChains.move_by_offset(220, 0)

    # 这里要注意：
    # 以下三个是以上面的坐标(220,0)为起点来计算的
    # 所以最终移动的距离是220加上以下的累计
    actionChains.move_by_offset(11, 0)

    actionChains.move_by_offset(13, 0)

    actionChains.move_by_offset(10, 0)

    actionChains.release()

    actionChains.perform()

    html = client.page_source

    client.quit()

    if file_name != '':

        with open(file_name, 'w', encoding='utf-8') as f:

            f.write(html)

    return html


if __name__ == '__main__':

    html = getHTML(base_url, outdir / 'c02.html')

    flights = extractFlights(html)

    for obj in flights:

        print(obj['from'], '->', obj['to'], obj['price'])

    report([obj['price'] for obj in flights])

    # 备用：走浏览器拖滑块，再从渲染后的表格里取第 3 列
    # html = getHTMLBySelenium(base_url, outdir / 'c02_rendered.html')
    # report(parseHTML(html))


# 来源：https://spiderbuf.cn/code/scraper-practice-c02
# 爬虫练习网站：Spiderbuf
