# Scrap Master — Installation Guide

## For Humans

Copy this to your AI Agent:

```
Install Scrap Master: https://raw.githubusercontent.com/festomanolo/scrap-master/main/docs/install.md
```

> 🛡️ **Safe by default:** `scrap-master install` only checks the machine and lists missing dependencies:
> ```
> Safely check and install Scrap Master: https://raw.githubusercontent.com/festomanolo/scrap-master/main/docs/install.md
> ```
> Only use `--system` after the user explicitly approves system-level installs and configuration writes.

---

## For AI Agents

### Goal


### ⚠️ Boundaries

When fixing issues, stay within these limits:

- **DO NOT** run commands with `sudo` unless the user explicitly approved
- **DO NOT** modify system files outside `~/.scrap-master/`
- **DO NOT** install packages not listed in this guide
- **DO NOT** disable firewalls, security settings, or system protections
- **DO NOT** clone repos, create files, or run commands inside the agent workspace / working directory
- If something requires elevated permissions, **tell the user** what's needed and let them decide

### 📁 Directory Rules

All Scrap Master files go in dedicated directories — **never in the agent workspace**:

| Purpose | Directory | Example |
|---------|-----------|---------|
| Config & tokens | `~/.scrap-master/` | `~/.scrap-master/config.json` |
| Temporary files | `/tmp/` | `/tmp/yt-dlp-output/` |
| Skills | `~/.openclaw/skills/scrap-master/` | SKILL.md |

**Why?** If you clone repos or create files in the workspace, it pollutes the user's project directory and can break their agent over time. Keep the workspace clean.

### Step 1: Install the basics

```bash
# Recommended: pipx (simplest method)
pipx install https://github.com/festomanolo/scrap-master/archive/main.zip
scrap-master install --env=auto               # Read-only check (default)
# After the user explicitly approves system changes:
scrap-master install --env=auto --system

# If your Python comes from Homebrew / you hit PEP 668 (externally-managed-environment)
# install in a virtual environment:
python3 -m venv ~/.scrap-master-venv
source ~/.scrap-master-venv/bin/activate
pip install https://github.com/festomanolo/scrap-master/archive/main.zip
scrap-master install --env=auto               # Read-only check (default)
# After the user explicitly approves system changes:
scrap-master install --env=auto --system
```

> 💡 **Windows / Microsoft Store Python alias?**
> If `python3 --version` opens the Microsoft Store, or `where python3` points to
> `...\AppData\Local\Microsoft\WindowsApps\python3.exe`, then `python3` is a Windows Store alias,
> not a usable Python installation. Use the Python Launcher `py -3` instead, or the `python.exe`
> in your actual Python installation directory.
>
> PowerShell example:
> ```powershell
> py -3 -m venv $env:USERPROFILE\.scrap-master-venv
> $env:USERPROFILE\.scrap-master-venv\Scripts\Activate.ps1
> python -m pip install https://github.com/festomanolo/scrap-master/archive/main.zip
> scrap-master install --env=auto
> ```

The default command checks core infrastructure (gh CLI, Node.js, mcporter, Exa search, yt-dlp config) without changing the host. With explicit `--system` approval it installs/configures the missing pieces and activates these zero-config channels:


> 💡 **macOS / Homebrew Python showing `externally-managed-environment`?**
> This is PEP 668 protection — not a Scrap Master issue. Use `pipx install ...` first, or create a `venv` before installing.

**Install modes:**

```bash
scrap-master install --env=auto             # Check only; safe default
scrap-master install --env=auto --safe      # Same check-only behavior (compatibility)
scrap-master install --env=auto --system    # Explicitly allow external/system installs
scrap-master install --env=auto --dry-run   # Preview what --system would do
```

### Step 2: Ask the user which optional channels they want

After installing the basics, **ask the user** which additional channels they need. Present this list:

> The core channels are ready! You can now search the web, watch YouTube, read GitHub, and more.
>
> Here are the optional channels — which ones do you need?
>
> - 🐦 **Twitter/X** — search tweets, view timeline (requires login cookie)
> - 📖 **Reddit** — search and read posts (login required: desktop OpenCLI or rdt-cli + cookie)
> - 📘 **Facebook** — search, pages, feed, group list (desktop OpenCLI, reuses Chrome session)
> - 📷 **Instagram** — user search, profiles, recent posts, explore (desktop OpenCLI, reuses Chrome session)
> - 💼 **LinkedIn** — profile, job search
>

