# coding=utf-8



import requests

from lxml import etree



url = 'https://spiderbuf.cn/challenge/requests-lxml-for-scraping-beginner'


# 请求 网页内容
html = requests.get(url).text


# 将网页内容写入本地文件 01.html
f = open('01.html', 'w', encoding='utf-8')

f.write(html)

f.close()


# 解析网页内容，获取所有 tr 元素
root = etree.HTML(html)

trs = root.xpath('//tr')


# 将每个 tr 元素的内容写入本地文件 data01.txt
f = open('data01.txt', 'w', encoding='utf-8')

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



# print(html)
