# -*- coding: utf-8 -*-
"""MANOLO Scrap workspace — one predictable folder layout for every scraping job.

~/MANOLO-Scrap/
├── projects/<YYYY-MM-DD>_<slug>/
│   ├── pdfs/        downloaded PDFs and other binaries
│   ├── markdown/    text extracted from PDFs (PyMuPDF + OCR)
│   ├── scribd/      Scribd documents as Markdown
│   ├── pages/       scraped web pages as Markdown
│   ├── data/        manifests, search results, plans (JSON)
│   └── report.md    AI summary of what was collected
├── inbox/           quick one-off downloads
└── logs/            run logs
"""

import datetime as _dt
import re
from pathlib import Path

PROJECT_DIRS = ("pdfs", "markdown", "scribd", "pages", "data")


def workspace_root() -> Path:
    from scrap_master.config import Config

    root = Config().get("workspace") or str(Path.home() / "MANOLO-Scrap")
    path = Path(root).expanduser()
    for sub in ("projects", "inbox", "logs"):
        (path / sub).mkdir(parents=True, exist_ok=True)
    return path


def slugify(text: str, max_len: int = 48) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug[:max_len].rstrip("-") or "job"


def new_project(name: str) -> Path:
    """Create a dated project folder with the standard sub-folders and return it."""
    base = workspace_root() / "projects" / f"{_dt.date.today():%Y-%m-%d}_{slugify(name)}"
    path, n = base, 2
    while path.exists():
        path, n = base.with_name(f"{base.name}-{n}"), n + 1
    for sub in PROJECT_DIRS:
        (path / sub).mkdir(parents=True)
    return path


def file_kind_dir(project: Path, filename: str) -> Path:
    """Where a file of this type belongs inside a project."""
    ext = Path(filename).suffix.lower()
    if ext == ".md":
        return project / "markdown"
    if ext in (".json", ".csv", ".txt"):
        return project / "data"
    return project / "pdfs"


def organize(project: Path) -> int:
    """Move stray files in a project root into the right sub-folder. Returns files moved."""
    moved = 0
    for f in project.iterdir():
        if f.is_file() and f.name != "report.md":
            dest = file_kind_dir(project, f.name)
            dest.mkdir(exist_ok=True)
            f.rename(dest / f.name)
            moved += 1
    return moved
