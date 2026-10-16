# MANOLO Scrap

**Tell it what you want. It finds, downloads, reads and files it.**

Type `scrap`, write *"today I want to scrape Form 2 computer studies exams with marking schemes"*, and MANOLO Scrap plans the job with AI, searches the web, crawls the result pages, downloads every PDF / Google Drive / Scribd document in parallel, extracts the text (OCR for scanned pages), and writes a report — all filed in one tidy project folder.

By **festomanolo** · MIT License

---

## Install

```bash
pip install nolo-scrap            # installs the nolo-scrap command
pip install "https://github.com/festomanolo/scrap-master/archive/main.zip[all]"
scrap            # opens the TUI
```

Development:

```bash
git clone https://github.com/festomanolo/scrap-master.git && cd scrap-master
pip install -e ".[all,dev]" && pytest
```

## The TUI (`scrap`)

| Screen | What it does |
|---|---|
| 🧠 **Ask AI** | Describe the data you want in plain words. The AI plans searches, then MANOLO Scrap collects everything and writes `report.md`. |
| 🛠 **Tools** | Harvest a site · Download URLs · Scribd → Markdown · Read PDF (OCR) · Read any page · Web search |
| 📄 **File viewer** | Browse the workspace tree, render Markdown, view/edit text files |
| ⚙ **Settings** | AI provider (Ollama / OpenRouter), models, API key, favourite sites, workspace folder |
| 🩺 **Health check** | Which channels are ready on this machine |

**Keys:** `ctrl+a` Ask AI · `ctrl+t` Tools · `ctrl+s` Settings · `n` new folder · `f` new file · `r` rename · `del` delete · `o` open in Finder · `ctrl+e` edit/save · `ctrl+r` refresh · `ctrl+q` quit

## Scrape only what you need

```bash
scrap-master ask "form 4 chemistry past papers, pdfs only"          # AI job, PDFs only
scrap-master ask "TCP/IP lecture decks" --only slides                # force a type
scrap-master harvest https://site/library --only docs,sheets --organize
scrap-master download URL… --only pdf --organize                     # skip everything else
scrap-master organize ~/Downloads                                    # sort a folder by type
scrap-master types                                                   # list presets
```

Presets: `pdf docs slides sheets ebooks images audio video archives code data`, groups
`office media documents all`, or any raw extension (`--only .djvu`). Scribd and Google
Drive are only crawled when a document type is selected.

## Benchmark

`scrap-master bench` serves a mixed batch from a local, bandwidth-capped server and races
MANOLO Scrap against a plain Python loop, `curl`, `curl -Z`, `wget` and `aria2c` (whichever
are installed). Plain tools get a hand-filtered list; Scrap gets the full mixed list and must
pick the right types itself. Score = 60% speed · 20% filtering · 10% folders · 10% integrity.

```
#  Tool                      Time  ×naive   Files  Filter  Folders  Score
1  MANOLO Scrap             0.23s   17.4×     8/8       ✔        ✔    100
2  curl -Z (parallel)       1.09s    3.6×     8/8       ✘        ✘     23
3  python loop (naive)      3.98s    1.0×     8/8       ✘        ✘     13
```

## Where results go

```
~/MANOLO-Scrap/
├── projects/
│   └── 2026-10-16_form-2-computer-exams/
│       ├── pdfs/        downloaded PDFs & files
│       ├── markdown/    text extracted from PDFs (incl. OCR)
│       ├── scribd/      Scribd documents as Markdown
│       ├── pages/       every crawled web page as Markdown
│       ├── data/        plan.json, search_results.json, harvest_manifest.json
│       └── report.md    AI summary of what was collected
├── inbox/               one-off downloads from Tools
└── logs/
```

Change the location in Settings.

## AI: Ollama or OpenRouter

- **Ollama (free, local):** install Ollama, `ollama pull llama3.1`, pick it in Settings.
- **OpenRouter (cloud):** paste your key in Settings, or `scrap-master configure openrouter-key`.

With no AI available it still works: it uses a keyword plan and lists what it found instead of writing an AI summary.

## Command line (`scrap-master`)

```bash
scrap-master harvest https://msomibora.com/ --depth 1 --extract -d out/   # crawl → download → extract
scrap-master download URL [URL…] --verify-pdf                             # parallel, Range-chunked
scrap-master scribd https://www.scribd.com/document/<id> -o doc.md
scrap-master read-pdf exam.pdf -o exam.md                                 # PyMuPDF + OCR
scrap-master doctor                                                       # channel health
```

## What it can read

Web pages (with anti-bot fallbacks: direct HTML → Chrome-fingerprint TLS → headless browser), PDFs (digital + scanned), Scribd, Google Drive / Docs, YouTube, GitHub, RSS, Twitter/X, Reddit, Facebook, Instagram, LinkedIn.

### Platform setup notes

- **Twitter/X:** cookies saved with `scrap-master configure twitter-cookies` are only used by `doctor`. Before calling `twitter` directly, set `TWITTER_AUTH_TOKEN` and `TWITTER_CT0` in that process's environment.
- **LinkedIn:** full profiles/jobs need the `mcp-server-linkedin` MCP server (see `scrap-master doctor`).

## License

MIT © festomanolo
