# -*- coding: utf-8 -*-
"""Harvest — crawl index pages, collect document links, download and extract them in one pass.

Pipeline: index page(s) -> link discovery (PDF / Google Drive / Scribd / custom regex)
-> optional same-site crawl to ``depth`` -> parallel download (Range-chunked)
-> optional text extraction (PyMuPDF + OCR, Scribd JSONP) -> JSON manifest.
"""

import json
import re
import urllib.parse
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set

_LINK_RE = re.compile(r"\]\((https?://[^)\s]+)\)|(https?://[^\s\"'<>()\]]+)")
_DEFAULT_EXTS = (".pdf",)


@dataclass
class HarvestItem:
    url: str
    kind: str  # "file" | "gdrive" | "scribd"
    source_page: str
    path: str = ""
    ok: bool = False
    size_bytes: int = 0
    text_path: str = ""
    error: str = ""


@dataclass
class HarvestReport:
    pages_crawled: List[str] = field(default_factory=list)
    items: List[HarvestItem] = field(default_factory=list)

    @property
    def ok_count(self) -> int:
        return sum(1 for i in self.items if i.ok)

    def to_json(self) -> str:
        return json.dumps(
            {"pages_crawled": self.pages_crawled, "items": [asdict(i) for i in self.items]},
            indent=2,
            ensure_ascii=False,
        )


def extract_links(markdown: str) -> List[str]:
    """Return unique absolute URLs from Markdown/plain text, in order of appearance."""
    seen: Dict[str, None] = {}
    for m in _LINK_RE.finditer(markdown):
        u = (m.group(1) or m.group(2)).rstrip(".,;")
        seen.setdefault(u, None)
    return list(seen)


def classify_link(url: str, exts=_DEFAULT_EXTS, pattern: Optional[re.Pattern] = None) -> Optional[str]:
    """Return the link kind if it is a harvestable document, else None."""
    from scrap_master.channels.gdrive import extract_gdrive_id
    from scrap_master.channels.scribd import extract_scribd_id

    host = urllib.parse.urlparse(url).netloc.lower()
    if "scribd.com" in host and extract_scribd_id(url):
        return "scribd"
    if ("drive.google.com" in host or "docs.google.com" in host) and extract_gdrive_id(url):
        return "gdrive"
    path = urllib.parse.unquote(urllib.parse.urlparse(url).path).lower()
    if any(path.endswith(e) for e in exts):
        return "file"
    if pattern is not None and pattern.search(url):
        return "file"
    return None


def _safe_name(url: str, idx: int) -> str:
    raw = urllib.parse.unquote(url.split("?")[0].rstrip("/").split("/")[-1])
    name = re.sub(r"[^\w.\-]+", "_", raw).strip("._")
    return name or f"download_{idx}.bin"


def _same_site(a: str, b: str) -> bool:
    return urllib.parse.urlparse(a).netloc.lower() == urllib.parse.urlparse(b).netloc.lower()


def discover(
    start_urls: List[str],
    depth: int = 0,
    exts=_DEFAULT_EXTS,
    pattern: Optional[str] = None,
    max_pages: int = 50,
    workers: int = 8,
) -> HarvestReport:
    """Crawl start pages (and same-site pages up to ``depth``) and collect document links."""
    from scrap_master.channels.web import WebChannel

    rx = re.compile(pattern) if pattern else None
    web = WebChannel()
    report = HarvestReport()
    found: Dict[str, HarvestItem] = {}
    visited: Set[str] = set()
    frontier = list(dict.fromkeys(start_urls))

    for level in range(depth + 1):
