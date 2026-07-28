import requests
from bs4 import BeautifulSoup

# 1. 发送请求
url = "https://example.com"
response = requests.get(url)

# 2. 解析HTML
soup = BeautifulSoup(response.text, 'html.parser')

# 3. 提取数据
title = soup.title.string
print(f"页面标题: {title}")
