# coding=utf-8

import os.path



import requests

from lxml import etree

from pathlib import Path

import time



base_url = 'https://spiderbuf.cn/challenge/css-sprites'

# 输出目录固定在脚本旁边，不受启动时工作目录影响；不存在就自动建
outdir = Path(__file__).resolve().parent / 'data' / 'n05'
outdir.mkdir(parents=True, exist_ok=True)

myheaders = {

    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.164 Safari/537.36'}



def getHTML(url,file_name=''):

    html_bytes = requests.get(url, headers=myheaders).content

    html = html_bytes.decode()

    if file_name != '':

        with open(file_name, 'w', encoding='utf-8') as f:

            f.write(html)

    return html







def parseHTML(html):

    class_map = {'sprite abcdef':'0',

                'sprite ghijkl':'1',

                'sprite mnopqr':'2',

                'sprite uvwxyz':'3',

                'sprite yzabcd':'4',

                'sprite efghij':'5',

                'sprite klmnop':'6',

                'sprite qrstuv':'7',

                'sprite wxyzab':'8',

                'sprite cdefgh':'9'}

    # parse html source code here

    root = etree.HTML(html)

    divs = root.xpath('//div[@style="margin-bottom: 30px;"]')



    for div in divs:

        titles = div.xpath('./h2')

        title = ''

        if len(titles) > 0:

            title = titles[0].text

            print(title)



        amount_spans = div.xpath('./p/span[@class]')

        amount_str = ''

        for span in amount_spans:

            attr_class = span.attrib["class"] if "class" in span.attrib else ""

            # print(f"{span} - {attr_class}")

            # print(span.text)

            amount_str += class_map[attr_class]

        print(amount_str)







if __name__ == '__main__':

    html = getHTML(base_url, str(outdir / 'n05.html'))

    parseHTML(html)




# 来源：https://spiderbuf.cn/code/css-sprites
# 爬虫练习网站：Spiderbuf