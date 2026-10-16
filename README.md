# MANOLO Scrap

**Tell it what you want. It finds, downloads, reads and files it.**

Type `scrap`, write *"today I want to scrape Form 2 computer studies exams with marking schemes"*, and MANOLO Scrap plans the job with AI, searches the web, crawls the result pages, downloads every PDF / Google Drive / Scribd document in parallel, extracts the text (OCR for scanned pages), and writes a report — all filed in one tidy project folder.

By **festomanolo** · MIT License

---

## Install

```bash
pip install "https://github.com/festomanolo/scrap-master/archive/main.zip[all]"
scrap            # opens the TUI
```

Development:

```bash
git clone https://github.com/festomanolo/scrap-master.git
cd scrap-master
pip install -e ".[dev]"
pytest
```

---

## How to use it

### 1. Check the status of every platform

```bash
scrap-master doctor           # human-readable report
scrap-master doctor --json    # machine-readable, includes the active backend per platform
```

### 2. Install optional channels

`install` is read-only by default. It checks your machine and changes nothing until you pass `--system`.

```bash
scrap-master install --env=auto --dry-run            # preview only
scrap-master install --env=auto --system             # install core dependencies
scrap-master install --system --channels=twitter,reddit,bilibili
scrap-master install --system --channels=all         # everything
```

Use `--env=server` on a headless machine (desktop-only channels are skipped) and `--env=local` on a desktop.

### 3. Scrape: call the active backend directly

Once `doctor` shows a platform as ready, use its tool. The common ones:

```bash
# Any web page as clean Markdown
curl -s https://r.jina.ai/https://example.com/article

# YouTube: metadata, subtitles, search
yt-dlp --dump-json "https://www.youtube.com/watch?v=VIDEO_ID"
yt-dlp --write-auto-subs --skip-download "https://www.youtube.com/watch?v=VIDEO_ID"
yt-dlp --dump-json "ytsearch5:python web scraping"

# GitHub
gh repo view owner/repo
gh search repos "LLM framework" --limit 10
gh search code "def main" --language python

# Twitter/X (after configuring cookies)
twitter search "web scraping" -n 20

# RSS / Atom
python -c "import feedparser; [print(e.title, e.link) for e in feedparser.parse('https://hnrss.org/frontpage').entries]"

# V2EX public API
curl -s https://www.v2ex.com/api/topics/hot.json
```

The exact command for each platform, including fallbacks and retry chains, is documented in [`scrap_master/skill/references/`](scrap_master/skill/references). Run `scrap-master doctor --json` to see which backend is active.

### 4. Use it from Python

```python
from scrap_master import ScrapMaster

sm = ScrapMaster()
print(sm.doctor_report())      # same as `scrap-master doctor`
results = sm.doctor()          # dict: channel -> status, message, active backend
```

### 5. Use it from an AI agent

```bash
scrap-master skill --install   # registers SKILL.md for Claude Code, OpenClaw, OpenCode, etc.
```

Then ask your agent in plain language ("what are people saying about X on Reddit?", "summarize this YouTube video", "read this link"). The skill tells it which tool to call for each platform and what to do when one fails. An MCP server is also available (`pip install "scrap-master[all] @ https://github.com/festomanolo/scrap-master/archive/main.zip"`, see `scrap_master/integrations/mcp_server.py`).

### 6. Transcribe audio and video

```bash
scrap-master configure groq-key --stdin            # free key from console.groq.com
scrap-master transcribe "https://example.com/video" -o transcript.txt
scrap-master transcribe ./interview.mp3
```

---

## Unlock on demand

Everything below is optional. Skip what you do not need.

### Cookies (free, about 2 minutes)

For Twitter/X, Xueqiu and similar platforms, export cookies from your browser with the Cookie-Editor extension and save them. See [docs/cookie-export.md](docs/cookie-export.md).

```bash
scrap-master configure twitter-cookies --stdin      # paste the exported header string
scrap-master configure xhs-cookies --stdin
scrap-master configure --from-browser chrome --platform xueqiu   # explicit, single platform
```

Secrets are read from stdin or a hidden prompt, never from process arguments.

Saved Twitter cookies are used by `doctor` to check that credentials are present. Direct `twitter` commands still read `TWITTER_AUTH_TOKEN` and `TWITTER_CT0` from their own process environment, so export those before calling `twitter` yourself.

### Other keys and tokens

```bash
scrap-master configure github-token --stdin
scrap-master configure groq-key --stdin
scrap-master configure openai-key --stdin
scrap-master setup                                  # interactive wizard
```

### Proxy ($1/month, restricted networks only)

Most users need none. If your network blocks Reddit or Twitter, get a proxy and save it:

