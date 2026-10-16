from scrap_master.utils.harvest import _same_site, classify_link, extract_links


def test_extract_links_dedupes_markdown_and_bare_urls():
    md = "[a](https://x.org/a.pdf) see https://x.org/a.pdf and https://x.org/b."
    assert extract_links(md) == ["https://x.org/a.pdf", "https://x.org/b"]


def test_classify_link_kinds():
    assert classify_link("https://x.org/My%20Paper.PDF") == "file"
    assert classify_link("https://drive.google.com/file/d/abcDEF123456789/view") == "gdrive"
    assert classify_link("https://www.scribd.com/document/843737831/Ics") == "scribd"
    assert classify_link("https://x.org/page/2/") is None


def test_same_site_ignores_www():
    assert _same_site("https://msomibora.com/", "https://www.msomibora.com/page/2/")
    assert not _same_site("https://a.com/", "https://b.com/")


def test_classify_link_respects_sources_and_exts():
    assert classify_link("https://www.scribd.com/document/843737831/Ics", sources=()) is None
    assert classify_link("https://x.org/deck.pptx", (".pptx",)) == "file"
    assert classify_link("https://x.org/a.pdf", (".pptx",)) is None
