# coding=utf-8



import requests

from lxml import etree

from pathlib import Path


# 输出目录固定在脚本旁边，不受启动时工作目录影响；不存在就自动建
outdir = Path(__file__).resolve().parent / 'data' / 'n07'
outdir.mkdir(parents=True, exist_ok=True)


base_url = 'https://spiderbuf.cn/challenge/random-css-classname'


my_headers = {

    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.164 Safari/537.36'}



# 取到网页源码，写入文件 n07.html
html_bytes = requests.get(base_url, headers=my_headers).content

html = html_bytes.decode()

root = etree.HTML(html)

with open(outdir / 'n07.html', 'w', encoding='utf-8') as f:

    f.write(html)

# print(html)

divs = root.xpath('//main/div/div[@class]')

with open(outdir / 'n07.txt','w',encoding='utf-8') as f:

    for div in divs:

        print(div.text)

        if div.text:

            f.write(f'{div.text}\n')


# 来源：https://spiderbuf.cn/code/random-css-classname
# 爬虫练习网站：Spiderbuf