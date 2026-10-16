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


def _site(url: str) -> str:
    host = urllib.parse.urlparse(url).netloc.lower()
    return host[4:] if host.startswith("www.") else host


def _same_site(a: str, b: str) -> bool:
    return _site(a) == _site(b)


def discover(
    start_urls: List[str],
    depth: int = 0,
    exts=_DEFAULT_EXTS,
    pattern: Optional[str] = None,
    max_pages: int = 50,
    workers: int = 8,
) -> HarvestReport:
    """Crawl start pages (and same-site pages up to ``depth``) and collect document links."""
    from scrap_master.channels.web import WebChannel, _read_via_direct_http

    rx = re.compile(pattern) if pattern else None
    web = WebChannel()
    report = HarvestReport()
    found: Dict[str, HarvestItem] = {}
    visited: Set[str] = set()
    frontier = list(dict.fromkeys(start_urls))

    for level in range(depth + 1):
        batch = [u for u in frontier if u not in visited][: max(0, max_pages - len(visited))]
        if not batch:
            break
        visited.update(batch)

        def _read(u):
            # Direct HTML keeps every <a>/<iframe> link; Jina Reader often drops them,
            # so use it (and its curl_cffi / Playwright fallbacks) only when direct fails.
            try:
                md = _read_via_direct_http(u)
                if len(extract_links(md)) > 5:
            try:
                return u, web.read(u)
            except Exception:
                return u, ""

        next_frontier: List[str] = []
        with ThreadPoolExecutor(max_workers=max(1, min(workers, len(batch)))) as pool:
            for page_url, md in pool.map(_read, batch):
                if not md:
                    continue
                report.pages_crawled.append(page_url)
                for link in extract_links(md):
                    kind = classify_link(link, exts, rx)
                    if kind:
                        found.setdefault(link, HarvestItem(url=link, kind=kind, source_page=page_url))
                    elif level < depth and _same_site(link, page_url):
                        next_frontier.append(link.split("#")[0])
        frontier = next_frontier

    report.items = list(found.values())
    return report


def harvest(
    start_urls: List[str],
    out_dir,
    depth: int = 0,
    exts=_DEFAULT_EXTS,
    pattern: Optional[str] = None,
    extract_text: bool = False,
    ocr: bool = True,
    workers: int = 12,
    chunks: int = 8,
    max_pages: int = 50,
    limit: Optional[int] = None,
) -> HarvestReport:
    """Discover, download and (optionally) extract every document linked from the start pages."""
    from scrap_master.channels.gdrive import extract_gdrive_id, get_direct_gdrive_url
    from scrap_master.channels.scribd import ScribdChannel, extract_scribd_id
    from scrap_master.utils.parallel_downloader import download_batch_parallel

    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    report = discover(start_urls, depth=depth, exts=exts, pattern=pattern, max_pages=max_pages)
    if limit is not None:
        report.items = report.items[:limit]

    # Binary downloads (direct files + Google Drive exports)
    file_items = [i for i in report.items if i.kind in ("file", "gdrive")]
    pairs, used = [], set()
    for idx, it in enumerate(file_items, 1):
        if it.kind == "gdrive":
            fid, _ = extract_gdrive_id(it.url)
            url, name = get_direct_gdrive_url(it.url), f"gdrive_{fid}.pdf"
        else:
            url, name = it.url, _safe_name(it.url, idx)
        while name in used:
            name = f"{idx}_{name}"
        used.add(name)
        it.path = str(out / name)
        pairs.append((url, out / name))
    for it, res in zip(file_items, download_batch_parallel(pairs, max_workers=workers, chunks_per_file=chunks)):
        it.ok, it.size_bytes, it.error = res.ok, res.size_bytes, res.error

    # Scribd documents are extracted directly to Markdown
    scribd_items = [i for i in report.items if i.kind == "scribd"]

    def _scribd(it: HarvestItem):
        try:
            doc = ScribdChannel().extract_document(it.url)
            p = out / f"scribd_{extract_scribd_id(it.url)}.md"
            p.write_text(doc["markdown"], encoding="utf-8")
            it.path = it.text_path = str(p)
            it.ok, it.size_bytes = True, p.stat().st_size
        except Exception as e:
            it.error = f"{type(e).__name__}: {e}"

    if scribd_items:
        with ThreadPoolExecutor(max_workers=min(4, len(scribd_items))) as pool:
            list(pool.map(_scribd, scribd_items))

    if extract_text:
        _extract_texts([i for i in file_items if i.ok and i.path.lower().endswith(".pdf")], ocr)

    (out / "harvest_manifest.json").write_text(report.to_json(), encoding="utf-8")
    return report


def _extract_texts(items: List[HarvestItem], ocr: bool) -> None:
    from scrap_master.utils.pdf_reader import extract_pdf_text

    # OCR runs a single native batch process per PDF, so extract PDFs one at a time.
    for it in items:
        try:
            res = extract_pdf_text(it.path, ocr_fallback=ocr)
            p = Path(it.path).with_suffix(".md")
            p.write_text(res["markdown"], encoding="utf-8")
            it.text_path = str(p)
        except Exception as e:
            it.error = f"text extraction failed: {type(e).__name__}: {e}"
