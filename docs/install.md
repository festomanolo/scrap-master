# Agent Reach — Installation Guide

## For Humans

Copy this to your AI Agent:

```
Install Agent Reach: https://raw.githubusercontent.com/Panniantong/agent-reach/main/docs/install.md
```

> 🛡️ **Safe by default:** `agent-reach install` only checks the machine and lists missing dependencies:
> ```
> Safely check and install Agent Reach: https://raw.githubusercontent.com/Panniantong/agent-reach/main/docs/install.md
> ```
> Only use `--system` after the user explicitly approves system-level installs and configuration writes.

---

## For AI Agents

### Goal

Install Agent Reach and all upstream tools so your user's agent has full internet access. After installation, you'll use the upstream tools directly (OpenCLI, twitter-cli, bili-cli, rdt-cli, yt-dlp, mcporter, gh CLI, etc.) — Agent Reach is the selector, installer, health checker and router, never a wrapper.

### ⚠️ Boundaries

When fixing issues, stay within these limits:

- **DO NOT** run commands with `sudo` unless the user explicitly approved
- **DO NOT** modify system files outside `~/.agent-reach/`
- **DO NOT** install packages not listed in this guide
- **DO NOT** disable firewalls, security settings, or system protections
- **DO NOT** clone repos, create files, or run commands inside the agent workspace / working directory
- If something requires elevated permissions, **tell the user** what's needed and let them decide

### 📁 Directory Rules

All Agent Reach files go in dedicated directories — **never in the agent workspace**:

| Purpose | Directory | Example |
|---------|-----------|---------|
| Config & tokens | `~/.agent-reach/` | `~/.agent-reach/config.json` |
| Upstream tool repos | `~/.agent-reach/tools/` | `~/.agent-reach/tools/xiaoyuzhou/` |
| Temporary files | `/tmp/` | `/tmp/yt-dlp-output/` |
| Skills | `~/.openclaw/skills/agent-reach/` | SKILL.md |

**Why?** If you clone repos or create files in the workspace, it pollutes the user's project directory and can break their agent over time. Keep the workspace clean.

### Step 1: Install the basics

```bash
# Recommended: pipx (simplest method)
pipx install https://github.com/Panniantong/agent-reach/archive/main.zip
agent-reach install --env=auto               # Read-only check (default)
# After the user explicitly approves system changes:
agent-reach install --env=auto --system

# If your Python comes from Homebrew / you hit PEP 668 (externally-managed-environment)
# install in a virtual environment:
python3 -m venv ~/.agent-reach-venv
source ~/.agent-reach-venv/bin/activate
pip install https://github.com/Panniantong/agent-reach/archive/main.zip
agent-reach install --env=auto               # Read-only check (default)
# After the user explicitly approves system changes:
agent-reach install --env=auto --system
```

> 💡 **Windows / Microsoft Store Python alias?**
> If `python3 --version` opens the Microsoft Store, or `where python3` points to
> `...\AppData\Local\Microsoft\WindowsApps\python3.exe`, then `python3` is a Windows Store alias,
> not a usable Python installation. Use the Python Launcher `py -3` instead, or the `python.exe`
> in your actual Python installation directory.
>
> PowerShell example:
> ```powershell
> py -3 -m venv $env:USERPROFILE\.agent-reach-venv
> $env:USERPROFILE\.agent-reach-venv\Scripts\Activate.ps1
> python -m pip install https://github.com/Panniantong/agent-reach/archive/main.zip
> agent-reach install --env=auto
> ```

The default command checks core infrastructure (gh CLI, Node.js, mcporter, Exa search, yt-dlp config) without changing the host. With explicit `--system` approval it installs/configures the missing pieces and activates these zero-config channels:

- Web (Jina Reader), YouTube, GitHub, RSS, Exa Search, V2EX, Bilibili (basic)

> 💡 **macOS / Homebrew Python showing `externally-managed-environment`?**
> This is PEP 668 protection — not an Agent Reach issue. Use `pipx install ...` first, or create a `venv` before installing.

**Install modes:**

```bash
agent-reach install --env=auto             # Check only; safe default
agent-reach install --env=auto --safe      # Same check-only behavior (compatibility)
agent-reach install --env=auto --system    # Explicitly allow external/system installs
agent-reach install --env=auto --dry-run   # Preview what --system would do
```

### Step 2: Ask the user which optional channels they want

After installing the basics, **ask the user** which additional channels they need. Present this list:

