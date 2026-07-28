"""End-to-end example: fetch a URL, clean it, extract structured data with Claude, save it.

Usage:
    python examples/extract_article.py https://example.com/some-article
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ai.extractor import extract_structured_data  # noqa: E402
from crawler.fetcher import FetchError, fetch_html  # noqa: E402
from crawler.parser import extract_title, html_to_clean_text  # noqa: E402
from storage.writer import save_result  # noqa: E402

MAX_CHARS = 20000


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch a URL and extract structured info with Claude.")
    parser.add_argument("url", help="Page URL to crawl")
    args = parser.parse_args()

    try:
        html = fetch_html(args.url)
    except FetchError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)

    text = html_to_clean_text(html)
    title = extract_title(html)

    if len(text) > MAX_CHARS:
        print(
            f"Warning: page text is {len(text)} chars; only the first {MAX_CHARS} "
            "will be sent to Claude.",
            file=sys.stderr,
        )
        text = text[:MAX_CHARS]

    data = extract_structured_data(text)
    if title and not data.get("title"):
        data["title"] = title

    output_path = save_result(args.url, data)
    print(f"Saved extraction to {output_path}")


if __name__ == "__main__":
    main()
