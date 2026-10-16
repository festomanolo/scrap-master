# -*- coding: utf-8 -*-
"""AI job runner — "today I want to scrape data about ..." -> organised project folder.

plan (Ollama / OpenRouter, or a keyword fallback) -> keyless web search (DuckDuckGo HTML)
-> save result pages as Markdown -> collect PDF / Drive / Scribd documents -> download,
extract, OCR -> AI report.md
"""

import json
import re
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Callable, List, Optional

from scrap_master.utils.filetypes import resolve, sources_for, types_from_text

_DDG_RESULT_RE = re.compile(r'class="result__a" href="([^"]+)"')

Log = Callable[[str], None]


def _unwrap(href: str) -> str:
    href = href.replace("&amp;", "&")
    qs = urllib.parse.parse_qs(urllib.parse.urlparse(href).query)
    return qs.get("uddg", [href])[0]


def _ddg_html(query: str) -> List[str]:
    url = "https://html.duckduckgo.com/html/?" + urllib.parse.urlencode({"q": query})
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=25) as resp:
        html = resp.read().decode("utf-8", errors="ignore")
    return [_unwrap(h) for h in _DDG_RESULT_RE.findall(html)]


def _ddg_lite(query: str) -> List[str]:
    from curl_cffi import requests as cffi

    html = cffi.post("https://lite.duckduckgo.com/lite/", data={"q": query},
                     impersonate="chrome", timeout=25).text
    return [_unwrap(h) for h in re.findall(r'class=.result-link.[^>]*href="([^"]+)"|href="([^"]+)"[^>]*class=.result-link.', html) for h in h if h]


def _bing_rss(query: str) -> List[str]:
    from curl_cffi import requests as cffi

    xml = cffi.get("https://www.bing.com/search", params={"q": query, "format": "rss"},
                   impersonate="chrome", timeout=25).text
    return re.findall(r"<item>.*?<link>(https?://[^<]+)</link>", xml, re.S)


def _browser_ddg(query: str) -> List[str]:
    from playwright.sync_api import sync_playwright

    from scrap_master.channels.web import launch_browser

    with sync_playwright() as p:
        browser = launch_browser(p)
        try:
            page = browser.new_page()
            page.goto("https://duckduckgo.com/?" + urllib.parse.urlencode({"q": query, "ia": "web"}),
                      wait_until="domcontentloaded", timeout=60000)
            page.wait_for_selector("a[data-testid=result-title-a]", timeout=30000)
            return page.eval_on_selector_all("a[data-testid=result-title-a]", "els => els.map(a => a.href)")
        finally:
            browser.close()


SEARCH_BACKENDS = (_ddg_html, _ddg_lite, _bing_rss, _browser_ddg)


def web_search(query: str, max_results: int = 8) -> List[str]:
    """Keyless web search. Tries DuckDuckGo HTML/Lite, Bing RSS, then a real browser."""
    errors = []
    for backend in SEARCH_BACKENDS:
        try:
            urls = [u for u in backend(query) if u.startswith("http") and "duckduckgo.com" not in u]
            if urls:
                return list(dict.fromkeys(urls))[:max_results]
        except Exception as e:
            errors.append(f"{backend.__name__}: {type(e).__name__}")
    if errors:
        raise RuntimeError("all search backends failed: " + ", ".join(errors))
    return []


def fallback_plan(request: str) -> dict:
    return {
        "project_name": request[:40],
        "queries": [request, f"{request} pdf"],
        "urls": [u for u in re.findall(r"https?://\S+", request)],
        "file_types": list(types_from_text(request) or (".pdf",)),
        "depth": 0,
        "extract_text": True,
        "max_documents": 20,
    }


