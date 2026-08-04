# coding=utf-8



import requests

import json

from pathlib import Path



url = 'https://spiderbuf.cn/challenge/iplist'
# https://spiderbuf.cn/challenge/scraping-ajax-api



myheaders = {'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.164 Safari/537.36'}



# 输出目录固定在脚本旁边，不受启动时工作目录影响；不存在就自动建
outdir = Path(__file__).resolve().parent / 'data' / '7'

outdir.mkdir(parents=True, exist_ok=True)



resp = requests.get(url, headers=myheaders)

# 接口返回 text/json 但响应头没带 charset，requests 会默认按 ISO-8859-1 解码导致中文乱码
resp.encoding = 'utf-8'

data_json = resp.text

print(data_json)



f = open(outdir / '07.html', 'w', encoding='utf-8')

f.write(data_json)

f.close()



ls = json.loads(data_json)

print(ls)



f = open(outdir / 'data07.txt', 'w', encoding='utf-8')

for item in ls:

    # print(item)

    s = '%s|%s|%s|%s|%s|%s|%s\n' % (item['ip'], item['mac'],item['manufacturer'], item['name'],item['ports'], item['status'], item['type'])

    f.write(s)

f.close()


# 来源：https://spiderbuf.cn/code/scraping-ajax-api
# 爬虫练习网站：Spiderbuf