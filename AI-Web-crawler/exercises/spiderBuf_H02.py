# coding=utf-8
# 界面元素参考：
#     <div class="row" style="margin-top: 10px;">

#         <div class="col-xs-12 col-lg-12">

#             <h2>致命魔术 The Prestige</h2></br>

#             <div class="col-xs-3 col-lg-3">

#                 <img src="/static/images/douban_movie/posters/tt0482571.jpg" alt="致命魔术 The Prestige"

#                     class="img-responsive img-thumbnail">

#             </div>

#             <div class="col-xs-9 col-lg-9">

#                 <span >豆瓣电影评分:</span> 8.9<br/>

#                 <span ><span>导演</span>: <span>克里斯托弗·诺兰</span></span><br/>

#                 <span ><span>编剧</span>: <span>乔纳森·诺兰 </span></span>/乔纳森·诺兰 / 克里斯托弗·诺兰 / 克里斯托弗·普瑞丝特<br/>

#                 <span ><span>主演</span>: <span>休·杰克曼 </span></span>/休·杰克曼 / 克里斯蒂安·贝尔 / 迈克尔·凯恩 / 丽贝卡·豪尔 / 斯嘉丽·约翰逊 / 大卫·鲍伊 / 安迪·瑟金斯 / 派珀·佩拉博 / 萨曼塔·马霍林 / 丹尼尔·戴维斯 / 吉姆·皮多克 / 克里斯托弗·尼姆 / 马克·瑞安 / 罗杰·里斯 / 杰米·哈里斯 / 罗恩·帕金斯 / 瑞奇·杰 / 安东尼·德·马克 / 冀朝理<br/>

#                 <span ><span>类型:</span><span> 剧情 </span></span>/剧情 / 悬疑 / 惊悚<br/>

#                 <span ><span>制片国家/地区:</span><span> 英国 </span></span>/英国 / 美国<br/>

#                 <span ><span>语言:</span><span> 英语</span></span><br/>

#                 <span ><span>上映日期:</span><span> 2006-10-17(罗马电影节) </span></span>/2006-10-17(罗马电影节) / 2006-10-20(美国)<br/>

#                 <span ><span>片长:</span><span> 130分钟</span></span><br/>

#                 <span ><span>又名:</span><span> 死亡魔法(港) </span></span>/死亡魔法(港) / 顶尖对决(台) / 魔高一丈 / 魔道争锋<br/>

#                 <span >IMDb:</span> tt0482571<br/>

#             </div>

#         </div>

#     </div>

#     <div class="row" style="margin-top: 10px;">

#         <div class="col-xs-12 col-lg-12">简介：</br>19世纪末，人们对科学文明还不是认识得太过清楚，于是，安吉尔（休•杰克曼Hugh Jackman饰）和伯登（克里斯蒂安•贝尔Christian Bale饰）的魔术，成为了伦敦城内的神奇人物。安吉尔出身贵族，魔术手段华丽丰富，是富人圈子里的表演常客。而伯登即使出身平平，争强好胜的心智和充满创造力的魔术技巧，却也令他有了名气。两人自小本是要好的伙伴，然而，现在魔术界二人各有领地，并且都有野心想成为音乐大厅里的顶级魔术师，一番明争暗斗如箭在弦上。</div>

#     </div>
import os.path



import requests

from lxml import etree

import time

from pathlib import Path


# 输出目录固定在脚本旁边，不受启动时工作目录影响；不存在就自动建
outdir = Path(__file__).resolve().parent / 'data' / 'h02'
outdir.mkdir(parents=True, exist_ok=True)




base_url = 'https://spiderbuf.cn/challenge/scraping-douban-movies-xpath-advanced'



