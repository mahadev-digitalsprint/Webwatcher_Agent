from webwatcher.normalization.html_normalizer import normalize_html


def test_html_normalizer_removes_script_and_extracts_pdf() -> None:
    html = """
    <html>
      <head><script>alert('x')</script></head>
      <body>
        <h1>Quarterly Results</h1>
        <p>Revenue: INR 100 Cr</p>
        <a href="/docs/result.pdf">Download</a>
      </body>
    </html>
    """
    normalized = normalize_html(html, "https://example.com/investor")
    assert "alert" not in normalized.clean_text
    assert normalized.pdf_links == ["https://example.com/docs/result.pdf"]
    assert normalized.page_hash
    assert normalized.numbers_hash