> The core channels are ready! You can now search the web, watch YouTube, read GitHub, and more.
>
> Here are the optional channels — which ones do you need?
>
> - 🌟 **OpenCLI** (recommended on desktop) — one install unlocks Reddit/Facebook/Instagram/Bilibili subtitles/Twitter fallback, and serves as the XiaoHongShu desktop backend; only uses your existing, explicitly controlled Chrome session for XiaoHongShu
> - 🐦 **Twitter/X** — search tweets, view timeline (requires login cookie)
> - 📈 **Xueqiu** — stock quotes, trending posts (requires login cookie)
> - 🎙️ **Xiaoyuzhou Podcast** — audio transcription (requires a free Groq key)
> - 📕 **XiaoHongShu** — search, read, comments (OpenCLI uses existing session; MCP/legacy tools use Cookie-Editor)
> - 📖 **Reddit** — search and read posts (login required: desktop OpenCLI or rdt-cli + cookie)
> - 📘 **Facebook** — search, pages, feed, group list (desktop OpenCLI, reuses Chrome session)
> - 📷 **Instagram** — user search, profiles, recent posts, explore (desktop OpenCLI, reuses Chrome session)
> - 📺 **Bilibili full** — trending, rankings, search, video detail (bili-cli, no login needed)
> - 💼 **LinkedIn** — profile, job search
> - 🎯 **Boss Zhipin** — job search + full JD text (local dedicated Chrome; user logs in manually)
>
> Tell me which ones you want, e.g. "help me install XiaoHongShu and Twitter", "help me install Facebook and Instagram", or "install everything".

Based on the user's choice, run:

```bash
agent-reach install --env=auto --system --channels=opencli,xiaohongshu   # Desktop user chose XHS
agent-reach install --env=auto --system --channels=facebook,instagram    # Desktop Meta channels
agent-reach install --env=local --system --channels=boss                # Desktop Boss Zhipin
agent-reach install --env=auto --system --channels=all                   # User approved everything
```

Supported channel names: `opencli`, `twitter`, `xiaoyuzhou`, `xueqiu`, `xiaohongshu`, `reddit`, `facebook`, `instagram`, `bilibili`, `linkedin`, `boss`, `all`

### Step 3: Fix what's broken

Run `agent-reach doctor` and check the output.

Try to get as many channels to ✅ as possible. If something failed during install or shows as ❌/⚠️ in doctor, diagnose the problem and try to fix it — but stay within the boundaries above. If a fix requires elevated permissions or system changes, ask the user first.

Only ask the user when you genuinely need their input (credentials, permissions, etc.).

### Step 3: Configure things that need user input

Some channels need credentials only the user can provide. Based on the doctor output, ask for what's missing:

> 🔒 **Security tip:** For platforms that need cookies or browser sessions (Twitter, XiaoHongShu, Reddit, Facebook, Instagram, Boss Zhipin), we recommend using a **dedicated/secondary account** rather than your main account. Cookie/browser-session auth carries two risks:
> 1. **Account ban** — platforms may detect non-browser API calls and restrict or ban the account
> 2. **Credential exposure** — cookies grant full account access; using a secondary account limits the blast radius if credentials are ever compromised

