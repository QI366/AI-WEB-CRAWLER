# coding=utf-8



import requests

from lxml import etree

import numpy as np

from pathlib import Path

# 输出目录固定在脚本旁边，不受启动时工作目录影响；不存在就自动建
outdir = Path(__file__).resolve().parent / 'data' / 'c01'
outdir.mkdir(parents=True, exist_ok=True)

base_url = 'https://spiderbuf.cn/challenge/scraper-practice-c01'

data_url = base_url + '/mnist'


# :authority
# spiderbuf.cn
# :method
# GET
# :path
# /challenge/scraper-practice-c01/mnist
# :scheme
# https
# Accept
# text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7
# Accept-Encoding
# gzip, deflate, br, zstd
# Accept-Language
# zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6
# Cookie
# _ga=GA1.1.1040765495.1785824231; __cgf3t=G0gzgFKDRlLtmZH7NrzqOb1x4pek1xNQk12KKc4g21Y-1731624199; __gads=ID=bc51c6e49bcb3b31:T=1785824266:RT=1785985638:S=ALNI_MaNIrWd8AKpO1u6S80oqgFcEXMgBA; __gpi=UID=0000145ff850bee4:T=1785824266:RT=1785985638:S=ALNI_Maha4iEeqEDo_106SGC12seisLQXw; __eoi=ID=c1ce658dc93faf45:T=1785824266:RT=1785985638:S=AA-AfjaimUcnE_e50YJJsAWD_3Ez; FCCDCF=%5Bnull%2Cnull%2Cnull%2Cnull%2Cnull%2Cnull%2C%5B%5B32%2C%22%5B%5C%2286933c32-3db8-43f7-9b3c-363e4c41cc64%5C%22%2C%5B1785824232%2C566000000%5D%5D%22%5D%5D%5D; FCNEC=%5B%5B%22AKsRol9rTduwpuMaJede8Wk-hNdWtytWRMvlSFeEJJwg2SJgNS6VnVQUabJ3faMYDzYGjUM5tovZf1oWKF2DkAaxSavx2zufEreOxhttV1F6C_9XJKDafp5qISkUAlSUEdCYs8RNH_Txg8QygI28HkZGo3SUYyXouw%3D%3D%22%5D%5D; _ga_7B42BKG1QE=GS2.1.s1785979937$o7$g1$t1785985761$j39$l0$h0
# Priority
# u=0, i
# Referer
# https://spiderbuf.cn/challenge/scraper-practice-c01
# Sec-Ch-Ua
# "Not=A?Brand";v="99", "Microsoft Edge";v="151", "Chromium";v="151"
# Sec-Ch-Ua-Mobile
# ?0
# Sec-Ch-Ua-Platform
# "Windows"
# Sec-Fetch-Dest
# document
# Sec-Fetch-Mode
# navigate
# Sec-Fetch-Site
# same-origin
# Sec-Fetch-User
# ?1
# Upgrade-Insecure-Requests
# 1
# User-Agent
# Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36 Edg/151.0.0.0
# 只保留服务端真正会看的两项：
# - User-Agent：不带任何请求头时服务端直接返回 403
# - Accept-Language：可选，让请求更像浏览器
# 不要手抄 Accept-Encoding（br/zstd requests 解不了，会拿到二进制乱码），
# 也不要抄 :authority / :method / :path / :scheme（HTTP/2 伪首部，requests 走 HTTP/1.1）
my_headers = {

    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36 Edg/151.0.0.0',

    'Accept-Language': 'zh-CN,zh;q=0.9'}





# mnist 页面校验 __cgf3t 这个 cookie，缺了会 307 跳到 //challenge/...（协议相对 URL），
# requests 会把 challenge 当成主机名去解析并报 ConnectionError。
# 这个 cookie 由父页面下发，所以先用 Session 访问父页面把它收下，不要手写死 Cookie 头。
session = requests.Session()

session.headers.update(my_headers)

session.get(base_url, timeout=15)

resp = session.get(data_url, headers={'Referer': base_url}, timeout=15)

resp.raise_for_status()

html = resp.text

root = etree.HTML(html)

with open(outdir / 'c01.html', 'w', encoding='utf-8') as f:

    f.write(html)

# print(html)



trs = root.xpath('//tbody/tr')





pix1_arry = []

for tr in trs:

    tds = tr.xpath('td')

    # 把 pix1 列的值添加到数组

    pix1_arry.append(int(tds[1].text) if len(tds) > 1 else 0)

    print('pix1 列值：', tds[1].text if len(tds) > 1 else 0)


# 打印 pix1 列总和
print('pix1 列总和：', sum(pix1_arry))

# 计算 pix1 列的平均值并四舍五入至两位小数
print('pix1 列平均值：', round(np.mean(pix1_arry),2))