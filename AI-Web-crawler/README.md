# AI Web Crawler 学习项目

一个用于学习"AI 网页爬虫"的示例项目：先用传统方式抓取并清洗网页内容，再用 Claude 对内容做结构化信息抽取（标题、摘要、要点、主题标签），最终把结果保存为本地 JSON 文件。

## 项目结构

```
AI-Web-crawler/
├── config.py                # 全局配置（从 .env 读取）
├── crawler/
│   ├── fetcher.py            # requests 抓取静态页面
│   ├── browser_fetcher.py    # Playwright 抓取 JS 渲染页面（可选）
│   └── parser.py             # BeautifulSoup 清洗 HTML -> 纯文本
├── ai/
│   └── extractor.py          # 调用 Claude API 做结构化信息抽取
├── storage/
│   └── writer.py             # 抽取结果落盘为 JSON
├── examples/
│   └── extract_article.py    # 端到端示例：URL -> 抓取 -> 清洗 -> AI 抽取 -> 保存
├── tests/
│   └── test_parser.py
├── data/                      # 抽取结果输出目录（json 文件已被 git 忽略）
├── requirements.txt
└── .env
```

## 快速开始

1. 创建虚拟环境并安装依赖：

   ```bash
   python -m venv .venv
   .venv\Scripts\activate    # Windows
   pip install -r requirements.txt
   playwright install chromium   # 仅在需要抓取 JS 渲染页面时执行
   ```

2. 配置 API Key：复制 `.env.example` 为 `.env`，填入你的 `ANTHROPIC_API_KEY`。

3. 运行示例：

   ```bash
   python examples/extract_article.py https://example.com/some-article
   ```

   运行成功后，结构化结果会保存到 `data/` 目录下的 JSON 文件中。

4. 运行测试：

   ```bash
   pytest
   ```

## 学习路线建议

- **第一步**：读 `crawler/fetcher.py` 和 `crawler/parser.py`，理解"抓取 -> 清洗"的基础爬虫流程。
- **第二步**：读 `ai/extractor.py`，理解如何用 `output_config.format`（JSON Schema）让 Claude 返回结构化数据，而不是自由文本。
- **第三步**：尝试给 `EXTRACTION_SCHEMA` 增加新字段（比如情感倾向、发布日期），观察 Claude 输出的变化。
- **进阶**：把 `crawler/fetcher.py` 换成 `crawler/browser_fetcher.py`，抓取需要 JS 渲染才能看到内容的页面；或者引入重试机制、并发抓取、去重存储等能力。

## 配置项（.env）

| 变量 | 说明 | 默认值 |
| --- | --- | --- |
| `ANTHROPIC_API_KEY` | Claude API Key | 无（必填） |
| `ANTHROPIC_MODEL` | 使用的 Claude 模型 | `claude-opus-5` |
| `REQUEST_TIMEOUT` | 请求超时时间（秒） | `15` |
| `OUTPUT_DIR` | 抽取结果输出目录 | `data` |