> 🍪 **Cookies / login sessions:**
>
> For platforms that need cookies via CLI (Twitter, Xueqiu, etc.), **prefer Cookie-Editor import** — it is the simplest and most reliable method:
> 1. The user logs in to the platform in their browser
> 2. Install the [Cookie-Editor](https://chromewebstore.google.com/detail/cookie-editor/hlkenndednhfkekhgcdicdfddnkalmdm) Chrome extension
> 3. Click the extension → Export → Header String
> 4. Paste the exported string to the Agent
>
> Twitter only accepts content explicitly exported by the user via Cookie-Editor. Agent Reach never logs the user in to XiaoHongShu and never reads XiaoHongShu browser cookies. XiaoHongShu OpenCLI only uses the user's existing, explicitly controlled Chrome session. If no existing session is present, use Cookie-Editor export to configure xiaohongshu-mcp / legacy tools instead. Xueqiu and Bilibili can be imported per-platform explicitly, e.g. `agent-reach configure --from-browser chrome --platform xueqiu`; the command does not scan or save cookies from other platforms.

**Twitter search & posting:**
> "To unlock Twitter search, I need your Twitter cookies. Install the Cookie-Editor Chrome extension, go to x.com/twitter.com, click the extension → Export → Header String, and paste it to me."

```bash
agent-reach configure twitter-cookies
```

This saves `twitter_auth_token` and `twitter_ct0` for `agent-reach doctor` to check whether credentials are present. `doctor` does not run the upstream `twitter status` in real time and does not modify the current shell. Before running `twitter search/read/...` directly, you must explicitly set the following in that process environment:

```bash
export TWITTER_AUTH_TOKEN="..."
export TWITTER_CT0="..."
twitter search "query" -n 10
```

> **Proxy note (networks requiring a proxy, e.g. mainland China):**
>
> twitter-cli and rdt-cli use Python and support proxies via environment variables.
>
> **What the Agent needs to do:**
> 1. Confirm the user has a proxy configured: `agent-reach configure proxy` (hidden input)
> 2. Set environment variables: `export HTTP_PROXY="..." HTTPS_PROXY="..."`
> 3. Agent Reach handles the rest automatically — no additional action needed from the user
>
> If the user reports "fetch failed", see [troubleshooting.md](troubleshooting.md)

**Reddit (login is mandatory — no zero-config path):**
> Reddit's anonymous endpoints are blocked; the official API requires manual approval. Desktop users should use OpenCLI first (just log in to reddit.com in Chrome); server/legacy users use rdt-cli:

```bash
# PyPI version lags upstream — install from GitHub (same pinned version as _RDT_GIT_SOURCE in code)
pipx install 'git+https://github.com/public-clis/rdt-cli.git@5e4fb3720d5c174e976cd425ccc3b879d52cac66'
rdt login   # automatically extracts browser cookies; on a server without a browser, set cookies manually per doctor hints
```

> Mainland China access to Reddit requires a proxy; if server IPs are blocked, use a residential proxy (e.g. https://webshare.io, ~$1/month):
> ```bash
> agent-reach configure proxy
> ```

**XiaoHongShu (multi-backend, choose by environment):**

> **Authentication boundary:** Agent Reach never logs the user in to XiaoHongShu and never reads
> browser cookies. OpenCLI only uses an existing Chrome session explicitly controlled by the user.
> `agent-reach configure xhs-cookies` does not inject cookies into OpenCLI or Chrome.
> If no existing session is present, do not automate login; use a Cookie-Editor manual export
> to configure xiaohongshu-mcp or a legacy tool instead:
>
> ```bash
> agent-reach configure xhs-cookies
> ```
>
> This explicit command saves/imports the user-provided xiaohongshu.com-domain cookie set.
> Confirm the cookie names and scope before running. Non-xiaohongshu.com domain cookies are ignored.
>
> **Desktop (recommended: OpenCLI):**

```bash
agent-reach install --system --channels opencli
```

> After installation, guide the user through the one manual step (Chrome security limitation — cannot be automated):
> 1. Open https://chromewebstore.google.com/detail/opencli/ildkmabpimmkaediidaifkhjpohdnifk
> 2. Click "Add to Chrome"
> 3. Run `opencli doctor` to verify (shows "Extension: connected" when successful)
>
> When AUTH_REQUIRED and the user has no existing session, do not auto-login; switch to the
> xiaohongshu-mcp / legacy tools Cookie-Editor route below.
>
> **Server / no-desktop environment (xiaohongshu-mcp):**
> 1. Download the platform binary from https://github.com/xpzouying/xiaohongshu-mcp/releases to `~/.agent-reach/tools/`
> 2. Start the service (first run auto-downloads ~150MB headless browser — wait for it to finish)
> 3. Import cookies manually using the Cookie-Editor flow above
> 4. Connect: `mcporter config add xiaohongshu http://localhost:18060/mcp --scope home`
> 5. Always include `--timeout 120000` when calling it
>
> **Legacy users (xhs-cli):** An already-installed xhs-cli continues to work as a fallback backend
> (upstream unmaintained since March 2026 — not recommended for new installs); authentication still
> uses the Cookie-Editor manual export flow above.

**Facebook / Instagram (desktop OpenCLI):**
> Both platforms use OpenCLI, which reuses the user's Chrome login session without storing credentials and without going through the Meta Graph API approval process. Server / no-desktop environments are not supported.

```bash
agent-reach install --system --channels facebook,instagram
```

> After installation:
> 1. Confirm the OpenCLI extension is installed in Chrome and passes `opencli doctor`
> 2. Log in to facebook.com / instagram.com in Chrome
> 3. The Agent calls directly:
>    ```bash
>    opencli facebook search "query" -f yaml
>    opencli facebook profile zuck -f yaml
>    opencli facebook groups -f yaml
>    opencli instagram search "query" -f yaml     # user search
>    opencli instagram profile nasa -f yaml
>    opencli instagram user nasa -f yaml          # recent posts for a specific user
>    ```
>
> Facebook Groups currently only guarantees reading the group list and recent activity visible to the current account — arbitrary group posts and comments are not guaranteed. Instagram `search` is a user search, not a global post keyword search; on 429/login errors, have the user re-login in Chrome and reduce call frequency.

**Xueqiu (stock quotes + trending posts):**
> "Xueqiu requires a login cookie. Please log in to xueqiu.com in Chrome first, then run:"

```bash
agent-reach configure --from-browser chrome --platform xueqiu
```

> Only reads and saves the minimum cookies Xueqiu requires; does not collect cookies from other platforms.

**Xiaoyuzhou Podcast (Groq Whisper):**
> "Xiaoyuzhou Podcast transcription is installed by default. You only need a free Groq API key."

The transcription script is automatically installed with Agent Reach; the user only needs to provide a key:

```bash
agent-reach configure groq-key
```

> **Get a Groq API key (free, no credit card, 30 seconds):**
> 1. Go to https://console.groq.com
> 2. Sign in with Google/GitHub (or register)
> 3. Left menu → API Keys → Create API Key
> 4. Copy the key (starts with `gsk_`) and paste it to the Agent
>
> **How to use:**
> The user sends a Xiaoyuzhou link to the Agent, which automatically calls:
> ```bash
> bash ~/.agent-reach/tools/xiaoyuzhou/transcribe.sh https://www.xiaoyuzhoufm.com/episode/xxxxx
> ```
>
> Auto-downloads audio → transcodes and splits → Groq Whisper transcription → full text transcript.
>
> **Free tier and limits:**
> - ~2 hours of audio per hour (7200 seconds); after that, auto-recovers after 15 minutes
> - More than enough for everyday podcast listening
> - High transcription quality (Whisper large-v3), but does not distinguish speakers
> - Podcasts over 2 hours: recommend processing in batches

**LinkedIn (optional — mcp-server-linkedin):**
> "Basic LinkedIn content can be read via Jina Reader. Full features (profile details, people and job search) require mcp-server-linkedin."

> **Setup (recommended: stdio):**
> First install `uv` (which also provides `uvx`) per the official instructions:
> https://docs.astral.sh/uv/getting-started/installation/
>
> ```bash
> mcporter config add linkedin --command uvx --arg mcp-server-linkedin@latest --env UV_HTTP_TIMEOUT=300 --scope home
> ```
>
> `uvx` fetches and starts the latest version on demand — no separate Python package install or persistent HTTP service needed.
>
> **First-time login (requires a browser):**
> ```bash
> uvx mcp-server-linkedin@latest --login
> ```
> A browser window opens; log in manually. The session is saved to `~/.linkedin-mcp/profile/`.
> On a server without a desktop, run the same login command in a VNC or similar visible desktop environment.
>
> See https://github.com/stickerdaniel/linkedin-mcp-server for details

**Boss Zhipin (desktop only — boss-agent-cli + CDP):**

When the user says "help me configure Boss Zhipin", the Agent handles the automatable parts and leaves only the website login to the user:

1. First explain that an upstream CLI will be installed and a dedicated Chrome profile directory created, and request approval for system-level installation.
2. After the user approves, run:
   ```bash
   agent-reach install --env=local --system --channels=boss
   ```
3. Launch the dedicated Chrome bound to loopback only per your OS:
   ```bash
   # macOS
   open -na "Google Chrome" --args --remote-debugging-address=127.0.0.1 \
     --remote-debugging-port=9222 --user-data-dir="$HOME/.boss-chrome-profile" \
     "https://www.zhipin.com/web/geek/job"

   # Linux
   google-chrome --remote-debugging-address=127.0.0.1 \
     --remote-debugging-port=9222 --user-data-dir="$HOME/.boss-chrome-profile" \
     "https://www.zhipin.com/web/geek/job"
   ```
   Windows PowerShell：
   ```powershell
   Start-Process chrome.exe -ArgumentList '--remote-debugging-address=127.0.0.1','--remote-debugging-port=9222',"--user-data-dir=$env:USERPROFILE\.boss-chrome-profile",'https://www.zhipin.com/web/geek/job'
   ```
4. Pause and have the **user visually confirm** they are logged in (avatar in the top right); if not logged in, have the **user manually
   log in**, scan QR, or handle any slider. The Agent must not request credentials, log in on
   the user's behalf, or use `boss status` as a substitute — it only validates local `session.enc`
   and does not represent the Chrome login state.
5. After the user confirms login is complete, run:
   ```bash
   boss --cdp-url http://localhost:9222 login --cdp
   agent-reach doctor    # check the boss line for the browser wt2 cookie probe result
   ```

> Security boundary: any local process that can reach debug port 9222 has full control over this Chrome.
> You must use `--remote-debugging-address=127.0.0.1` — never expose it to LAN or the internet.
> Use a dedicated profile and reuse it long-term; do not delete or recreate it for each run, and do
> not default to the user's daily Chrome. Close the dedicated Chrome when not in use. Boss Zhipin does
> not support server / no-desktop environments. Search commands must include
> `--browser-source existing-browser --cdp-url http://localhost:9222`。
>
> Dependency: boss-agent-cli PRs #403–#407 are all merged into upstream master. The installer pins to
> upstream commit
> `4c991b77086a203173bf08a4cb64a23af6514fe6` rather than a moving branch. That commit includes
> `browser_source="existing-browser"` (strict CDP), `JobItem.lid`, and `job_card_browser()`. Switch to
> a version constraint after an official upstream release.

### Step 4: Final check

Run `agent-reach doctor` one final time and report the results to your user.

### Step 5: Set up daily monitoring (OpenClaw only)

If you are running inside **OpenClaw**, ask your user:

> "Agent Reach is set up! Would you like me to create a daily automated check task? It will monitor these channels and check for new versions — only notifying you when something is wrong or an update is available."

If the user agrees, create a **cron job** (daily, `sessionTarget: "isolated"`, `delivery: "announce"`) with this task:

```
Run the agent-reach watch command.
If the output contains "all good", do not notify the user — finish silently.
If the output contains issues (❌ ⚠) or a new version (🆕), send the full report to the user with suggested fixes.
If a new version is available, ask the user whether to upgrade (paste this to the user's Agent for a full update: Update Agent Reach: https://raw.githubusercontent.com/Panniantong/agent-reach/main/docs/update.md).
```

If the user wants a different agent to handle it, let them choose.

---

## Quick Reference

| Command | What it does |
|---------|-------------|
| `agent-reach install --env=auto` | Read-only dependency and channel check (default) |
| `agent-reach install --env=auto --system` | Explicitly install/configure core external tools |
| `agent-reach install --env=auto --system --channels=twitter,xiaohongshu` | Install approved optional channels |
| `agent-reach install --env=local --system --channels=boss` | Install the desktop Boss Zhipin strict-CDP backend |
| `agent-reach install --env=auto --system --channels=all` | Install everything after explicit approval |
| `agent-reach install --env=auto --safe` | Compatibility alias for the safe default |
| `agent-reach install --env=auto --dry-run` | Preview what would be done |
| `agent-reach doctor` | Show channel status |
| `agent-reach watch` | Quick health + update check (for scheduled tasks) |
| `agent-reach check-update` | Check for new versions |
| `agent-reach configure twitter-cookies` | Save Twitter cookies via hidden input; direct calls still require explicit env vars |
| `agent-reach configure proxy` | Save proxy address via hidden input; not an automatic unlock switch |
| `agent-reach configure groq-key` | Configure the Xiaoyuzhou transcription key via hidden input |

After installation, use upstream tools directly. See SKILL.md for the full command reference:

| Platform | Upstream Tool | Example |
|----------|--------------|---------|
| Twitter/X | `twitter` (fallback: `opencli`) | Set `TWITTER_AUTH_TOKEN` / `TWITTER_CT0` then run `twitter search "query" -n 10` |
| YouTube | `yt-dlp` | `yt-dlp --dump-json URL` |
| Bilibili | `bili` (subtitles via `opencli`) | `bili search "query" --type video` / `opencli bilibili subtitle BVxxx` |
| Reddit | `opencli` (fallback: `rdt`) | `opencli reddit search "query" -f yaml` / `rdt read POST_ID` |
| Facebook | `opencli` | `opencli facebook search "query" -f yaml` |
| Instagram | `opencli` | `opencli instagram user nasa -f yaml` |
| GitHub | `gh` | `gh search repos "query"` |
| Web | `curl` + Jina | `curl -s "https://r.jina.ai/URL"` |
| Exa Search | `mcporter` | `mcporter call exa.web_search_exa query="..." numResults=5` |
| XiaoHongShu | `opencli` (server: `mcporter`) | `opencli xiaohongshu search "query" -f yaml` |
| Xiaoyuzhou Podcast | `transcribe.sh` | `bash ~/.agent-reach/tools/xiaoyuzhou/transcribe.sh <URL>` |
| LinkedIn | `mcporter` | `mcporter call linkedin.get_person_profile linkedin_username="..."` |
| Boss Zhipin | `boss` / Python public API | `agent-reach doctor` (browser wt2 probe; `boss status` only reflects local session.enc); see `references/career.md` for search and JD |
| RSS | `feedparser` | `python3 -c "import feedparser; ..."` |

> For multi-backend platforms, use the `active_backend` from `agent-reach doctor --json`.
