# -*- coding: utf-8 -*-
"""High-speed parallel file/PDF downloader with automatic backoff retries."""

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
import time
from typing import Dict, Iterable, List, Optional, Tuple, Union
import urllib.request

_DEFAULT_UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"


@dataclass
class DownloadResult:
    url: str
    path: Path
    ok: bool
    size_bytes: int = 0
    is_valid_pdf: bool = False
    attempts: int = 1
    elapsed_sec: float = 0.0
    error: str = ""


def download_one(
    url: str,
    dest: Union[str, Path],
    timeout: int = 20,
    retries: int = 3,
    verify_pdf: bool = False,
    headers: Optional[Dict[str, str]] = None,
) -> DownloadResult:
    """Download a single file with exponential backoff retries and optional PDF magic-byte check."""
    dest_path = Path(dest)
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    req_headers = {"User-Agent": _DEFAULT_UA}
    if headers:
        req_headers.update(headers)

    t0 = time.monotonic()
    last_err = ""
    for attempt in range(1, retries + 2):
        try:
            req = urllib.request.Request(url, headers=req_headers)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = resp.read()
            is_pdf = data[:4] == b"%PDF"
            if verify_pdf and not is_pdf:
                raise ValueError("Downloaded payload does not start with %PDF header")
            dest_path.write_bytes(data)
            return DownloadResult(
                url=url,
                path=dest_path,
                ok=True,
                size_bytes=len(data),
                is_valid_pdf=is_pdf,
                attempts=attempt,
                elapsed_sec=round(time.monotonic() - t0, 3),
            )
        except Exception as e:  # noqa: BLE001
            last_err = str(e)
            if attempt <= retries:
                time.sleep(0.5 * (2 ** (attempt - 1)))

    return DownloadResult(
        url=url,
        path=dest_path,
        ok=False,
        attempts=retries + 1,
        elapsed_sec=round(time.monotonic() - t0, 3),
        error=last_err,
