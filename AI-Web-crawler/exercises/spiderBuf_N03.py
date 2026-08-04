# coding=utf-8



import requests

from lxml import etree

from pathlib import Path

import time


# 输出目录固定在脚本旁边，不受启动时工作目录影响；不存在就自动建
outdir = Path(__file__).resolve().parent / 'data' / 'n03'
outdir.mkdir(parents=True, exist_ok=True)

base_url = 'https://spiderbuf.cn/challenge/scraper-bypass-request-limit/%d'



myheaders = {

    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.164 Safari/537.36'}



max_no = 20

# exit()



for i in range(1, max_no + 1):

    print(i)

    url = base_url % i

    print(url)

    html = requests.get(url, headers=myheaders).text

    print(html)




    f = open(outdir / f'n03_{i}.html', 'w', encoding='utf-8')

    f.write(html)

    f.close()



    root = etree.HTML(html)

    trs = root.xpath('//tr')




    f = open(outdir / f'datan03_{i}.txt', 'w', encoding='utf-8')

    for tr in trs:

        tds = tr.xpath('./td')

        s = ''

        for td in tds:

            s = s + str(td.xpath('string(.)')) + '|'

            # s = s + str(td.text) + '|'

        print(s)

        if s != '':

            f.write(s + '\n')

    time.sleep(2)

    f.close()




# 来源：https://spiderbuf.cn/code/scraper-bypass-request-limit
# 爬虫练习网站：Spiderbuf