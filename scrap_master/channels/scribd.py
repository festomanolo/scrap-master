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
