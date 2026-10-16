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
