# coding=utf-8
# 带验证码的登录爬取
# 题目：https://spiderbuf.cn/challenge/web-scraping-with-captcha
#
# 流程：
#   1. GET  /challenge/web-scraping-with-captcha        取登录页，解析验证码图片地址 + captchaId
#   2. GET  /challenge/captcha/<id>.png                 下载验证码（必须同一个 session）
#   3. POST /challenge/web-scraping-with-captcha/login  提交账号/密码/验证码
#   4. GET  /challenge/web-scraping-with-captcha/list   用登录后的 cookie 取数据
#
# 关键点：全程用 requests.Session()，登录成功后服务端下发的 cookie（名字是 admin）
# 会自动存进 cookie jar 并在后续请求带上，不需要手工往 headers 里贴 Cookie。

import requests
from lxml import etree
from pathlib import Path

BASE = 'https://spiderbuf.cn'
LOGIN_PAGE = BASE + '/challenge/web-scraping-with-captcha'
LOGIN_API = BASE + '/challenge/web-scraping-with-captcha/login'
LIST_URL = BASE + '/challenge/web-scraping-with-captcha/list'

USERNAME = 'admin'
PASSWORD = '123456'
MAX_RETRY = 5  # 验证码识别错了就重来

# 输出目录固定在脚本旁边，不受启动时工作目录影响；不存在就自动建
outdir = Path(__file__).resolve().parent / 'data' / 'e02'
outdir.mkdir(parents=True, exist_ok=True)

session = requests.Session()
session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                  '(KHTML, like Gecko) Chrome/91.0.4472.164 Safari/537.36'
})

# 装了 ddddocr 就自动识别，没装就退回人工看图输入
try:
    import ddddocr
    ocr = ddddocr.DdddOcr(show_ad=False)
except ImportError:
    ocr = None
    print('[提示] 未安装 ddddocr，改用手动输入。自动识别请执行：pip install ddddocr')


def solve_captcha(img_bytes, img_path):
    """返回验证码字符串。有 ddddocr 走自动，否则让用户看图输入。"""
    if ocr is not None:
        code = ocr.classification(img_bytes)
        print('[OCR] 识别结果:', code)
        return code
    return input('打开 %s 看图，输入验证码: ' % img_path).strip()


def login():
    """走完一次登录流程，成功返回 True。"""
    # --- 1. 取登录页，解析验证码图片地址和 captchaId ---
    # captchaId 是服务端用来配对答案的凭据，和图片一一对应，必须从这次页面里取
    resp = session.get(LOGIN_PAGE, timeout=15)
    root = etree.HTML(resp.text)
    img_src = root.xpath('//img[@id="image"]/@src')[0]
    captcha_id = root.xpath('//input[@name="captchaId"]/@value')[0]

    # --- 2. 下载验证码 ---
    # 用同一个 session：换连接重新请求会拿到新的 captchaId，和上面解析到的就对不上了
    img_bytes = session.get(BASE + img_src, timeout=15).content
    img_path = outdir / 'captcha.png'
    img_path.write_bytes(img_bytes)

    code = solve_captcha(img_bytes, img_path)

    # --- 3. 提交登录 ---
    # 表单是 method="post"，四个字段一个都不能少
    resp = session.post(LOGIN_API, data={
        'username': USERNAME,
        'password': PASSWORD,
        'captchaSolution': code,
        'captchaId': captcha_id,
    }, timeout=15)

    # 登录成功会 302 到 /list；失败则被打回登录页
    ok = resp.url.endswith('/list')
    print('登录%s  最终地址: %s  cookie: %s'
          % ('成功' if ok else '失败', resp.url, session.cookies.get_dict()))
    return ok


for attempt in range(1, MAX_RETRY + 1):
    print('--- 第 %d 次尝试登录 ---' % attempt)
    if login():
        break
else:
    raise SystemExit('连续 %d 次登录失败，请检查验证码识别结果' % MAX_RETRY)


# --- 4. 取数据 ---
html = session.get(LIST_URL, timeout=15).text

f = open(outdir / 'e02.html', 'w', encoding='utf-8')
f.write(html)
f.close()

root = etree.HTML(html)
trs = root.xpath('//tr')
print('抓到 %d 行' % len(trs))

f = open(outdir / 'data_e02.txt', 'w', encoding='utf-8')
for tr in trs:
    tds = tr.xpath('./td')
    s = ''
    for td in tds:
        # string(.) 取整个单元格的所有后代文本，比 td.text 稳（后者遇到嵌套标签返回 None）
        s = s + str(td.xpath('string(.)')).strip() + '|'
    if s != '':
        print(s)
        f.write(s + '\n')
f.close()


# 来源：https://spiderbuf.cn/code/web-scraping-with-captcha
# 爬虫练习网站：Spiderbuf
