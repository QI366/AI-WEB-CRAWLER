# coding=utf-8
"""N06 的 RPA 解法：用 Playwright 驱动真实浏览器，而不是 requests 抓源码。

和 spiderBuf_N06.py 的区别：
  requests 拿到的是服务器返回的 HTML 文本，只能读到预填值；
  RPA 操作的是浏览器里活着的 DOM，读的是控件的 value 属性（property），
  所以自己填进去的内容也能读回来 —— 这是 requests 做不到的。

运行：python spiderBuf_N06_rpa.py
"""

from pathlib import Path

from lxml import etree
from playwright.sync_api import sync_playwright

outdir = Path(__file__).resolve().parent / 'data' / 'n06'
outdir.mkdir(parents=True, exist_ok=True)

base_url = 'https://spiderbuf.cn/challenge/scraping-form-rpa'

# 控件 name -> 中文标签。textarea 和 input 混在一起，下面用同一套代码处理
FIELDS = [
    ('username', '用户名'),
    ('password', '密码'),
    ('email', '邮箱'),
    ('website', '网站'),
    ('date', '生日'),
    ('time', '时间'),
    ('number', '数量'),
    ('range', '滑块'),
    ('color', '颜色'),
    ('search', '搜索'),
    ('textarea', '评论'),
]


def read_form(page):
    """读当前 DOM 里表单的值。"""
    for name, label in FIELDS:
        # 属性选择器同时命中 input 和 textarea；input_value() 读的是 DOM property，
        # 所以不用像 lxml 那样区分「value 属性」和「文本节点」两种取值方式
        print(f'{label}:{page.locator(f"[name={name}]").input_value()}')

    gender = page.locator('input[name="gender"]:checked')
    if gender.count():
        print(f'性别:{gender.first.input_value()}')

    for cb in page.locator('input[name="interest"]:checked').all():
        print(f'开发语言:{cb.input_value()}')

    print(f'人物代表:{page.locator("select[name=country]").input_value()}')

    active = page.locator('ul.items li a.active')
    if active.count():
        print(f'代表人物出处：{active.first.inner_text().strip()}')


def main():
    with sync_playwright() as p:
        # headless=False 可以看到浏览器实际操作的过程
        browser = p.chromium.launch(channel='msedge', headless=True)
        page = browser.new_page()
        page.goto(base_url, wait_until='domcontentloaded')

        print('=== 1. 服务器预填的值（requests 也读得到）===')
        read_form(page)

        print('\n=== 2. 模拟人工填写 ===')
        page.fill('input[name="username"]', 'zhuoz')
        page.fill('input[name="email"]', 'stitch@example.com')
        page.fill('textarea[name="textarea"]', '这是我自己输入的评论')
        page.check('input[name="gender"][value="female"]')
        page.select_option('select[name="country"]', index=0)
        print('已填写：用户名 / 邮箱 / 评论 / 性别 / 下拉框')

        print('\n=== 3. 重新读取：自己输入的值也拿得到 ===')
        read_form(page)

        print('\n=== 4. 对比：此刻的 HTML 源码里仍然是旧值 ===')
        html = page.content()
        (outdir / 'n06_rpa.html').write_text(html, encoding='utf-8')
        root = etree.HTML(html)
        print('  input[name=username] 的 value 属性 =',
              root.xpath('//input[@name="username"]/@value'))
        print('  textarea 的文本节点 =',
              repr((root.xpath('//textarea')[0].text or '')[:24] + '...'))
        print('  ↑ 这就是 requests 能看到的全部内容，所以它抓不到手动输入的值')

        browser.close()


if __name__ == '__main__':
    main()


# 来源：https://spiderbuf.cn/code/scraping-form-rpa
# 爬虫练习网站：Spiderbuf
