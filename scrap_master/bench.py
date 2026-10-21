"""Offline benchmark: Scrap Master vs. common download tools on the same simulated network.

A local HTTP server serves a mixed batch of files (PDFs, slides, sheets, images, …) with
per-connection bandwidth caps and latency, like a real slow host. Every contender downloads
the batch; we time it, verify checksums, and check whether files end up organized by type.

Scrap Score (0-100) = 60% speed vs. the fastest contender (same bytes for everyone)
                    + 20% filtering (picked the requested types out of a mixed list by itself)
                    + 10% organization (files filed into type folders)
                    + 10% integrity (byte-exact downloads)
"""

import hashlib
import os
import shutil
import subprocess
import tempfile
import threading
import time
import urllib.request
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Callable, Dict, List, Optional

_MIX = (".pdf", ".pdf", ".pdf", ".docx", ".pptx", ".xlsx", ".epub", ".jpg", ".zip", ".mp3")


@dataclass
class BenchResult:
    tool: str
    seconds: float = 0.0
    ok_files: int = 0
    total_files: int = 0
    filtered: bool = False
    organized: bool = False
    note: str = ""
    score: int = 0
    extra: Dict[str, float] = field(default_factory=dict)

    @property
    def mbps(self) -> float:
        return self.extra.get("mb", 0) / self.seconds if self.seconds else 0.0


def _make_handler(root: Path, bytes_per_sec: int, latency: float):
    chunk = 16 * 1024

    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, *a):  # silence
            pass

        def do_HEAD(self):
            self._serve(head=True)

        def do_GET(self):
            self._serve(head=False)

        def _serve(self, head: bool):
            f = root / self.path.lstrip("/").split("?")[0]
            if not f.is_file():
                self.send_error(404)
                return
            data = f.read_bytes()
            start, end = 0, len(data) - 1
            rng = self.headers.get("Range", "")
            if rng.startswith("bytes="):
                a, _, b = rng[6:].partition("-")
                start = int(a or 0)
                end = min(int(b), end) if b else end
                self.send_response(206)
                self.send_header("Content-Range", f"bytes {start}-{end}/{len(data)}")
            else:
                self.send_response(200)
            self.send_header("Accept-Ranges", "bytes")
            self.send_header("Content-Length", str(end - start + 1))
            self.send_header("Content-Type", "application/octet-stream")
            self.end_headers()
            if head:
                return
            time.sleep(latency)
            body = memoryview(data)[start:end + 1]
            for i in range(0, len(body), chunk):
                self.wfile.write(body[i:i + chunk])
                time.sleep(chunk / bytes_per_sec)

    return Handler


def _fixture(root: Path, files: int, size_kb: int) -> Dict[str, str]:
    """Write ``files`` pseudo-random files; return name -> sha256."""
    sums = {}
    for i in range(files):
        ext = _MIX[i % len(_MIX)]
        name = f"file_{i:03d}{ext}"
        blob = (b"%PDF-1.4\n" if ext == ".pdf" else b"") + os.urandom(size_kb * 1024)
        (root / name).write_bytes(blob)
        sums[name] = hashlib.sha256(blob).hexdigest()
    return sums


# ── contenders ───────────────────────────────────────────────

def _naive(urls: List[str], out: Path) -> None:
    """A plain one-at-a-time script (what most tutorials / browser 'save all' do)."""
    for u in urls:
        with urllib.request.urlopen(u, timeout=60) as r:
            (out / u.rsplit("/", 1)[-1]).write_bytes(r.read())


def _curl(urls: List[str], out: Path) -> None:
    args = ["curl", "-s", "--fail"]
    for u in urls:
        args += ["-o", str(out / u.rsplit("/", 1)[-1]), u]
    subprocess.run(args, check=True, timeout=600)


def _curl_parallel(urls: List[str], out: Path) -> None:
    args = ["curl", "-s", "--fail", "-Z", "--parallel-max", "12"]
    for u in urls:
        args += ["-o", str(out / u.rsplit("/", 1)[-1]), u]
    subprocess.run(args, check=True, timeout=600)


def _wget(urls: List[str], out: Path) -> None:
    subprocess.run(["wget", "-q", "-P", str(out), *urls], check=True, timeout=600)


def _aria2(urls: List[str], out: Path) -> None:
    lst = out / ".aria2.txt"
    lst.write_text("\n".join(urls))
    subprocess.run(["aria2c", "-q", "-x8", "-s8", "-j12", "-d", str(out), "-i", str(lst)],
                   check=True, timeout=600)
    lst.unlink()


def _scrap(urls: List[str], out: Path, exts) -> None:
    from scrap_master.utils.filetypes import category_of
    from scrap_master.utils.harvest import classify_link
    from scrap_master.utils.parallel_downloader import download_batch_parallel

    keep = [u for u in urls if classify_link(u, exts, sources=())]
    pairs = [(u, out / category_of(u) / u.rsplit("/", 1)[-1]) for u in keep]
    res = download_batch_parallel(pairs, max_workers=12, chunks_per_file=8,
                                  min_chunk_size_bytes=64 * 1024)
    bad = [r for r in res if not r.ok]
    if bad:
        raise RuntimeError(bad[0].error)


