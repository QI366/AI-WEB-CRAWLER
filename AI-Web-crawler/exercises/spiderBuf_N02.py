# coding=utf-8



import requests

from lxml import etree

from pathlib import Path

import base64



# 输出目录固定在脚本旁边，不受启动时工作目录影响；不存在就自动建
outdir = Path(__file__).resolve().parent / 'data' / 'n02'
outdir.mkdir(parents=True, exist_ok=True)



url = 'https://spiderbuf.cn/challenge/scraping-images-base64'



myheaders = {

    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.164 Safari/537.36'}





html = requests.get(url, headers=myheaders).text

print(html)




f = open(outdir / 'n02.html', 'w', encoding='utf-8')

f.write(html)

f.close()



root = etree.HTML(html)

imgs = root.xpath('//img/@src')

print(imgs)

for item in imgs:

    print(item)

    # item 是获取到的base64字符串

    item = item.replace('data:image/png;base64,','')

    str_bytes = item.encode('raw_unicode_escape')  # str 转 bytes

    decoded = base64.b64decode(str_bytes)




    img = open(outdir / 'n02.png', 'wb')

    img.write(decoded)

    img.close()






# 来源：https://spiderbuf.cn/code/scraping-images-base64
# 爬虫练习网站：Spiderbuf