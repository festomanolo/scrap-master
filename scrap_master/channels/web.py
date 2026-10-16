# -*- coding: utf-8 -*-
"""Web — any URL via Jina Reader. Always available."""

import urllib.request

from scrap_master.utils.url import normalize_public_http_url

from .base import Channel

_UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
_MAX_RESPONSE_BYTES = 5 * 1024 * 1024
_ANTIBOT_SCAN_BYTES = 4096


def _is_antibot_page(body: bytes) -> bool:
    """Recognize high-confidence Jina/Cloudflare challenge responses."""
    sample = body[:_ANTIBOT_SCAN_BYTES].decode("utf-8", errors="ignore").casefold()

    jina_captcha_warning = "warning:" in sample and "requiring captcha" in sample
    challenge_structure = any(
        marker in sample
        for marker in (
            "title: just a moment...",
            "## performing security verification",
            "title: attention required! | cloudflare",
        )
    )
    cloudflare_block = "title: attention required! | cloudflare" in sample and (
        "ray id" in sample or "/cdn-cgi/challenge-platform/" in sample
    )
    return (jina_captcha_warning and challenge_structure) or cloudflare_block


def _html_to_clean_markdown(html_text: str, base_url: str = "") -> str:
    """Convert raw HTML into clean Markdown with preserved links using BeautifulSoup."""
    import urllib.parse
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html_text, "html.parser")
    for tag in soup(["script", "style", "noscript", "svg", "footer", "nav"]):
        tag.decompose()

    # Convert <a> tags into [text](url) so PDF/GDrive/Scribd links are preserved
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if base_url and not href.startswith(("http://", "https://", "mailto:", "javascript:")):
            href = urllib.parse.urljoin(base_url, href)
        label = a.get_text(" ", strip=True) or href
        a.replace_with(f"[{label}]({href})")

    # Convert <iframe> src (e.g. Google Drive / Scribd embeds) into explicit links
    for iframe in soup.find_all("iframe", src=True):
        src = iframe["src"].strip()
        if base_url and src.startswith("//"):
            src = "https:" + src
        iframe.replace_with(f"\n[Embedded Document]({src})\n")

    lines = [line.strip() for line in soup.get_text("\n").splitlines() if line.strip()]
    return "\n".join(lines)


def _read_via_playwright(url: str, timeout_ms: int = 25000) -> str:
    """Render a JS/Cloudflare-protected page via headless Playwright Chromium and convert to Markdown."""
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            context = browser.new_context(user_agent=_UA)
            page = context.new_page()
            page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
            page.wait_for_timeout(1500)
            html_content = page.content()
            return _html_to_clean_markdown(html_content, base_url=url)
        finally:
            browser.close()


def _read_via_direct_http(url: str, timeout: int = 20) -> str:
    """Fetch HTML directly with browser headers and convert to Markdown with links."""
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": _UA,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read(_MAX_RESPONSE_BYTES + 1)
    return _html_to_clean_markdown(raw.decode("utf-8", errors="ignore"), base_url=url)


class WebChannel(Channel):
    name = "web"
    description = "Any web page"
    backends = ["Jina Reader", "Playwright Headless Chromium", "Direct HTTP + BeautifulSoup"]
    tier = 0

    def can_handle(self, url: str) -> bool:
        return True  # Fallback — handles any URL

    def check(self, config=None):
        # Always-available fallback channel: no local command, no network probe
        # (doctor already makes multiple network calls), keeps overhead at zero.
        self.active_backend = self.backends[0]
        return "ok", "Read any web page via Jina Reader (curl https://r.jina.ai/URL)"

    def read(self, url: str) -> str:
        """Read a web page via Jina Reader and return the full Markdown text."""
        url = normalize_public_http_url(url)
        jina_url = f"https://r.jina.ai/{url}"
        req = urllib.request.Request(
            jina_url,
            headers={"User-Agent": _UA, "Accept": "text/plain"},
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = resp.read(_MAX_RESPONSE_BYTES + 1)
        if len(body) > _MAX_RESPONSE_BYTES:
            raise ValueError(
                f"Jina Reader response exceeds {_MAX_RESPONSE_BYTES} byte limit"
            )
        if _is_antibot_page(body):
            raise RuntimeError(
                "Jina Reader returned an anti-bot challenge page — target content was not retrieved. "
                "Try a site-specific tool or open the page in a browser."
            )
        return body.decode("utf-8")
