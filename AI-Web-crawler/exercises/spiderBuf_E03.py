# https://spiderbuf.cn/challenge/scraping-random-pagination

# coding=utf-8



import requests

from lxml import etree

import re

from pathlib import Path



base_url = 'https://spiderbuf.cn/challenge/scraping-random-pagination'

# https://spiderbuf.cn/e03/5f685274073b

# 输出目录固定在脚本旁边，不受启动时工作目录影响；不存在就自动建
outdir = Path(__file__).resolve().parent / 'data' / 'e03'
outdir.mkdir(parents=True, exist_ok=True)


myheaders = {

    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.164 Safari/537.36'}



# 取页数

html = requests.get(base_url, headers=myheaders).text

root = etree.HTML(html)

print(html)



lis = root.xpath('//ul[@class="pagination"]/li/a/@href')

print(lis)



i = 1

for item in lis:

    print(item)

    s = item.replace('/challenge/scraping-random-pagination','')

    print(base_url + s)

    url = base_url + s

    # print(url)

    html = requests.get(url, headers=myheaders).text

    # print(html)

    #

    f = open(outdir / f'e03_{i}.html', 'w', encoding='utf-8')

    f.write(html)

    f.close()

    #

    root = etree.HTML(html)

    trs = root.xpath('//tr')




    f = open(outdir / f'e03_{i}.txt', 'w', encoding='utf-8')

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


# 来源：https://spiderbuf.cn/code/scraping-random-pagination
# 爬虫练习网站：Spiderbuf