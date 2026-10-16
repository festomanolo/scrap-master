from scrap_master.utils.harvest import _same_site, classify_link, extract_links


def test_extract_links_dedupes_markdown_and_bare_urls():
