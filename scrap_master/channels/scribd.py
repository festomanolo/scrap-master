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
        """Fetch document metadata from Scribd's public OEmbed API."""
        url = (
            "https://www.scribd.com/services/oembed?format=json&url="
            f"https://www.scribd.com/document/{doc_id}"
        )
        req = urllib.request.Request(url, headers={"User-Agent": _MOBILE_UA})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8", errors="ignore"))

    def extract_document(
        self,
        url_or_id: str,
        max_workers: int = 10,
        timeout: int = 20,
        session_cookie: Optional[str] = None,
    ) -> Dict:
        """Extract all pages from a Scribd document via the Embed + JSONP asset API in parallel."""
        doc_id = extract_scribd_id(url_or_id)
        if not doc_id:
            raise ValueError(f"Could not extract Scribd document ID from: {url_or_id}")

        headers = {"User-Agent": _MOBILE_UA}
        if session_cookie:
            headers["Cookie"] = session_cookie

        metadata = {}
        try:
            metadata = self.fetch_oembed(doc_id, timeout=timeout)
        except Exception:
            pass

        embed_url = f"https://www.scribd.com/embeds/{doc_id}/content"
        req = urllib.request.Request(embed_url, headers=headers)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            embed_html = resp.read().decode("utf-8", errors="ignore")

        pages_text: Dict[int, str] = {}
        pages_images: Dict[int, List[str]] = {}

        # 1. Parse inline outer_page_N blocks present directly in /embeds/<id>/content
        for m in re.finditer(
            r'id="outer_page_(\d+)"(.*?)(?=id="outer_page_|<script)',
            embed_html,
            re.S,
        ):
            pnum = int(m.group(1))
            txt, imgs = _parse_scribd_page_html(m.group(2))
            if txt or imgs:
                pages_text[pnum] = txt
                pages_images[pnum] = imgs

        # 2. Discover all .jsonp page asset URLs from docManager.addPage(...)
        jsonp_tasks: Dict[int, str] = {}
        for m in re.finditer(
            r"https://html\.scribdassets\.com/[^\"'\s]+/pages/(\d+)-[a-zA-Z0-9]+\.jsonp",
            embed_html,
        ):
            pnum = int(m.group(1))
            jsonp_tasks[pnum] = m.group(0)

        # 3. Fetch all .jsonp page slices concurrently
        if jsonp_tasks:
            def _fetch_one(p_num: int, j_url: str):
                r = urllib.request.Request(j_url, headers=headers)
                with urllib.request.urlopen(r, timeout=timeout) as resp_j:
                    raw_bytes = resp_j.read()
                decoded = _decompress_jsonp_bytes(raw_bytes)
                return p_num, _parse_scribd_page_html(decoded)

            with ThreadPoolExecutor(max_workers=min(max_workers, len(jsonp_tasks))) as pool:
                futures = [
                    pool.submit(_fetch_one, pnum, jurl)
                    for pnum, jurl in jsonp_tasks.items()
                ]
                for fut in as_completed(futures):
                    pnum, (txt, imgs) = fut.result()
                    if txt or not pages_text.get(pnum):
                        pages_text[pnum] = txt
                    if imgs:
                        pages_images[pnum] = imgs

        sorted_pages = sorted(set(pages_text.keys()) | set(pages_images.keys()))
        markdown_sections = []
        title = metadata.get("title") or f"Scribd Document {doc_id}"
        markdown_sections.append(f"# {title}\n")
        if metadata.get("author_name"):
            markdown_sections.append(f"**Author:** {metadata['author_name']}  ")
        markdown_sections.append(
            f"**Document ID:** `{doc_id}` | **Pages Extracted:** {len(sorted_pages)}\n"
        )

        for pnum in sorted_pages:
            markdown_sections.append(f"\n---\n## Page {pnum}\n")
            if pages_text.get(pnum):
                markdown_sections.append(pages_text[pnum])
            for img in pages_images.get(pnum, []):
                markdown_sections.append(f"\n![Page {pnum} Image]({img})")

        return {
            "doc_id": doc_id,
            "title": title,
            "author": metadata.get("author_name"),
            "page_count": len(sorted_pages),
            "pages": {p: pages_text.get(p, "") for p in sorted_pages},
            "images": {p: pages_images.get(p, []) for p in sorted_pages},
            "markdown": "\n".join(markdown_sections),
        }

    def read(self, url: str) -> str:
        """Read a Scribd document URL and return its full Markdown text."""
        return self.extract_document(url)["markdown"]
