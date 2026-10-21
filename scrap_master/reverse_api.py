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


def path_template(path: str) -> str:
    """/api/items/12345/reviews -> /api/items/{id}/reviews"""
    return "/".join("{id}" if _ID_SEGMENT.match(seg) else seg for seg in path.split("/"))


def group_endpoints(calls: List[dict]) -> List[dict]:
    """Collapse raw calls into unique endpoints with their query params and one sample."""
    endpoints: Dict[tuple, dict] = {}
    for c in calls:
        u = urllib.parse.urlsplit(c["url"])
        key = (c["method"], u.netloc, path_template(u.path))
        ep = endpoints.setdefault(key, {
            "method": c["method"],
            "base": f"{u.scheme}://{u.netloc}",
            "path": key[2],
            "params": {},
            "headers": c.get("headers", {}),
            "body": c.get("post_data", ""),
            "status": c.get("status"),
            "sample": c.get("sample", ""),
            "hits": 0,
        })
        ep["hits"] += 1
        for k, v in urllib.parse.parse_qsl(u.query, keep_blank_values=True):
            ep["params"].setdefault(k, v)
        ep["params"] = scrub_params(ep["params"])
    return sorted(endpoints.values(), key=lambda e: -e["hits"])


def _func_name(ep: dict, used: set) -> str:
    words = [w for w in re.split(r"[^A-Za-z0-9]+", ep["path"]) if w and w != "id" and not w.isdigit()]
    stem = "_".join(words[-3:]).lower() or "root"
    name = f"{ep['method'].lower()}_{stem}"
    base, n = name, 2
    while name in used:
        name, n = f"{base}_{n}", n + 1
    used.add(name)
    return name


def template_client(endpoints: List[dict], site: str) -> str:
    """Deterministic requests-based client — used when no LLM is available."""
    used: set = set()
    lines = [
        f'"""API client for {site} — generated by scrap-master reverse-api."""',
        "",
        "import requests",
        "",
        "",
        "class Client:",
        "    def __init__(self, session=None):",
        "        self.s = session or requests.Session()",
        '        self.s.headers["User-Agent"] = "Mozilla/5.0"',
    ]
    for ep in endpoints:
        name = _func_name(ep, used)
        ids = [f"id{i}" if i > 1 else "id" for i in range(1, ep["path"].count("{id}") + 1)]
        names = iter(ids)
        path = re.sub(r"\{id\}", lambda _: "{%s}" % next(names), ep["path"])
        has_body = ep["method"] in ("POST", "PUT", "PATCH")
        args = ["self"] + ids + (["body=None"] if has_body else []) + ["**params"]
        defaults = json.dumps({k: v for k, v in ep["params"].items() if v != REDACTED},
                              ensure_ascii=False)
        url = f'f"{ep["base"]}{path}"' if ids else repr(ep["base"] + path)
        lines += [
            "",
            f"    def {name}({', '.join(args)}):",
            f'        """{ep["method"]} {ep["path"]}  (seen {ep["hits"]}x)"""',
            f"        query = {{**{defaults}, **params}}",
        ]
        if has_body:
            lines.append(f"        r = self.s.request({ep['method']!r}, {url}, params=query, json=body)")
        else:
            lines.append(f"        r = self.s.request({ep['method']!r}, {url}, params=query)")
        lines += ["        r.raise_for_status()", "        return r.json()"]
    return "\n".join(lines) + "\n"


CLIENT_PROMPT = """You write Python API clients from captured browser traffic.
Write ONE self-contained Python module using `requests` with a `Client` class that has one
clear, well-named method per endpoint below (path ids become arguments, query params become
keyword arguments with the observed values as defaults). Infer pagination when you see
page/offset/cursor params. Never hard-code cookies or auth tokens.
Reply with ONLY the Python code."""


def ai_client(endpoints: List[dict], site: str, chat: Optional[Callable] = None) -> str:
    from scrap_master import ai

    chat = chat or ai.chat
    brief = json.dumps([{k: ep[k] for k in ("method", "base", "path", "params", "body", "sample")}
                        for ep in endpoints[:25]], indent=1, ensure_ascii=False)
    reply = chat([{"role": "system", "content": CLIENT_PROMPT},
                  {"role": "user", "content": f"Site: {site}\nEndpoints:\n{brief}"}])
    m = re.search(r"```(?:python)?\n(.*?)```", reply, re.S)
    code = (m.group(1) if m else reply).strip() + "\n"
    compile(code, "api_client.py", "exec")  # reject replies that are not valid Python
    return code
