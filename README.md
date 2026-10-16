# MANOLO Scrap

**Tell it what you want. It finds, downloads, reads and files it.**

Type `scrap`, write *"today I want to scrape Form 2 computer studies exams with marking schemes"*, and MANOLO Scrap plans the job with AI, searches the web, crawls the result pages, downloads every PDF / Google Drive / Scribd document in parallel, extracts the text (OCR for scanned pages), and writes a report — all filed in one tidy project folder.

<p align="center">
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-blue.svg?style=for-the-badge" alt="MIT License"></a>
  <a href="https://www.python.org/"><img src="https://img.shields.io/badge/Python-3.10+-green.svg?style=for-the-badge&logo=python&logoColor=white" alt="Python 3.10+"></a>
</p>

<p align="center">
  <a href="#quick-start">Quick Start</a> · <a href="#supported-platforms">Platforms</a> · <a href="#how-to-use-it">How to use it</a> · <a href="#design-philosophy">Philosophy</a>
</p>

---

## Why Scrap Master?

The most valuable data lives on social and niche platforms: Twitter/X discussions, Reddit feedback, YouTube tutorials, GitHub activity, Bilibili videos, stock forums, job boards. Each one has its own barriers:

| Pain point | Reality |
|------------|---------|
| Twitter/X API | Pay-per-use, roughly $215/month at moderate volume |
| Reddit | Server IPs get 403'd, anonymous endpoints are blocked |
| XiaoHongShu | Login required to browse |
| Bilibili | Blocks overseas and server IPs, and blocks yt-dlp |
| Instagram / Facebook | No practical public API |

Connecting a script or an AI agent to all of them means finding tools, installing dependencies, and debugging configs, one platform at a time, and redoing it every time an access path dies.

**Scrap Master does that work once.** It maintains an ordered list of backends for every platform, probes them for real, tells you which one is active, and tells you exactly how to fix the ones that are broken.

### Strengths

| | |
|---|---|
| 🌍 **16 platforms, one tool** | Web pages, Twitter/X, Reddit, Facebook, Instagram, YouTube, Bilibili, GitHub, LinkedIn, XiaoHongShu, Xueqiu, V2EX, Boss Zhipin, Xiaoyuzhou podcasts, RSS and web search |
| 🔄 **Resilient by design** | Every platform has a primary backend plus fallbacks. When one dies, the next takes over (for example, Bilibili blocked yt-dlp, so Bilibili now routes to bili-cli, then OpenCLI, then a search API) |
| 🩺 **Honest health checks** | `scrap-master doctor` actually probes each backend and reports what works, what needs login, and the exact fix. It never claims a login-gated platform works unless it was verified |
| 📄 **Clean, LLM-ready output** | Any URL becomes clean Markdown through Jina Reader; subtitles, transcripts, JSON and RSS come back structured |
| 🔒 **Privacy-first** | Cookies and tokens stay on your machine in owner-only files and are never uploaded. Symlink-safe config handling, no silent browser-cookie harvesting |
| 💰 **Free** | All backends are open source and every API used has a free tier. The only possible cost is a $1/month proxy on restricted networks |
| 🤖 **Works with any agent** | Ships a `SKILL.md` and an MCP server for Claude Code, Cursor, Windsurf, OpenClaw and anything else that can run commands |
| 🎙️ **Audio and video to text** | Transcribe any audio/video URL or local file with Whisper (Groq or OpenAI) |

> **What Scrap Master is, and is not.** It is a *capability layer*: it selects, installs, health-checks and routes to best-in-class upstream tools (yt-dlp, gh, twitter-cli, OpenCLI, Jina Reader, feedparser, and others). The actual fetching is done by those tools, which you or your agent call directly. It is not a bulk crawler or a proxy-rotation framework, so it will not replace Scrapy for crawling millions of pages from one site. It is strongest when you need data from many different platforms without maintaining a scraper for each.

---

## Supported Platforms

| Platform | Capabilities | Setup | Notes |
|----------|-------------|:-----:|-------|
| 🌐 **Web** | Read | Zero config | Any URL to clean Markdown ([Jina Reader](https://github.com/jina-ai/reader)) |
| 🔍 **Web search** | Search | Free key | Semantic web search ([Exa](https://exa.ai) via [mcporter](https://github.com/nicobailon/mcporter)) |
| 📦 **GitHub** | Read · Search | Zero config | [gh CLI](https://cli.github.com). Public repos work immediately; `gh auth login` unlocks forks, issues and PRs |
| 📺 **YouTube** | Read · Search | Zero config | Subtitles and search across 1800+ video sites ([yt-dlp](https://github.com/yt-dlp/yt-dlp)) |
| 📺 **Bilibili** | Read · Search | Zero config | Search and video detail via [bili-cli](https://github.com/public-clis/bilibili-cli) (no login); subtitles via [OpenCLI](https://github.com/jackwener/opencli) |
| 📡 **RSS** | Read | Zero config | Any RSS/Atom feed ([feedparser](https://github.com/kurtmckee/feedparser)) |
| 💻 **V2EX** | Hot topics · Nodes · Topics and replies · Profiles | Zero config | Public JSON API, no auth |
| 🐦 **Twitter/X** | Read · Search | Cookie | Search, timelines, tweets and articles ([twitter-cli](https://github.com/public-clis/twitter-cli)) |
| 📖 **Reddit** | Search · Read | OpenCLI / cookie | No zero-config path (anonymous endpoints are blocked). Desktop: OpenCLI via your browser session, or [rdt-cli](https://github.com/public-clis/rdt-cli) |
| 📘 **Facebook** | Search · Profiles · Feed · Groups | OpenCLI | Desktop only; reuses your logged-in Chrome session |
| 📷 **Instagram** | User search · Profiles · Recent posts · Explore | OpenCLI | Desktop only; reuses your logged-in Chrome session |
| 💼 **LinkedIn** | Public pages (Jina) · Full profiles, companies, jobs (MCP) | MCP server | Tell your agent "help me set up LinkedIn" |
| 📕 **XiaoHongShu** | Read · Search · Comments | OpenCLI / MCP | OpenCLI uses only an existing user-controlled Chrome session; MCP and legacy tools use a manual Cookie-Editor export |
| 📈 **Xueqiu** | Stock quotes · Search · Hot posts · Hot stocks | Browser cookie | Tell your agent "help me set up Xueqiu" |
| 🎯 **Boss Zhipin** | Job search · Full job descriptions | Desktop Chrome | Tell your agent "help me configure Boss Zhipin"; the agent sets up a dedicated Chrome and you log in manually |
| 🎙️ **Xiaoyuzhou Podcast** | Transcription | Free API key | Podcast audio to full-text transcript via Groq Whisper |

> **Setup levels:** Zero config = install and go · Free key = sign up, no payment · Cookie = export from your browser · OpenCLI = desktop Chrome session · Proxy = $1/month, restricted networks only

---

## Quick Start

```bash
# 1. Install from GitHub
pipx install https://github.com/festomanolo/scrap-master/archive/main.zip
#    or: pip install https://github.com/festomanolo/scrap-master/archive/main.zip

# 2. See what works right now
scrap-master doctor
```

That is enough to read web pages, GitHub, YouTube, Bilibili, RSS and V2EX. Everything else is optional and unlocked on demand (see below).

For development:

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
