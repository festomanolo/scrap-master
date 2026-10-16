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
