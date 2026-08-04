# coding=utf-8



import requests

from lxml import etree



url = 'https://spiderbuf.cn/challenge/scraper-http-header'


# 构造请求头，模拟浏览器访问
myheaders = {'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.164 Safari/537.36'}


# 请求 网页内容
html = requests.get(url, headers=myheaders).text

print(html)


# 写入本地文件 02.html
f = open('02.html', 'w', encoding='utf-8')

f.write(html)

f.close()



root = etree.HTML(html)

trs = root.xpath('//tr')



f = open('data02.txt', 'w', encoding='utf-8')

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






# 来源：https://spiderbuf.cn/code/scraper-http-header
# 爬虫练习网站：Spiderbuf