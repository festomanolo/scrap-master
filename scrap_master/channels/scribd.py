# -*- coding: utf-8 -*-
"""Scribd channel — direct API / Embed / JSONP asset extraction.

Instead of loading the public Scribd web UI (which loads paywall modals, CSS
blur filters, and ad trackers), this channel communicates directly with:
  1. Scribd OEmbed JSON API (`/services/oembed`) for document metadata
  2. Scribd Embed Reader (`/embeds/<doc_id>/content`) for unblurred inline DOM
     text layers and `docManager.addPage(...)` asset manifests
  3. Scribd Asset CDN (`html.scribdassets.com/.../pages/<N>-<hash>.jsonp`)
     in parallel via ThreadPoolExecutor, automatically decompressing gzip/zip
     streams and reconstructing reading order from (x, y) coordinates.
"""

from concurrent.futures import ThreadPoolExecutor, as_completed
import gzip
import html as htmllib
import json
import re
from typing import Dict, List, Optional, Tuple
import urllib.parse
import urllib.request
import zipfile
import io

from .base import Channel

_MOBILE_UA = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
)
_SCRIBD_URL_RE = re.compile(
    r"scribd\.com/(?:document|doc|presentation|embeds)/(\d+)", re.IGNORECASE
)


def extract_scribd_id(url_or_id: str) -> Optional[str]:
    """Extract numeric Scribd document ID from a URL or raw ID string."""
    s = url_or_id.strip()
    if s.isdigit():
        return s
    m = _SCRIBD_URL_RE.search(s)
    return m.group(1) if m else None


def _decompress_jsonp_bytes(raw: bytes) -> str:
    """Decompress Scribd .jsonp payload (raw UTF-8, gzip, or PK zip stream)."""
    # 1. Try GZIP magic bytes (1f 8b)
    gz_idx = raw.find(b"\x1f\x8b")
    if gz_idx != -1:
        try:
            return gzip.decompress(raw[gz_idx:]).decode("utf-8", errors="ignore")
        except Exception:
            pass

    # 2. Try ZIP archive (PK\x03\x04)
    if raw[:2] == b"PK":
        try:
            with zipfile.ZipFile(io.BytesIO(raw)) as zf:
                names = zf.namelist()
                if names:
                    return zf.read(names[0]).decode("utf-8", errors="ignore")
        except Exception:
            pass
        # Raw deflate fallback after PK local header (30 bytes + filename len + extra len)
        if len(raw) > 30:
            import zlib
            fname_len = int.from_bytes(raw[26:28], "little")
            extra_len = int.from_bytes(raw[28:30], "little")
            offset = 30 + fname_len + extra_len
            try:
                return zlib.decompress(raw[offset:], -zlib.MAX_WBITS).decode(
                    "utf-8", errors="ignore"
                )
            except Exception:
                pass

    return raw.decode("utf-8", errors="ignore")


def _parse_scribd_page_html(raw_html: str) -> Tuple[str, List[str]]:
    """Reconstruct readable lines and image URLs from a Scribd page HTML/JSONP block."""
    # Unescape JSONP string escapes if wrapped in window.pageN_callback(["..."])
    m_cb = re.search(r'page\d+_callback\(\["(.*)"\]\)', raw_html, re.S)
    if m_cb:
        body = m_cb.group(1)
        body = (
            body.replace(r"\"", '"')
            .replace(r"\n", "\n")
            .replace(r"\t", "\t")
            .replace(r"\/", "/")
        )
    else:
        body = raw_html

    items: List[Tuple[int, int, str]] = []
    for m in re.finditer(
        r'<span class=["\']?a["\']?\s+style=["\']left:(\d+)px;top:(\d+)px[^"\']*["\']>(.*?)(?=<span class=["\']?a|</div>)',
        body,
        re.S,
    ):
        x, y, inner = int(m.group(1)), int(m.group(2)), m.group(3)
        clean = re.sub(r"<[^>]+>", "", inner)
        clean = htmllib.unescape(clean).replace("\xa0", " ").replace("Â", " ").strip()
        if clean:
            items.append((y, x, clean))

    items.sort(key=lambda t: (t[0] // 40, t[1]))
    lines: List[str] = []
    cur_y: Optional[int] = None
    cur_line: List[str] = []
    for y, x, txt in items:
        if cur_y is None or abs(y - cur_y) > 45:
            if cur_line:
                lines.append(" ".join(cur_line))
            cur_line = [txt]
            cur_y = y
        else:
            cur_line.append(txt)
    if cur_line:
        lines.append(" ".join(cur_line))

    images = re.findall(
        r'https://html\.scribdassets\.com/[^"\'\s>]+?\.(?:jpg|png)', body
    )
    return "\n".join(lines), images


class ScribdChannel(Channel):
    """Direct Scribd API & Embed/JSONP document extractor."""

    name = "scribd"
    description = "Scribd documents and marking schemes (API + JSONP bypass)"
    backends = ["Scribd Embed/JSONP API", "Jina Reader"]
    tier = 0

    def can_handle(self, url: str) -> bool:
        return extract_scribd_id(url) is not None

    def check(self, config=None) -> Tuple[str, str]:
        self.active_backend = self.backends[0]
        return (
            "ok",
            "Direct Scribd OEmbed + Embed/JSONP asset API ready (zero-config, parallel page fetch)",
        )

    def fetch_oembed(self, doc_id: str, timeout: int = 15) -> Dict:
