"""File-type presets: pick *what* to scrape (``--only pdf,docs``) and file it by kind.

A selection is a list of preset names, aliases or raw extensions, e.g.
``["pdf", "slides", ".epub"]``. ``resolve()`` turns it into a tuple of extensions.
"""

import re
import shutil
from pathlib import Path
from typing import Dict, Iterable, Optional, Tuple

PRESETS: Dict[str, Tuple[str, ...]] = {
    "pdf": (".pdf",),
    "docs": (".doc", ".docx", ".odt", ".rtf", ".txt", ".md", ".pages", ".tex"),
    "slides": (".ppt", ".pptx", ".odp", ".key"),
    "sheets": (".xls", ".xlsx", ".ods", ".csv", ".tsv"),
    "ebooks": (".epub", ".mobi", ".azw3", ".djvu", ".fb2"),
    "images": (".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg", ".tif", ".tiff", ".bmp"),
    "audio": (".mp3", ".wav", ".m4a", ".flac", ".ogg", ".aac"),
    "video": (".mp4", ".mkv", ".webm", ".mov", ".avi", ".m4v"),
    "archives": (".zip", ".rar", ".7z", ".tar", ".gz", ".tgz", ".bz2", ".xz"),
    "code": (".py", ".ipynb", ".js", ".ts", ".java", ".c", ".cpp", ".h", ".go", ".rs", ".rb", ".php"),
    "data": (".json", ".xml", ".sql", ".parquet", ".sqlite", ".db", ".yaml", ".yml"),
}
GROUPS: Dict[str, Tuple[str, ...]] = {
    "office": ("docs", "slides", "sheets"),
    "documents": ("pdf", "docs", "slides", "sheets", "ebooks"),
    "media": ("images", "audio", "video"),
    "all": tuple(PRESETS),
}
ALIASES = {
    "pdfs": "pdf", "doc": "docs", "word": "docs", "text": "docs",
    "ppt": "slides", "pptx": "slides", "powerpoint": "slides", "presentations": "slides",
    "excel": "sheets", "spreadsheets": "sheets", "spreadsheet": "sheets", "xls": "sheets",
    "books": "ebooks", "ebook": "ebooks", "epub": "ebooks",
    "image": "images", "photos": "images", "pictures": "images", "img": "images",
    "music": "audio", "mp3": "audio", "videos": "video", "mp4": "video",
    "zip": "archives", "zips": "archives", "archive": "archives",
    "datasets": "data", "dataset": "data", "json": "data",
    "everything": "all", "any": "all",
}
# Scribd and Google Drive yield documents, so they only belong to document selections.
_DOC_KINDS = {"pdf", "docs", "slides", "sheets", "ebooks"}


def _names(token: str) -> Tuple[str, ...]:
    t = ALIASES.get(token, token)
    if t in GROUPS:
        return GROUPS[t]
    return (t,) if t in PRESETS else ()


def resolve(selection: Optional[Iterable[str]], default=("pdf",)) -> Tuple[str, ...]:
    """Turn presets / aliases / extensions (comma lists allowed) into a tuple of extensions."""
    tokens = [t.strip().lower() for s in (selection or default) for t in str(s).split(",") if t.strip()]
    exts: Dict[str, None] = {}
    for t in tokens:
        names = _names(t.lstrip("."))
        if names:
            for n in names:
                exts.update(dict.fromkeys(PRESETS[n]))
        else:
            exts[t if t.startswith(".") else f".{t}"] = None
    return tuple(exts)


def sources_for(exts: Iterable[str]) -> Tuple[str, ...]:
    """Document sources (Scribd, Google Drive) worth crawling for these extensions."""
    wanted = {category_of(e) for e in exts}
    return ("scribd", "gdrive") if wanted & _DOC_KINDS else ()


def category_of(name: str) -> str:
    """Folder a file belongs in, by extension (``other`` if unknown)."""
    ext = name if name.startswith(".") and name.count(".") == 1 else Path(name).suffix
    ext = ext.lower()
    for cat, exts in PRESETS.items():
        if ext in exts:
            return cat
    return "other"


_ONLY_RX = re.compile(
    r"\b(?:only|just)\s+([a-z0-9 ,/&]+?)(?:\s+files?)?\b(?=[.;!?]|$|\s+(?:from|about|on|for|of|and\s+not))"
    r"|\b([a-z0-9]+)\s+only\b",
    re.I,
)


def types_from_text(request: str) -> Optional[Tuple[str, ...]]:
    """Extensions named in a request like "pdfs only" / "only slides and sheets", else None."""
    for m in _ONLY_RX.finditer(request):
        words = re.split(r"[\s,/&]+|\band\b", (m.group(1) or m.group(2)).lower())
        names = [w for w in words if w and _names(w.lstrip("."))]
        if names:
            return resolve(names)
    return None


def organize(folder, recursive: bool = False) -> Dict[str, int]:
    """Move loose files in ``folder`` into ``<category>/`` subfolders. Returns counts per category."""
    root = Path(folder)
    counts: Dict[str, int] = {}
    files = root.rglob("*") if recursive else root.iterdir()
    for f in [p for p in files if p.is_file() and not p.name.startswith(".")]:
        cat = category_of(f.name)
        if f.parent.name == cat or f.name.endswith("_manifest.json"):
            continue
        dest = root / cat / f.name
        dest.parent.mkdir(parents=True, exist_ok=True)
        n = 1
        while dest.exists():
            dest = dest.with_name(f"{f.stem}_{n}{f.suffix}")
            n += 1
        shutil.move(str(f), dest)
        counts[cat] = counts.get(cat, 0) + 1
    return counts
