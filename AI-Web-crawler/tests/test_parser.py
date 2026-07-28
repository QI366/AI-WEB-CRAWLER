from crawler.parser import extract_title, html_to_clean_text

SAMPLE_HTML = """
<html>
<head><title>Sample Page</title></head>
<body>
<nav>Menu</nav>
<h1>Hello World</h1>
<p>This is a paragraph.</p>
<script>console.log('noise')</script>
</body>
</html>
"""


def test_html_to_clean_text_strips_noise():
    text = html_to_clean_text(SAMPLE_HTML)
    assert "Hello World" in text
    assert "This is a paragraph." in text
    assert "console.log" not in text
    assert "Menu" not in text


def test_extract_title():
    assert extract_title(SAMPLE_HTML) == "Sample Page"