def _contenders() -> List[tuple]:
    out = [("python loop (naive)", _naive, None)]
    if shutil.which("curl"):
        out.append(("curl (sequential)", _curl, None))
        if b"parallel" in subprocess.run(["curl", "--help", "all"], capture_output=True).stdout:
            out.append(("curl -Z (parallel)", _curl_parallel, None))
    if shutil.which("wget"):
        out.append(("wget", _wget, None))
    if shutil.which("aria2c"):
        out.append(("aria2c -x8 -j12", _aria2, None))
    return out


def run(
    files: int = 20,
    size_kb: int = 768,
    kbps: int = 2048,
    latency_ms: int = 60,
    only=("pdf",),
    log: Callable[[str], None] = print,
    tools: Optional[List[str]] = None,
) -> List[BenchResult]:
    """Run the benchmark and return results sorted best-first (by score)."""
    from scrap_master.utils.filetypes import category_of, resolve

    exts = resolve(only)
    tmp = Path(tempfile.mkdtemp(prefix="scrap-bench-"))
    src = tmp / "srv"
    src.mkdir()
    sums = _fixture(src, files, size_kb)
    wanted = {n for n in sums if Path(n).suffix in exts}
    server = ThreadingHTTPServer(("127.0.0.1", 0), _make_handler(src, kbps * 1024, latency_ms / 1000))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{server.server_address[1]}/"
    urls = [base + n for n in sorted(sums)]
    log(f"Batch: {files} mixed files × {size_kb} KB · link {kbps} KB/s per connection · "
        f"{latency_ms} ms latency · want: {' '.join(exts)} ({len(wanted)} files)")

    # Fair work: every tool moves the same bytes. Plain tools get a hand-filtered URL list;
    # Scrap Master gets the full mixed list and must pick the right types itself.
    picked = [u for u in urls if u.rsplit("/", 1)[-1] in wanted]
    contenders = _contenders() + [("Scrap Master", lambda u, o: _scrap(u, o, exts), True)]
    if tools:
        contenders = [c for c in contenders if any(t.lower() in c[0].lower() for t in tools)]
    results: List[BenchResult] = []
    try:
        for name, fn, self_filters in contenders:
            out = tmp / f"out_{len(results)}"
            out.mkdir()
            r = BenchResult(tool=name, total_files=len(wanted))
            t0 = time.perf_counter()
            try:
                fn(urls if self_filters else picked, out)
            except Exception as e:  # keep benchmarking the rest
                r.note = f"{type(e).__name__}: {str(e)[:60]}"
            r.seconds = time.perf_counter() - t0
            got = [p for p in out.rglob("*") if p.is_file() and not p.name.startswith(".")]
            r.ok_files = sum(1 for p in got if p.name in wanted
                             and hashlib.sha256(p.read_bytes()).hexdigest() == sums[p.name])
            r.filtered = bool(self_filters) and bool(got) and {p.name for p in got} <= wanted
            r.organized = bool(got) and all(p.parent.name == category_of(p.name) for p in got)
            r.extra["mb"] = sum(p.stat().st_size for p in got) / 1e6
            results.append(r)
            log(f"  {name:<22} {r.seconds:6.2f}s  {r.ok_files}/{r.total_files} ok"
                + (f"  ({r.note})" if r.note else ""))
    finally:
        server.shutdown()
        shutil.rmtree(tmp, ignore_errors=True)

    fastest = min((r.seconds for r in results if r.ok_files), default=1.0)
    for r in results:
        speed = fastest / r.seconds if r.ok_files and r.seconds else 0
        integrity = r.ok_files / r.total_files if r.total_files else 0
        r.score = round(60 * speed + 20 * r.filtered + 10 * r.organized + 10 * integrity)
        r.extra["speedup_vs_naive"] = results[0].seconds / r.seconds if r.seconds else 0
    return sorted(results, key=lambda r: -r.score)


def render(results: List[BenchResult]) -> str:
    lines = [
        f"{'#':<3}{'Tool':<22}{'Time':>8}{'×naive':>8}{'Files':>8}{'Filter':>8}{'Folders':>9}{'Score':>7}",
        "─" * 73,
    ]
    for i, r in enumerate(results, 1):
        lines.append(
            f"{i:<3}{r.tool:<22}{r.seconds:>7.2f}s{r.extra.get('speedup_vs_naive', 0):>7.1f}×"
            f"{f'{r.ok_files}/{r.total_files}':>8}{'✔' if r.filtered else '✘':>8}"
            f"{'✔' if r.organized else '✘':>9}{r.score:>7}"
        )
    return "\n".join(lines)
