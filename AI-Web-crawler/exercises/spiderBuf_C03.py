# coding=utf-8



import requests

from lxml import etree

import time

import json

import hashlib

import random

import numpy as np

from pathlib import Path



# 分页获取关键难点：
# <div class="flex justify-center items-center my-4">
#             <nav aria-label="Page navigation">
#                 <ul class="pagination">
#                     <li><span>共3页</span></li>
#                     <li><a href="#" onclick="getIrisData(1);">1</a></li>
#                     <li><a href="#" onclick="getIrisData(2);">2</a></li>
#                     <li><a href="#" onclick="getIrisData(3);">3</a></li>
#                     <li><a href="#" onclick="getIrisData(4);">4</a></li>
#                     <li><a href="#" onclick="getIrisData(5);">5</a></li>
#                 </ul>
#             </nav>
#         </div>
# getIrisData函数
# 函数参数与内部变量
# _0x3d0eeb：传入的一个参数，可能是某种令牌（token）或用户标识，用于后续的异或运算。

# 2.1 生成随机数 _0x1fa068
# javascript
# const _0x1fa068 = Math.floor(Math.random() * (0xba7af ^ 0xbb8ef) + (0xbe628 ^ 0xbe1f8));
# 计算两个异或值：

# 0xba7af ^ 0xbb8ef = 0x1f40（十进制 8000）

# 0xbe628 ^ 0xbe1f8 = 0x7d0（十进制 2000）

# 所以实际为：

# javascript
# const random = Math.floor(Math.random() * 8000 + 2000);
# 即生成一个 2000 到 9999 之间的随机整数。

# 2.2 生成时间戳 _0x542b78
# javascript
# const _0x542b78 = Math.floor(Date.now() / (0x54458 ^ 0x547b0));
# 计算异或值：

# 0x54458 ^ 0x547b0 = 0x3e8（十进制 1000）

# 所以实际为：

# javascript
# const timestamp = Math.floor(Date.now() / 1000);
# 即 当前时间的 Unix 时间戳（秒）。

# 2.3 计算异或结果 _0x39669e
# javascript
# const _0x39669e = _0x3d0eeb ^ _0x542b78;
# 将传入参数与时间戳按位异或，得到一个整数。

# 2.4 计算 MD5 哈希
# javascript
# const _0x56e6b4 = md5('' + _0x39669e + _0x542b78).toString();
# 将异或结果和时间戳拼接成字符串（如 "1234567890"），然后计算其 MD5 值，并转为十六进制字符串。

# 3. 构造请求体
# javascript
# const _0x811850 = {
#     "xorResult": _0x39669e,
#     'random': _0x1fa068,
#     "timestamp": _0x542b78,
#     "hash": _0x56e6b4
# };
# 包含四个字段：

# xorResult：传入参数与时间戳的异或结果

# random：生成的随机数（2000~9999）

# timestamp：当前 Unix 时间戳（秒）

# hash：上述拼接字符串的 MD5

# 4. 发送 POST 请求
# javascript
# fetch("scraper-practice-c03", {
#     "method": 'POST',
#     'body': JSON.stringify(_0x811850)
# })
# 向相对路径 /scraper-practice-c03 发送 POST 请求，请求体为上面对象的 JSON 字符串。

# 5. 处理响应并渲染表格
# 解析响应 JSON（假设返回一个数组，每个元素包含鸢尾花数据：sepal_length, sepal_width, petal_length, petal_width, class）。

# 找到页面中 #flightTable tbody 元素。

# 清空原有内容。

# 遍历返回的数组，为每条数据创建一行 <tr>，包含：

# 行号（从 1 开始）

# 五个特征值

# 追加到 tbody 中。


# 实测补充：
# - 签名是真校验的：hash 乱填或缺字段 -> 400 Invalid payload
# - random 字段必须存在，但服务端不校验它的值（纯干扰项）
# - timestamp 不校验时效，一小时前的时间戳照样通过
# - 页面写着「共3页」是过时文案，实际 5 页 × 30 行 = 150 行（完整鸢尾花数据集）
#   所以不写死页数，翻到返回空数组为止

base_url = 'https://spiderbuf.cn/challenge/scraper-practice-c03'

# 输出目录固定在脚本旁边，不受启动时工作目录影响；不存在就自动建
outdir = Path(__file__).resolve().parent / 'data' / 'c03'
outdir.mkdir(parents=True, exist_ok=True)



