# coding=utf-8



import requests

from lxml import etree

import re
from pathlib import Path
from urllib.parse import urljoin



# 输出目录固定在脚本旁边，不受启动时工作目录影响；不存在就自动建
outdir = Path(__file__).resolve().parent / 'data' / 'e04'
outdir.mkdir(parents=True, exist_ok=True)


base_url = 'https://spiderbuf.cn/challenge/block-ip-proxy'



myheaders = {

    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.164 Safari/537.36'}



# 代理默认不启用；本题不用代理也能抓完，只有 IP 被封时才需要。
# 要启用就填一个真正支持 CONNECT 的代理，http/https 两个键都要写，且带上 scheme：
# proxies = {'http': 'http://127.0.0.1:8080', 'https': 'http://127.0.0.1:8080'}
proxies = None

# 取页数

html = requests.get(base_url, headers=myheaders, proxies=proxies).text

root = etree.HTML(html)

# print(html)

lis = root.xpath('//ul[@class="pagination"]/li/a')

pages = []

for item in lis:

    print(item.attrib['href'])

    if item.attrib['class'] != 'item trap':

        pages.append(item.attrib['href'])

print(pages)

i = 1

for item in pages:

    print(item)

    # href 是站点根目录下的绝对路径，用 urljoin 拼域名，避免手工拼接把路径重复一遍
    url = urljoin(base_url, item)

    print(url)

    # print(url)

    html = requests.get(url, headers=myheaders, proxies=proxies).text

    # print(html)

    #

    f = open(outdir / f'e04_{i}.html', 'w', encoding='utf-8')

    f.write(html)

    f.close()

    #

    root = etree.HTML(html)

    trs = root.xpath('//tr')




    f = open(outdir / f'e04_{i}.txt', 'w', encoding='utf-8')

    for tr in trs:

        tds = tr.xpath('./td')

        s = ''

        for td in tds:

            s = s + str(td.xpath('string(.)')) + '|'

            # s = s + str(td.text) + '|'

        print(s)

        if s != '':

            f.write(s + '\n')



    f.close()

    i += 1




# 来源：https://spiderbuf.cn/code/block-ip-proxy
# 爬虫练习网站：Spiderbuf