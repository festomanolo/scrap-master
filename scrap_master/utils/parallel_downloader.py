# -*- coding: utf-8 -*-
"""High-speed parallel file/PDF downloader with HTTP Range chunk splitting and backoff retries.

Combines two levels of parallelism:
  1. File-level parallelism (`download_batch_parallel`): downloads multiple files concurrently.
  2. Byte-range chunk parallelism (`download_one` with `chunks_per_file > 1`): splits files larger
     than `min_chunk_size_bytes` (default 256 KB) into parallel `Range: bytes=start-end` requests
     to bypass per-TCP-connection server bandwidth throttling (e.g. ~22 KB/s per stream).
"""

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
import time
from typing import Dict, Iterable, List, Optional, Tuple, Union
import urllib.request

_DEFAULT_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)


@dataclass
class DownloadResult:
    url: str
    path: Path
    ok: bool
    size_bytes: int = 0
    is_valid_pdf: bool = False
    attempts: int = 1
    chunks_used: int = 1
    elapsed_sec: float = 0.0
    error: str = ""


def _probe_range_support(
    url: str, headers: Dict[str, str], timeout: int
) -> Tuple[Optional[int], bool]:
    """Probe file size and HTTP 206 Partial Content support using a 1-byte Range GET."""
    probe_headers = dict(headers)
    probe_headers["Range"] = "bytes=0-0"
    req = urllib.request.Request(url, headers=probe_headers)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        status = getattr(resp, "status", resp.getcode())
        content_range = resp.headers.get("Content-Range", "")
        # e.g. "bytes 0-0/4523456"
        if status == 206 and "/" in content_range:
            total_str = content_range.split("/")[-1].strip()
            if total_str.isdigit():
                return int(total_str), True
        content_len = resp.headers.get("Content-Length", "")
        if content_len.isdigit():
            return int(content_len), False
    return None, False


def _fetch_byte_range(
    url: str,
    start: int,
    end: int,
    headers: Dict[str, str],
    timeout: int,
    retries: int,
) -> Tuple[int, bytes]:
    """Fetch a single [start, end] inclusive byte slice with exponential backoff retries."""
    range_headers = dict(headers)
    range_headers["Range"] = f"bytes={start}-{end}"
    last_err: Optional[Exception] = None
    for attempt in range(1, retries + 2):
        try:
            req = urllib.request.Request(url, headers=range_headers)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                status = getattr(resp, "status", resp.getcode())
                data = resp.read()
                if status != 206:
                    raise RuntimeError(f"Expected HTTP 206 for Range, got {status}")
                return start, data
        except Exception as e:  # noqa: BLE001
            last_err = e
            if attempt <= retries:
                time.sleep(0.4 * (2 ** (attempt - 1)))
    raise RuntimeError(f"Range {start}-{end} failed: {last_err}")


def download_one(
    url: str,
    dest: Union[str, Path],
    timeout: int = 25,
    retries: int = 3,
    verify_pdf: bool = False,
    chunks_per_file: int = 8,
    min_chunk_size_bytes: int = 256 * 1024,
    headers: Optional[Dict[str, str]] = None,
) -> DownloadResult:
    """Download a single file with optional multi-connection HTTP Range chunking and retries."""
    dest_path = Path(dest)
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    req_headers = {"User-Agent": _DEFAULT_UA}
    if headers:
        req_headers.update(headers)

    t0 = time.monotonic()
    last_err = ""

    # Try multi-connection HTTP Range chunked download if enabled
    if chunks_per_file > 1:
        try:
            total_size, supports_range = _probe_range_support(url, req_headers, timeout)
            if (
                supports_range
                and total_size is not None
                and total_size >= min_chunk_size_bytes * 2
            ):
                num_chunks = min(
                    chunks_per_file, max(2, total_size // min_chunk_size_bytes)
                )
                step = total_size // num_chunks
                ranges: List[Tuple[int, int]] = []
                for i in range(num_chunks):
                    s = i * step
                    e = (total_size - 1) if (i == num_chunks - 1) else ((i + 1) * step - 1)
                    ranges.append((s, e))

                parts: Dict[int, bytes] = {}
                with ThreadPoolExecutor(max_workers=num_chunks) as chunk_pool:
                    futs = [
                        chunk_pool.submit(
                            _fetch_byte_range,
                            url,
                            s,
                            e,
                            req_headers,
                            timeout,
                            retries,
                        )
                        for s, e in ranges
                    ]
                    for f in as_completed(futs):
                        s, chunk_bytes = f.result()
                        parts[s] = chunk_bytes

                data = b"".join(parts[s] for s, _ in ranges)
                is_pdf = data[:4] == b"%PDF"
                if verify_pdf and not is_pdf:
                    raise ValueError("Range-assembled payload does not start with %PDF")
                dest_path.write_bytes(data)
                return DownloadResult(
                    url=url,
                    path=dest_path,
                    ok=True,
                    size_bytes=len(data),
                    is_valid_pdf=is_pdf,
                    attempts=1,
                    chunks_used=num_chunks,
                    elapsed_sec=round(time.monotonic() - t0, 3),
                )
        except Exception as e:  # noqa: BLE001
            # Fall back transparently to full-stream download below
            last_err = str(e)

    # Standard single-stream download with retries
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
                chunks_used=1,
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
        chunks_used=1,
        elapsed_sec=round(time.monotonic() - t0, 3),
        error=last_err,
    )


def download_batch_parallel(
    items: Iterable[Tuple[str, Union[str, Path]]],
    max_workers: int = 12,
    timeout: int = 20,
    retries: int = 3,
    verify_pdf: bool = False,
    headers: Optional[Dict[str, str]] = None,
) -> List[DownloadResult]:
    """Download multiple (url, destination_path) pairs concurrently using a thread pool."""
    item_list = list(items)
    if not item_list:
        return []

    results: List[Optional[DownloadResult]] = [None] * len(item_list)
    workers = max(1, min(max_workers, len(item_list)))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        future_to_idx = {
            pool.submit(
                download_one,
                url,
                dest,
                timeout=timeout,
                retries=retries,
                verify_pdf=verify_pdf,
                headers=headers,
            ): idx
            for idx, (url, dest) in enumerate(item_list)
        }
        for fut in as_completed(future_to_idx):
            idx = future_to_idx[fut]
            results[idx] = fut.result()

    return [r for r in results if r is not None]
