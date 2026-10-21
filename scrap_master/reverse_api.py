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


def scrub_params(params: Dict[str, str]) -> Dict[str, str]:
    """Blank out query values whose names look like credentials."""
    return {k: REDACTED if _SECRET_PARAM.search(k) else v for k, v in params.items()}


def is_api_call(resource_type: str, content_type: str) -> bool:
    return resource_type in ("xhr", "fetch") or "json" in (content_type or "").lower()


def capture(url: str, wait_ms: int = 6000, scrolls: int = 3) -> List[dict]:
    """Load `url` in headless Chromium and return the JSON API calls it makes."""
    from playwright.sync_api import sync_playwright

    from scrap_master.channels.web import _UA, launch_browser
    from scrap_master.utils.url import normalize_public_http_url

    url = normalize_public_http_url(url)
    calls: List[dict] = []

    def on_response(resp):
        req = resp.request
        ctype = resp.headers.get("content-type", "")
        if not is_api_call(req.resource_type, ctype) or "json" not in ctype.lower():
            return
        try:
            body = resp.text()
        except Exception:
            body = ""
        calls.append({
            "method": req.method,
            "url": _scrub_url(req.url),
            "status": resp.status,
            "headers": scrub_headers(req.headers),
            "post_data": (req.post_data or "")[:SAMPLE_CHARS],
            "content_type": ctype,
            "sample": body[:SAMPLE_CHARS],
        })

    with sync_playwright() as p:
        browser = launch_browser(p)
        try:
            page = browser.new_context(user_agent=_UA).new_page()
            page.on("response", on_response)
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            for _ in range(scrolls):
                page.mouse.wheel(0, 4000)
                page.wait_for_timeout(wait_ms // max(scrolls, 1))
        finally:
            browser.close()
    return calls


def _scrub_url(url: str) -> str:
    u = urllib.parse.urlsplit(scrub_url_credentials(url))
    query = urllib.parse.urlencode(scrub_params(dict(urllib.parse.parse_qsl(u.query, keep_blank_values=True))),
                                   safe="<>")
    return urllib.parse.urlunsplit(u._replace(query=query))
