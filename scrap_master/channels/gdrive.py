# -*- coding: utf-8 -*-
"""Google Drive / Google Docs direct binary downloader and text extractor.

Converts embedded viewer URLs (`/file/d/<ID>/view`, `/file/d/<ID>/preview`,
`/open?id=<ID>`, `/document/d/<ID>/edit`) into direct binary download URLs,
handles Google's large-file virus-scan confirmation token (`confirm=t`),
and downloads files using the parallel HTTP Range downloader.
"""

from pathlib import Path
import re
from typing import Dict, Optional, Tuple, Union
import urllib.request

from scrap_master.channels.base import Channel
from scrap_master.utils.parallel_downloader import DownloadResult, download_one

_GDRIVE_FILE_RE = re.compile(
    r"(?:drive\.google\.com/file/d/|drive\.google\.com/open\?id=|drive\.google\.com/uc\?.*id=|docs\.google\.com/(?:document|spreadsheets|presentation)/d/)([a-zA-Z0-9_-]{15,})"
)


def extract_gdrive_id(url_or_id: str) -> Optional[Tuple[str, str]]:
    """Extract (file_id, doc_type) from a Google Drive/Docs URL or raw ID."""
    s = url_or_id.strip()
    if re.fullmatch(r"[a-zA-Z0-9_-]{25,}", s):
        return s, "file"
    m = _GDRIVE_FILE_RE.search(s)
    if not m:
        return None
    fid = m.group(1)
    if "docs.google.com/document" in s:
        return fid, "document"
    if "docs.google.com/spreadsheets" in s:
        return fid, "spreadsheets"
    if "docs.google.com/presentation" in s:
        return fid, "presentation"
    return fid, "file"


def get_direct_gdrive_url(url_or_id: str) -> str:
    """Convert any Google Drive / Docs viewer link into a direct PDF/binary export URL."""
    parsed = extract_gdrive_id(url_or_id)
    if not parsed:
        return url_or_id
    fid, dtype = parsed
    if dtype == "document":
        return f"https://docs.google.com/document/d/{fid}/export?format=pdf"
    if dtype == "spreadsheets":
        return f"https://docs.google.com/spreadsheets/d/{fid}/export?format=pdf"
    if dtype == "presentation":
        return f"https://docs.google.com/presentation/d/{fid}/export/pdf"
    return f"https://drive.usercontent.google.com/download?id={fid}&export=download&confirm=t"


class GoogleDriveChannel(Channel):
    """Direct Google Drive / Docs binary and PDF extractor."""

    name = "gdrive"
    description = "Google Drive & Docs embedded viewer bypass"
    backends = ["Google Drive Direct Export API"]
    tier = 0

    def can_handle(self, url: str) -> bool:
        return extract_gdrive_id(url) is not None

    def check(self, config=None) -> Tuple[str, str]:
        self.active_backend = self.backends[0]
        return (
            "ok",
            "Google Drive & Docs direct binary/PDF export ready (zero-config)",
        )

    def download(
        self,
        url_or_id: str,
        dest: Union[str, Path],
        verify_pdf: bool = False,
        chunks_per_file: int = 8,
    ) -> DownloadResult:
        """Download a Google Drive / Docs file directly to `dest`."""
        direct_url = get_direct_gdrive_url(url_or_id)
        return download_one(
            direct_url,
            dest,
            verify_pdf=verify_pdf,
            chunks_per_file=chunks_per_file,
        )
