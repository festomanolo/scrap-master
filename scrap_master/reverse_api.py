# -*- coding: utf-8 -*-
"""Reverse-engineer a site's hidden JSON API from its network traffic.

    scrap-master reverse-api https://site.example/search?q=books

A headless browser loads the page (optionally scrolling), records every fetch/XHR call
that returns JSON, groups them into endpoints, and writes a Python client for them —
AI-written when an LLM is configured, otherwise from a built-in template.
Cookies, auth headers and tokens are never written to disk.
"""

import json
import re
import urllib.parse
from pathlib import Path
from typing import Callable, Dict, List, Optional

from scrap_master.utils.text import scrub_url_credentials

SENSITIVE_HEADERS = ("cookie", "set-cookie", "authorization", "proxy-authorization",
                     "x-csrf-token", "x-xsrf-token", "x-api-key", "x-auth-token")
_KEEP_HEADERS = ("accept", "content-type", "x-requested-with", "referer", "origin")
SAMPLE_CHARS = 1500
_SECRET_PARAM = re.compile(r"key|token|secret|auth|sig|session|passw|csrf|xsrf", re.I)
REDACTED = "<redacted>"
_ID_SEGMENT = re.compile(r"^(?:\d+|[0-9a-f]{8}-[0-9a-f-]{27}|[0-9a-f]{16,}|[A-Za-z0-9_-]{22,})$", re.I)


def scrub_headers(headers: Dict[str, str]) -> Dict[str, str]:
    """Keep only harmless, useful request headers."""
    return {k.lower(): v for k, v in (headers or {}).items()
            if k.lower() in _KEEP_HEADERS and k.lower() not in SENSITIVE_HEADERS}