Based on the user's choice, run:

```bash
scrap-master install --env=auto --system --channels=facebook,instagram    # Desktop Meta channels
scrap-master install --env=auto --system --channels=all                   # User approved everything
```


### Step 3: Fix what's broken

Run `scrap-master doctor` and check the output.

Try to get as many channels to ✅ as possible. If something failed during install or shows as ❌/⚠️ in doctor, diagnose the problem and try to fix it — but stay within the boundaries above. If a fix requires elevated permissions or system changes, ask the user first.

Only ask the user when you genuinely need their input (credentials, permissions, etc.).

### Step 3: Configure things that need user input

Some channels need credentials only the user can provide. Based on the doctor output, ask for what's missing:

> 1. **Account ban** — platforms may detect non-browser API calls and restrict or ban the account
> 2. **Credential exposure** — cookies grant full account access; using a secondary account limits the blast radius if credentials are ever compromised

> 🍪 **Cookies / login sessions:**
>
> 1. The user logs in to the platform in their browser
> 2. Install the [Cookie-Editor](https://chromewebstore.google.com/detail/cookie-editor/hlkenndednhfkekhgcdicdfddnkalmdm) Chrome extension
> 3. Click the extension → Export → Header String
> 4. Paste the exported string to the Agent
>

**Twitter search & posting:**
> "To unlock Twitter search, I need your Twitter cookies. Install the Cookie-Editor Chrome extension, go to x.com/twitter.com, click the extension → Export → Header String, and paste it to me."

```bash
scrap-master configure twitter-cookies
```

This saves `twitter_auth_token` and `twitter_ct0` for `scrap-master doctor` to check whether credentials are present. `doctor` does not run the upstream `twitter status` in real time and does not modify the current shell. Before running `twitter search/read/...` directly, you must explicitly set the following in that process environment:

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
> 1. Confirm the user has a proxy configured: `scrap-master configure proxy` (hidden input)
> 2. Set environment variables: `export HTTP_PROXY="..." HTTPS_PROXY="..."`
> 3. Scrap Master handles the rest automatically — no additional action needed from the user
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
> scrap-master configure proxy
> ```


> browser cookies. OpenCLI only uses an existing Chrome session explicitly controlled by the user.
> If no existing session is present, do not automate login; use a Cookie-Editor manual export
>
> ```bash
> ```
>
>
> **Desktop (recommended: OpenCLI):**

```bash
scrap-master install --system --channels opencli
```

> After installation, guide the user through the one manual step (Chrome security limitation — cannot be automated):
> 1. Open https://chromewebstore.google.com/detail/opencli/ildkmabpimmkaediidaifkhjpohdnifk
> 2. Click "Add to Chrome"
> 3. Run `opencli doctor` to verify (shows "Extension: connected" when successful)
>
> When AUTH_REQUIRED and the user has no existing session, do not auto-login; switch to the
>
> 2. Start the service (first run auto-downloads ~150MB headless browser — wait for it to finish)
> 3. Import cookies manually using the Cookie-Editor flow above
> 5. Always include `--timeout 120000` when calling it
>
> (upstream unmaintained since March 2026 — not recommended for new installs); authentication still
> uses the Cookie-Editor manual export flow above.

**Facebook / Instagram (desktop OpenCLI):**
> Both platforms use OpenCLI, which reuses the user's Chrome login session without storing credentials and without going through the Meta Graph API approval process. Server / no-desktop environments are not supported.

```bash
scrap-master install --system --channels facebook,instagram
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


```bash
```



The transcription script is automatically installed with Scrap Master; the user only needs to provide a key:

```bash
scrap-master configure groq-key
```

> **Get a Groq API key (free, no credit card, 30 seconds):**
> 1. Go to https://console.groq.com
> 2. Sign in with Google/GitHub (or register)
> 3. Left menu → API Keys → Create API Key
> 4. Copy the key (starts with `gsk_`) and paste it to the Agent
>
> **How to use:**
> ```bash
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



1. First explain that an upstream CLI will be installed and a dedicated Chrome profile directory created, and request approval for system-level installation.
2. After the user approves, run:
   ```bash
   ```
3. Launch the dedicated Chrome bound to loopback only per your OS:
   ```bash
   # macOS
   open -na "Google Chrome" --args --remote-debugging-address=127.0.0.1 \

   # Linux
   google-chrome --remote-debugging-address=127.0.0.1 \
   ```
   Windows PowerShell：
   ```powershell
   ```
4. Pause and have the **user visually confirm** they are logged in (avatar in the top right); if not logged in, have the **user manually
   log in**, scan QR, or handle any slider. The Agent must not request credentials, log in on
   and does not represent the Chrome login state.
5. After the user confirms login is complete, run:
   ```bash
   ```

> Security boundary: any local process that can reach debug port 9222 has full control over this Chrome.
> You must use `--remote-debugging-address=127.0.0.1` — never expose it to LAN or the internet.
> Use a dedicated profile and reuse it long-term; do not delete or recreate it for each run, and do
> not support server / no-desktop environments. Search commands must include
> `--browser-source existing-browser --cdp-url http://localhost:9222`。
>
> upstream commit
> `4c991b77086a203173bf08a4cb64a23af6514fe6` rather than a moving branch. That commit includes
> `browser_source="existing-browser"` (strict CDP), `JobItem.lid`, and `job_card_browser()`. Switch to
> a version constraint after an official upstream release.

### Step 4: Final check

Run `scrap-master doctor` one final time and report the results to your user.

### Step 5: Set up daily monitoring (OpenClaw only)

If you are running inside **OpenClaw**, ask your user:

> "Scrap Master is set up! Would you like me to create a daily automated check task? It will monitor these channels and check for new versions — only notifying you when something is wrong or an update is available."

If the user agrees, create a **cron job** (daily, `sessionTarget: "isolated"`, `delivery: "announce"`) with this task:

```
Run the scrap-master watch command.
If the output contains "all good", do not notify the user — finish silently.
If the output contains issues (❌ ⚠) or a new version (🆕), send the full report to the user with suggested fixes.
If a new version is available, ask the user whether to upgrade (paste this to the user's Agent for a full update: Update Scrap Master: https://raw.githubusercontent.com/festomanolo/scrap-master/main/docs/update.md).
```

If the user wants a different agent to handle it, let them choose.

---

## Quick Reference

| Command | What it does |
|---------|-------------|
| `scrap-master install --env=auto` | Read-only dependency and channel check (default) |
| `scrap-master install --env=auto --system` | Explicitly install/configure core external tools |
| `scrap-master install --env=auto --system --channels=all` | Install everything after explicit approval |
| `scrap-master install --env=auto --safe` | Compatibility alias for the safe default |
| `scrap-master install --env=auto --dry-run` | Preview what would be done |
| `scrap-master doctor` | Show channel status |
| `scrap-master watch` | Quick health + update check (for scheduled tasks) |
| `scrap-master check-update` | Check for new versions |
| `scrap-master configure twitter-cookies` | Save Twitter cookies via hidden input; direct calls still require explicit env vars |
| `scrap-master configure proxy` | Save proxy address via hidden input; not an automatic unlock switch |

After installation, use upstream tools directly. See SKILL.md for the full command reference:

| Platform | Upstream Tool | Example |
|----------|--------------|---------|
| Twitter/X | `twitter` (fallback: `opencli`) | Set `TWITTER_AUTH_TOKEN` / `TWITTER_CT0` then run `twitter search "query" -n 10` |
| YouTube | `yt-dlp` | `yt-dlp --dump-json URL` |
| Reddit | `opencli` (fallback: `rdt`) | `opencli reddit search "query" -f yaml` / `rdt read POST_ID` |
| Facebook | `opencli` | `opencli facebook search "query" -f yaml` |
| Instagram | `opencli` | `opencli instagram user nasa -f yaml` |
| GitHub | `gh` | `gh search repos "query"` |
| Web | `curl` + Jina | `curl -s "https://r.jina.ai/URL"` |
| Exa Search | `mcporter` | `mcporter call exa.web_search_exa query="..." numResults=5` |
| LinkedIn | `mcporter` | `mcporter call linkedin.get_person_profile linkedin_username="..."` |
| RSS | `feedparser` | `python3 -c "import feedparser; ..."` |

> For multi-backend platforms, use the `active_backend` from `scrap-master doctor --json`.
