# Scrap Master — Capability Benchmark, Limitations, Scribd API Extraction & Parallel Speedup Architecture

Based on our live benchmark scraping **Tanzania Form Two National Assessment (FTNA — Subject Code `036`: Information and Computer Studies / Computer Science)** examination papers and marking schemes—and inspecting the architecture of **Scrap Master**—this document provides:

1. **Where Scrap Master Succeeds (Core Abilities)**
2. **Where Scrap Master Fails (Limitations & Blind Spots)**
3. **Summary Verdict Matrix**
4. **How Scribd API / Embed Extraction Works (Bypassing the Web UI & Paywall Blur)**
5. **How to Make Scrap Master Significantly Faster (Parallel Execution & Async Batch Downloading)**

---

## 1. Where It Succeeds (Its Core Abilities)

1. **Instant HTML-to-Markdown Conversion (`web` channel via Jina Reader)**
   - **What we saw:** With zero configuration, `curl -s https://r.jina.ai/https://maktaba.tetea.org/resources/form-1-2/` stripped away all complex HTML/CSS clutter and returned a clean Markdown table with `[2025](url.pdf)[(Solutions)](url-solutions.pdf)`.
   - **Why it's powerful:** You don't need to write brittle BeautifulSoup/XPath/CSS selectors for every new website. Any static or server-rendered web page is immediately readable by an LLM or a 3-line regex script.

2. **Multi-Platform Routing & Fallback Architecture (16+ Platforms)**
   - Instead of being a single scraper, it is a **capability router** (`scrap_master/channels/`) that knows the best upstream tool for supported platforms (Web, YouTube, GitHub, Twitter/X, Reddit, Facebook, Instagram, LinkedIn, Bilibili, XiaoHongShu, RSS, Exa Search, Scribd, etc.) and falls back when one breaks.
   - **`scrap-master doctor` Health Checks:** It probes your machine and tells an agent in JSON (`--json`) which backends are actually working right now and how to fix missing ones.

3. **Agent + Tool Synergy (PDF OCR & Inspection)**
   - When combined with an AI agent environment, once the PDFs are downloaded, we can directly render, OCR, and cross-verify scanned image PDFs (like `ICS-F2-2025.pdf`) against digital text PDFs (like `ICS-F2-2025-Solutions.pdf`).

---

## 2. Where It Fails (Limitations & Blind Spots)

### A. It Was Not Originally a File Downloader or Bulk Crawler
- **What happened in our test:** Scrap Master's `web` channel (`r.jina.ai`) could read the Maktaba index page and give us the 65 `.pdf` URLs, **but Scrap Master previously had no built-in parallel PDF/file downloader or retry queue**.
- Sequential `urllib.request` downloads took ~17 minutes for 27 files because of slow single-threaded TCP/SSL handshakes (`_ssl.c:983: The handshake operation timed out` on `ICS-F2-2025.pdf`).
- **Fix Implemented:** We added parallel `ThreadPoolExecutor` execution to `doctor.py` and a high-speed concurrent downloader (`scrap_master/utils/parallel_downloader.py`) with automatic exponential backoff retries and connection pooling.

### B. Paywalled / Login-Wall Document Hosts (Scribd, Academia, Google Drive Embeds)
- **What happened in our test:** Many Tanzanian regional/mock marking schemes are hosted on **Scribd** (`scribd.com`) or embedded in **Google Drive viewers** on blogs like *Msomi Bora* or *Learning Hub TZ*.
- Standard Jina Reader (`r.jina.ai/https://www.scribd.com/document/...`) hits Scribd's React paywall, blur overlay, and ad trackers, returning only truncated preview text or a login prompt.
- **Fix Implemented:** See **Section 4** below and `scrap_master/channels/scribd.py` for direct Scribd API / Embed (`content/embed` + `.jsonp` page asset manifest + mobile API token) extraction.

### C. No Built-In PDF/Binary OCR Inside `scrap-master`
- Scrap Master has `transcribe.py` for audio/video (via Whisper), but scanned camera/scanner image PDFs (like `ICS-F2-2025.pdf`) contain only image streams plus a watermark footer (`Find this and other free resources at: https://maktaba.tetea.org`).
- Without a vision model or OCR pipeline (`pypdf`/`pdfplumber` + `tesseract` or multimodal LLM vision), a plain-text scraper gets blank pages on scanned exams.
