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
