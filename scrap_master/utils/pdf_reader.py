# -*- coding: utf-8 -*-
"""Hybrid PDF text + parallel OCR extractor (`read-pdf`).

Automatically extracts digital text from PDF pages via PyMuPDF (`pymupdf` / `fitz`)
or `pypdf`. Whenever a page is a scanned camera/scanner image (like `ICS-F2-2025.pdf`
where digital text is empty or only contains a watermark footer), it renders the
page to PNG and runs OCR in parallel across all scanned pages using:
  1. macOS Native Apple Vision (`VNRecognizeTextRequest` compiled via `swiftc` and
     cached at `~/.scrap-master/bin/vision_ocr`) — zero third-party OCR install needed!
  2. `tesseract` CLI fallback (if installed on Linux/Windows/macOS).
"""

from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from typing import Dict, List, Optional, Tuple, Union

_SWIFT_VISION_SOURCE = """import Foundation
import Vision
import AppKit

let args = CommandLine.arguments
guard args.count > 1 else { exit(1) }
let url = URL(fileURLWithPath: args[1])
guard let img = NSImage(contentsOf: url),
      let cgImg = img.cgImage(forProposedRect: nil, context: nil, hints: nil) else {
    exit(2)
}
let req = VNRecognizeTextRequest()
req.recognitionLevel = .accurate
req.usesLanguageCorrection = true
let handler = VNImageRequestHandler(cgImage: cgImg, options: [:])
try handler.perform([req])
for obs in req.results ?? [] {
    if let top = obs.topCandidates(1).first {
        print(top.string)
    }
}
"""


def _get_macos_vision_ocr_binary() -> Optional[Path]:
    """Compile and cache the native macOS Apple Vision OCR binary on first use."""
    if sys.platform != "darwin" or not shutil.which("swiftc"):
        return None
    bin_dir = Path.home() / ".scrap-master" / "bin"
    bin_path = bin_dir / "vision_ocr"
    if bin_path.exists() and bin_path.stat().st_size > 0:
        return bin_path
    try:
        bin_dir.mkdir(parents=True, exist_ok=True)
        src_path = bin_dir / "vision_ocr.swift"
        src_path.write_text(_SWIFT_VISION_SOURCE, encoding="utf-8")
        subprocess.run(
            ["swiftc", "-O", str(src_path), "-o", str(bin_path)],
            check=True,
            capture_output=True,
            timeout=60,
        )
        return bin_path if bin_path.exists() else None
    except Exception:
        return None


def ocr_image_file(image_path: Union[str, Path], timeout: int = 30) -> str:
    """Run OCR on a single image file using macOS Vision or Tesseract fallback."""
    img_str = str(image_path)
    vision_bin = _get_macos_vision_ocr_binary()
    if vision_bin:
        r = subprocess.run(
            [str(vision_bin), img_str],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        if r.returncode == 0 and r.stdout.strip():
            return r.stdout.strip()

    tesseract_bin = shutil.which("tesseract")
    if tesseract_bin:
        r = subprocess.run(
            [tesseract_bin, img_str, "stdout"],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        if r.returncode == 0:
            return r.stdout.strip()

    return ""


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