```bash
scrap-master configure proxy        # prompts with hidden input: http://user:pass@host:port
```

### Keep it healthy

```bash
scrap-master watch           # quick health check + update check, good for cron
scrap-master check-update
scrap-master uninstall --dry-run
```

---

## Status at a glance

```
$ scrap-master doctor

Scrap Master Status
========================================

✅ Ready to use:
  ✅ GitHub repositories and code
  ✅ YouTube videos and subtitles
  ✅ RSS/Atom feeds
  ✅ Any web page — Jina Reader

Optional channels:
  [!] Twitter/X — credentials saved; not verified live by design
  [X] Reddit — needs OpenCLI browser session or rdt-cli login
  ...
Status: 6/16 channels available
```

---

## Design Philosophy

**Scrap Master is a capability layer, not yet another scraper.**

It sits one level above any specific implementation and handles **selection, installation, health checks and routing**. Reading is done by upstream tools that your script or agent calls directly, so there is no wrapper layer to go stale.

Every platform is an ordered list of backends (primary plus fallbacks). Switching access paths means reordering a list, not rewriting code. Each channel file actually probes its candidates in order, not just checking that a command exists. The first fully working one becomes active, and broken ones come with a fix.

```
scrap_master/channels/
├── web.py          → Jina Reader
├── twitter.py      → twitter-cli ▸ OpenCLI ▸ bird
├── youtube.py      → yt-dlp
├── github.py       → gh CLI
├── bilibili.py     → bili-cli ▸ OpenCLI ▸ search API
├── reddit.py       → OpenCLI ▸ rdt-cli
├── facebook.py     → OpenCLI
├── instagram.py    → OpenCLI
├── xiaohongshu.py  → OpenCLI ▸ xiaohongshu-mcp ▸ xhs-cli
├── linkedin.py     → linkedin-mcp ▸ Jina Reader
├── rss.py          → feedparser
├── v2ex.py         → public JSON API
├── xueqiu.py       → public API + cookie
├── boss.py         → boss-agent-cli over CDP
├── xiaoyuzhou.py   → Groq Whisper
├── exa_search.py   → Exa via mcporter
└── __init__.py     → channel registry (used by doctor)
```

### Current tool choices

| Scenario | Primary | Fallback |
|----------|---------|----------|
| Read web pages | [Jina Reader](https://github.com/jina-ai/reader) | none |
| Tweets | [twitter-cli](https://github.com/public-clis/twitter-cli) | [OpenCLI](https://github.com/jackwener/opencli), bird |
| Reddit | [OpenCLI](https://github.com/jackwener/opencli) | [rdt-cli](https://github.com/public-clis/rdt-cli) |
| Facebook / Instagram | [OpenCLI](https://github.com/jackwener/opencli) | none |
| YouTube | [yt-dlp](https://github.com/yt-dlp/yt-dlp) | none |
| Bilibili | [bili-cli](https://github.com/public-clis/bilibili-cli) | OpenCLI, search API |
| Web search | [Exa](https://exa.ai) via [mcporter](https://github.com/nicobailon/mcporter) | none |
| GitHub | [gh CLI](https://cli.github.com) | none |
| RSS | [feedparser](https://github.com/kurtmckee/feedparser) | none |
| XiaoHongShu | [OpenCLI](https://github.com/jackwener/opencli) | [xiaohongshu-mcp](https://github.com/xpzouying/xiaohongshu-mcp), xhs-cli |
| LinkedIn | [mcp-server-linkedin](https://github.com/stickerdaniel/linkedin-mcp-server) | Jina Reader |

These are the current choices. When a path dies, the list is reordered; `scrap-master doctor` always tells you which backend is active.

---

## Credits

Scrap Master builds on the work of these open-source projects: [twitter-cli](https://github.com/public-clis/twitter-cli) · [rdt-cli](https://github.com/public-clis/rdt-cli) · [xhs-cli](https://github.com/jackwener/xiaohongshu-cli) · [bili-cli](https://github.com/public-clis/bilibili-cli) · [OpenCLI](https://github.com/jackwener/opencli) · [yt-dlp](https://github.com/yt-dlp/yt-dlp) · [Jina Reader](https://github.com/jina-ai/reader) · [Exa](https://exa.ai) · [mcporter](https://github.com/nicobailon/mcporter) · [feedparser](https://github.com/kurtmckee/feedparser) · [mcp-server-linkedin](https://github.com/stickerdaniel/linkedin-mcp-server)

## Contributing and issues

See [CONTRIBUTING.md](CONTRIBUTING.md). Report bugs and request features through [GitHub Issues](https://github.com/festomanolo/scrap-master/issues).

## License

[MIT](LICENSE)