myheaders = {

    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36 Edg/151.0.0.0'}



def buildPayload(page):
    '''复现 JS 里 getIrisData(page) 的签名逻辑，四个字段缺一不可'''

    # Math.floor(Math.random() * 8000 + 2000) —— 2000 ~ 9999，服务端不校验值
    random_value = random.randint(2000, 9999)

    # Math.floor(Date.now() / 1000) —— 秒级时间戳
    timestamp = int(time.time())

    xor_result = page ^ timestamp

    # md5('' + xorResult + timestamp)：两个数字直接拼成字符串再取 MD5
    hash_value = hashlib.md5(f'{xor_result}{timestamp}'.encode('utf-8')).hexdigest()

    return {

        'xorResult': xor_result,

        'random': random_value,

        'timestamp': timestamp,

        'hash': hash_value}


def fetchPage(session, page):
    '''取第 page 页，返回该页的记录列表'''

    resp = session.post(base_url, json=buildPayload(page), timeout=15)

    # 签名不对时服务端返回 400 Invalid payload，这里让它直接抛出来
    resp.raise_for_status()

    return resp.json()


def fetchAll(file_name=''):
    '''从第 1 页开始翻，直到某页返回空数组为止'''

    session = requests.Session()

    session.headers.update(myheaders)

    rows = []

    page = 1

    while True:

        page_rows = fetchPage(session, page)

        print(f'第 {page} 页：{len(page_rows)} 条')

        if not page_rows:

            break

        rows += page_rows

        page += 1

    if file_name != '':

        with open(file_name, 'w', encoding='utf-8') as f:

            json.dump(rows, f, ensure_ascii=False, indent=2)

    return rows


def report(sepal_width_arr):

    print('记录条数：', len(sepal_width_arr))

    print('sepal_width 总和：', round(np.sum(sepal_width_arr), 4))

    print('sepal_width 平均值：', round(np.mean(sepal_width_arr), 4))


def parseHTML(html):
    '''从渲染后的 DOM 取 sepal_width（表头第 3 列 Sepal Width，即 td 下标 2）'''

    root = etree.HTML(html)

    trs = root.xpath('//tr')

    sepal_width_arr = []

    for tr in trs:

        tds = tr.xpath('./td')

        if len(tds) > 2:

            sepal_width_arr.append(float(tds[2].text))

    return sepal_width_arr


def getHTMLBySelenium(url, file_name=''):
    '''备用方案：开浏览器逐页点分页链接，等 JS 渲染完再取 page_source。
    本关用不上，留作分页点击的练习'''

    # 延迟导入：主流程不需要 selenium，没装也不影响脚本运行
    from selenium import webdriver

    from selenium.webdriver.common.by import By

    sepal_width_arr = []

    client = webdriver.Chrome()

    client.get(url)

    time.sleep(5)

    html = client.page_source

    sepal_width_arr += parseHTML(html)

    if file_name != '':

        with open(file_name + '_1.html', 'w', encoding='utf-8') as f:

            f.write(html)

    # 分页里第一个 li 是「共N页」的 span、没有 a，所以 a[0] 就是第 1 页；
    # a[1] ~ a[4] 对应第 2 ~ 5 页。限定 class 免得抓到导航栏里的其它 ul
    links = client.find_elements(By.XPATH, '//ul[@class="pagination"]/li/a')

    for i in range(1, len(links)):

        client.find_elements(By.XPATH, '//ul[@class="pagination"]/li/a')[i].click()

        time.sleep(5)

        html = client.page_source

        sepal_width_arr += parseHTML(html)

        if file_name != '':

            with open(file_name + f'_{i+1}.html', 'w', encoding='utf-8') as f:

                f.write(html)

    client.quit()

    return sepal_width_arr

    

    





if __name__ == '__main__':

    # 直接打签名请求接口，不开浏览器
    rows = fetchAll(outdir / 'c03.json')

    report([item['sepal_width'] for item in rows])

    # 备用：走浏览器逐页点击，再从渲染后的表格里取第 3 列
    # report(getHTMLBySelenium(base_url, str(outdir / 'c03')))






# 来源：https://spiderbuf.cn/code/scraper-practice-c03
# 爬虫练习网站：Spiderbuf