"""Fetch JS-rendered pages via Playwright. Requires `playwright install chromium` once."""

from playwright.sync_api import sync_playwright

from config import settings


def fetch_html_js(url: str, wait_ms: int = 2000) -> str:
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(user_agent=settings.user_agent)
        page.goto(url, timeout=settings.request_timeout * 1000)
        page.wait_for_timeout(wait_ms)
        html = page.content()
        browser.close()
    return html
