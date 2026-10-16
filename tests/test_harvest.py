from scrap_master.utils.harvest import _same_site, classify_link, extract_links


def test_extract_links_dedupes_markdown_and_bare_urls():
    md = "[a](https://x.org/a.pdf) see https://x.org/a.pdf and https://x.org/b."
    assert extract_links(md) == ["https://x.org/a.pdf", "https://x.org/b"]
