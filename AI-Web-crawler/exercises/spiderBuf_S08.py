# coding=utf-8



import requests

from lxml import etree

from pathlib import Path



url = 'https://spiderbuf.cn/challenge/scraper-via-http-post'



myheaders = {'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.164 Safari/537.36'}


# 输出目录固定在脚本旁边，不受启动时工作目录影响；不存在就自动建
outdir = Path(__file__).resolve().parent / 'data' / '8'

outdir.mkdir(parents=True, exist_ok=True)


payload = {'level':'8'}

html = requests.post(url, headers=myheaders, data=payload).text

print(html)



f = open(outdir / '08.html', 'w', encoding='utf-8')

f.write(html)

f.close()



root = etree.HTML(html)

trs = root.xpath('//tr')




f = open(outdir / 'data08.txt', 'w', encoding='utf-8')

for tr in trs:

    tds = tr.xpath('./td')

    s = ''

    for td in tds:

        # print(td.text)

        s = s + str(td.text) + '|'

    print(s)

    if s != '':

        f.write(s + '\n')



f.close()






# 来源：https://spiderbuf.cn/code/scraper-via-http-post
# 爬虫练习网站：Spiderbuf