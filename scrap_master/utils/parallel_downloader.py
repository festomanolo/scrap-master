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
