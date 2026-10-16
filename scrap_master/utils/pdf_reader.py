# -*- coding: utf-8 -*-
"""Hybrid PDF text + batch macOS Apple Vision / Tesseract OCR extractor (`read-pdf`).

Automatically extracts digital text from PDF pages via PyMuPDF (`pymupdf` / `fitz`).
Whenever a page is a scanned camera/scanner image (like `ICS-F2-2025.pdf` where
digital text is empty or only contains a watermark footer), it renders the scanned
pages to PNG and runs a single batch OCR invocation using:
  1. macOS Native Apple Vision (`VNRecognizeTextRequest` compiled via `swiftc` and
     cached at `~/.scrap-master/bin/vision_ocr_batch`) — processes all images in
     a single process to avoid macOS `mediaanalysisd` XPC deadlocks!
  2. `tesseract` CLI fallback (if installed on Linux/Windows/macOS).
"""

import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from typing import Dict, List, Optional, Sequence, Union

_SWIFT_VISION_BATCH_SOURCE = """import Foundation
import Vision
import AppKit

let args = Array(CommandLine.arguments.dropFirst())
var output: [String: String] = [:]

let req = VNRecognizeTextRequest()
req.recognitionLevel = .accurate
req.usesLanguageCorrection = true

for path in args {
    let url = URL(fileURLWithPath: path)
    guard let img = NSImage(contentsOf: url),
          let cgImg = img.cgImage(forProposedRect: nil, context: nil, hints: nil) else {
        output[path] = ""
        continue
    }
    let handler = VNImageRequestHandler(cgImage: cgImg, options: [:])
    do {
        try handler.perform([req])
        var lines: [String] = []
        for obs in req.results ?? [] {
            if let top = obs.topCandidates(1).first {
                lines.append(top.string)
            }
        }
        output[path] = lines.joined(separator: "\\n")
    } catch {
        output[path] = ""
    }
}

if let data = try? JSONSerialization.data(withJSONObject: output, options: []),
   let str = String(data: data, encoding: .utf8) {
    print(str)
}
"""


def _get_macos_vision_batch_binary() -> Optional[Path]:
    """Compile and cache the native macOS Apple Vision batch OCR binary."""
    if sys.platform != "darwin" or not shutil.which("swiftc"):
        return None
    bin_dir = Path.home() / ".scrap-master" / "bin"
    bin_path = bin_dir / "vision_ocr_batch"
    if bin_path.exists() and bin_path.stat().st_size > 0:
        return bin_path
    try:
        bin_dir.mkdir(parents=True, exist_ok=True)
        src_path = bin_dir / "vision_ocr_batch.swift"
        src_path.write_text(_SWIFT_VISION_BATCH_SOURCE, encoding="utf-8")
        subprocess.run(
            ["swiftc", "-O", str(src_path), "-o", str(bin_path)],
            check=True,
            capture_output=True,
            timeout=90,
        )
        return bin_path if bin_path.exists() else None
    except Exception:
        return None


def ocr_image_batch(image_paths: Sequence[Union[str, Path]], timeout: int = 120) -> Dict[str, str]:
    """Run OCR on a batch of image files and return {str(path): text}."""
    paths_str = [str(p) for p in image_paths]
    if not paths_str:
        return {}

    vision_bin = _get_macos_vision_batch_binary()
    if vision_bin:
        try:
            r = subprocess.run(
                [str(vision_bin), *paths_str],
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            if r.returncode == 0 and r.stdout.strip():
                return json.loads(r.stdout.strip())
        except Exception:
            pass

    tesseract_bin = shutil.which("tesseract")
    results: Dict[str, str] = {}
    if tesseract_bin:
        for p in paths_str:
            try:
                r = subprocess.run(
                    [tesseract_bin, p, "stdout"],
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
                results[p] = r.stdout.strip() if r.returncode == 0 else ""
            except Exception:
                results[p] = ""
    return results


def ocr_image_file(image_path: Union[str, Path], timeout: int = 45) -> str:
    """Run OCR on a single image file."""
    p_str = str(image_path)
    return ocr_image_batch([p_str], timeout=timeout).get(p_str, "")


def _is_watermark_only(text: str, min_meaningful_chars: int = 120) -> bool:
    """Return True if extracted digital text is empty or just a short footer/watermark."""
    cleaned_lines = [
        line.strip()
        for line in text.splitlines()
        if line.strip()
        and "find this and other free resources at" not in line.lower()
        and not line.strip().lower().startswith("page ")
    ]
    meaningful = " ".join(cleaned_lines)
    return len(meaningful) < min_meaningful_chars


def extract_pdf_text(
    pdf_path: Union[str, Path],
    ocr_fallback: bool = True,
    dpi: int = 150,
    max_workers: int = 8,
    max_pages: Optional[int] = None,
) -> Dict:
    """Extract text from a digital or scanned PDF in parallel, returning structured dict & Markdown."""
    path = Path(pdf_path)
    if not path.exists():
        raise FileNotFoundError(f"PDF file not found: {path}")

    import pymupdf  # PyMuPDF

    doc = pymupdf.open(str(path))
    total_pages = len(doc)
    limit = min(total_pages, max_pages) if max_pages else total_pages

    pages_digital: Dict[int, str] = {}
    scanned_pages: List[int] = []

    for i in range(limit):
        pnum = i + 1
        txt = doc[i].get_text("text").strip()
        if ocr_fallback and _is_watermark_only(txt):
            scanned_pages.append(pnum)
        else:
            pages_digital[pnum] = txt

    pages_ocr: Dict[int, str] = {}
    if scanned_pages and ocr_fallback:
        with tempfile.TemporaryDirectory(prefix="scrap_master_ocr_") as tmpdir:
            img_paths: Dict[int, Path] = {}
            for pnum in scanned_pages:
                pix = doc[pnum - 1].get_pixmap(dpi=dpi)
                img_file = Path(tmpdir) / f"page_{pnum}.png"
                pix.save(str(img_file))
                img_paths[pnum] = img_file

            workers = max(1, min(max_workers, len(scanned_pages)))
            with ThreadPoolExecutor(max_workers=workers) as pool:
                fut_to_pnum = {
                    pool.submit(ocr_image_file, img_paths[pnum]): pnum
                    for pnum in scanned_pages
                }
                for fut in as_completed(fut_to_pnum):
                    pnum = fut_to_pnum[fut]
                    pages_ocr[pnum] = fut.result()

    doc.close()

    all_pages: Dict[int, str] = {}
    md_lines = [
        f"# {path.name}",
        f"**Total Pages:** {total_pages} | **Digital Pages:** {len(pages_digital)} | **OCR Scanned Pages:** {len(pages_ocr)}\n",
    ]
    for pnum in range(1, limit + 1):
        mode = "OCR" if pnum in pages_ocr else "Digital"
        content = pages_ocr.get(pnum) or pages_digital.get(pnum, "")
        all_pages[pnum] = content
        md_lines.append(f"\n---\n## Page {pnum} ({mode})\n")
        md_lines.append(content)

    return {
        "file": str(path),
        "total_pages": total_pages,
        "digital_pages": len(pages_digital),
        "ocr_pages": len(pages_ocr),
        "pages": all_pages,
        "markdown": "\n".join(md_lines),
    }