def run_job(
    request: str,
    log: Log = print,
    use_ai: bool = True,
    plan: Optional[dict] = None,
    only: Optional[List[str]] = None,
    organize: bool = True,
) -> Path:
    """Run a full scraping job and return its project folder."""
    from scrap_master import ai
    from scrap_master.channels.web import WebChannel
    from scrap_master.utils.harvest import HarvestItem, classify_link, discover, fetch
    from scrap_master.workspace import new_project, slugify

    ai_ok = use_ai
    if plan is None:
        if use_ai:
            try:
                info = ai.provider_info()
                log(f"🧠 Planning with {info['provider']} ({info['model']})…")
                plan = ai.plan_job(request)
            except Exception as e:
                log(f"⚠ AI planning unavailable ({e}); using keyword plan")
                ai_ok = False
        plan = plan or fallback_plan(request)

    project = new_project(plan["project_name"])
    data = project / "data"
    (data / "plan.json").write_text(json.dumps(plan, indent=2), encoding="utf-8")
    log(f"📁 Project: {project}")
    for q in plan["queries"]:
        log(f"   • search: {q}")

    # 1. Search
    results: List[str] = list(plan["urls"])
    with ThreadPoolExecutor(max_workers=4) as pool:
        for q, urls in zip(plan["queries"], pool.map(_safe_search, plan["queries"])):
            log(f"🔎 {len(urls):>2} results  ← {q}")
            results.extend(u for u in urls if u not in results)
    (data / "search_results.json").write_text(json.dumps(results, indent=2), encoding="utf-8")

    fallback_seeds = False
    if not results:
        results = seed_sites()
        fallback_seeds = bool(results)
        log(f"⚠ Search returned nothing — crawling your favourite sites: {', '.join(results) or 'none set'}")

    exts = tuple(e.lower() for e in plan["file_types"])
    direct = [u for u in results if classify_link(u, exts)]
    pages = [u for u in results if u not in direct]
    log(f"📄 {len(direct)} direct documents, {len(pages)} pages to crawl")

    # 2. Crawl pages, collect linked documents
    report = discover(pages, depth=1 if fallback_seeds else plan["depth"], exts=exts, max_pages=30)
    if fallback_seeds:
        report.items = _relevant(report.items, request)
    known = {i.url for i in report.items}
    for u in direct:
        if u not in known:
            report.items.insert(0, HarvestItem(url=u, kind=classify_link(u, exts), source_page="search"))
    report.items = report.items[: plan["max_documents"]]

    # Pages that could not be read directly: try the full web chain once more.
    web = WebChannel()
    for u in pages:
        if u not in report.page_text:
            try:
                report.page_text[u] = web.read(u)
            except Exception:
                pass
    for i, (u, md) in enumerate(report.page_text.items(), 1):
        host = urllib.parse.urlparse(u).netloc
        name = f"{i:02d}_{slugify(host + urllib.parse.urlparse(u).path, 60)}.md"
        (project / "pages" / name).write_text(f"<!-- {u} -->\n{md}", encoding="utf-8")
    log(f"🌐 Saved {len(report.page_text)} pages as Markdown")

    # 3. Download + extract
    log(f"⬇ Downloading {len(report.items)} documents…")
    fetch(
        report,
        project / "pdfs",
        extract_text=plan["extract_text"],
        scribd_dir=project / "scribd",
        text_dir=project / "markdown",
        manifest_dir=data,
    )
    for it in report.items:
        log(f"   {'✅' if it.ok else '❌'} [{it.kind}] {Path(it.path).name if it.path else it.url}"
            + ("" if it.ok else f" — {it.error[:80]}"))
    log(f"📦 {report.ok_count}/{len(report.items)} documents saved")

    # 4. Report
    material = _material(project, report)
    if ai_ok:
        try:
            log("📝 Writing AI report…")
            body = ai.summarize(request, material)
        except Exception as e:
            log(f"⚠ AI report failed ({e})")
            body = material
    else:
        body = material
    (project / "report.md").write_text(f"# {request}\n\n{body}\n", encoding="utf-8")
    log(f"✨ Done → {project / 'report.md'}")
    return project


DEFAULT_SEED_SITES = ["https://maktaba.tetea.org/", "https://msomibora.com/", "https://learninghubtz.co.tz/"]


def seed_sites() -> List[str]:
    from scrap_master.config import Config

    raw = Config().get("seed_sites")
    if raw is None:
        return list(DEFAULT_SEED_SITES)
    return [u.strip() for u in str(raw).split(",") if u.strip().startswith("http")]


def _relevant(items, request: str):
    """Keep items whose URL or source page mentions a request keyword (all items if none match)."""
    words = [w for w in re.findall(r"[a-z0-9]+", request.lower()) if len(w) > 3]
    hits = [i for i in items if any(w in (i.url + " " + i.source_page).lower() for w in words)]
    return hits or items


def _safe_search(q: str) -> List[str]:
    try:
        return web_search(q)
    except Exception:
        return []



def _material(project: Path, report) -> str:
    parts = ["## Documents"]
    for it in report.items:
        parts.append(f"- {'OK' if it.ok else 'FAILED'} [{it.kind}] {it.url}"
                     + (f" -> {Path(it.path).relative_to(project)}" if it.ok and it.path else ""))
    parts.append("\n## Excerpts")
    for md in sorted((project / "markdown").glob("*.md")) + sorted((project / "scribd").glob("*.md")):
        parts.append(f"\n### {md.name}\n{md.read_text(encoding='utf-8')[:1500]}")
    for md in sorted((project / "pages").glob("*.md"))[:8]:
        parts.append(f"\n### {md.name}\n{md.read_text(encoding='utf-8')[:800]}")
    return "\n".join(parts)