myheaders = {

    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.164 Safari/537.36'}



def getHTML(url,file_name=''):

    html = requests.get(url, headers=myheaders).text

    if file_name != '':

        with open(file_name, 'w', encoding='utf-8') as f:

            f.write(html)

    return html





def downloadImage(url, path=''):

    img_data = requests.get(url, headers=myheaders).content

    # get image file name

    file_name = url.split('/').pop()



    with open(os.path.join(path, file_name), 'wb') as img:

        img.write(img_data)





def parseHTML(html):
    """
    解析豆瓣电影 HTML，提取每部电影的详细信息（标题、海报、评分、导演等）和简介，
    并下载海报图片到固定目录。
    """
    root = etree.HTML(html)
    # 定位所有电影信息行（class="row" 且 style 包含 "margin-top: 10px"）
    rows = root.xpath('//div[@class="row" and contains(@style, "margin-top: 10px;")]')
    movies = []          # 存储所有电影数据（便于扩展）
    i = 0
    while i < len(rows):
        row = rows[i]
        # 检查当前行是否为电影信息行（包含 h2 标题）
        h2s = row.xpath('.//h2')
        if h2s:
            # ---- 提取电影信息 ----
            movie = {}
            # 标题
            title = h2s[0].text.strip() if h2s[0].text else ''
            movie['title'] = title
            print(title)

            # 海报 URL 并下载
            img_url = row.xpath('.//img/@src')
            if img_url:
                img_url = 'https://spiderbuf.cn/' + img_url[0]
                movie['poster_url'] = img_url
                print(img_url)
                downloadImage(img_url, str(outdir))
            else:
                movie['poster_url'] = ''

            # 详情区域（col-xs-9 col-lg-9）
            detail_divs = row.xpath('.//div[@class="col-xs-9 col-lg-9"]')
            if not detail_divs:
                i += 1
                continue
            detail = detail_divs[0]

            # 字段配置：每个字段的标签文本和是否嵌套（标签在子 span 中）
            fields_config = {
                'rating':       {'label': '豆瓣电影评分:', 'nested': False},
                'director':     {'label': '导演',        'nested': True},
                'scriptwriter': {'label': '编剧',        'nested': True},
                'performer':    {'label': '主演',        'nested': True},
                'genre':        {'label': '类型:',       'nested': True},
                'area':         {'label': '制片国家/地区:', 'nested': True},
                'lang':         {'label': '语言:',       'nested': True},
                'release_date': {'label': '上映日期:',   'nested': True},
                'runtime':      {'label': '片长:',       'nested': True},
                'alias':        {'label': '又名:',       'nested': True},
                'imdb':         {'label': 'IMDb:',       'nested': False},
            }

            for key, config in fields_config.items():
                label = config['label']
                if config['nested']:
                    # 嵌套结构：<span><span>标签</span> 值 </span>
                    elems = detail.xpath(f'.//span[span/text()="{label}"]/..')
                    if elems:
                        parent = elems[0]
                        full_text = parent.xpath('string()').strip()
                        # 去除标签前缀（可能带有冒号）
                        if full_text.startswith(label):
                            value = full_text[len(label):].strip()
                        else:
                            # 尝试补冒号
                            alt = label + ':'
                            if full_text.startswith(alt):
                                value = full_text[len(alt):].strip()
                            else:
                                value = full_text.replace(label, '').strip()
                        movie[key] = value
                    else:
                        movie[key] = ''
                else:
                    # 非嵌套结构：<span>标签</span> 值 <br/>
                    elems = detail.xpath(f'.//span[text()="{label}"]')
                    if elems:
                        span = elems[0]
                        texts = span.xpath('following-sibling::text()')
                        value = ''.join(texts).strip() if texts else ''
                        movie[key] = value
                    else:
                        movie[key] = ''

                # 按原顺序打印字段值
                print(movie.get(key, ''))

            # ---- 提取简介（下一行） ----
            if i + 1 < len(rows):
                next_row = rows[i + 1]
                # 简介行通常只包含一个 div.col-xs-12.col-lg-12，里面是文本
                summary_divs = next_row.xpath('.//div[@class="col-xs-12 col-lg-12"]')
                if summary_divs:
                    summary_text = summary_divs[0].xpath('string()').strip()
                    # 去除可能的 "简介：" 前缀
                    for prefix in ('简介：', '简介:'):
                        if summary_text.startswith(prefix):
                            summary_text = summary_text[len(prefix):].strip()
                            break
                    movie['summary'] = summary_text
                    print(summary_text)
                # 跳过已处理的简介行
                i += 1

            movies.append(movie)
        i += 1

    # 如需返回数据可取消下面注释
    # return movies




if __name__ == '__main__':

    html = getHTML(base_url, str(outdir / 'h02.html'))

    # with open('./data/h02/h02.html', 'r', encoding='utf-8') as f:

    #     html = f.read()

    parseHTML(html)




# 来源：https://spiderbuf.cn/code/scraping-douban-movies-xpath-advanced
# 爬虫练习网站：Spiderbuf