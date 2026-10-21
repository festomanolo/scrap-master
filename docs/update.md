# Scrap Master — Update Guide

## For Humans

Copy this to your AI Agent:

```
Update Scrap Master: https://raw.githubusercontent.com/festomanolo/scrap-master/main/docs/update.md
```

---

## For AI Agents

### ⚠️ Workspace Rules

**Never create files, clone repos, or run commands in the agent workspace.** Use `/tmp/` for temporary work and `~/.scrap-master/` for persistent data.

### Goal

Update Scrap Master to the latest version, refresh upstream tools, migrate from retired backends, and verify everything works. The user should not need to do anything manually (except things only a human can do, like clicking a browser-extension install button).

### Step 1: Check current version

```bash
scrap-master check-update
```

If it says "Already up to date", skip to Step 4 (verify). Otherwise continue.

### Step 2: Update Scrap Master package

```bash
pip install --upgrade https://github.com/festomanolo/scrap-master/archive/main.zip
```

> If pip complains about `externally-managed-environment` (PEP 668), the user
> originally installed via pipx or a venv — use the matching command:
> `pipx install --force https://github.com/festomanolo/scrap-master/archive/main.zip`
> or activate `~/.scrap-master-venv` first.

### Step 3: Refresh upstream tools

Run these to keep installed tools current. **Only upgrade what is already
installed — do not install new tools the user never asked for** (the one
exception: OpenCLI on desktop, see below).

```bash
# Python-based CLIs the user already has (upgrade keeps signatures fresh)
which twitter >/dev/null 2>&1 && { pipx upgrade twitter-cli 2>/dev/null || uv tool upgrade twitter-cli 2>/dev/null; }
which yt-dlp  >/dev/null 2>&1 && { pipx install --force 'yt-dlp[default]' 2>/dev/null || uv tool install --force 'yt-dlp[default]' 2>/dev/null || python -m pip install -U 'yt-dlp[default]' 2>/dev/null; }

# rdt-cli is pinned to a git source (PyPI lags upstream) — same pin as the code's _RDT_GIT_SOURCE
which rdt >/dev/null 2>&1 && pipx install --force 'git+https://github.com/public-clis/rdt-cli.git@5e4fb3720d5c174e976cd425ccc3b879d52cac66' 2>/dev/null

# npm-based
which mcporter >/dev/null 2>&1 && npm update -g mcporter 2>/dev/null
which opencli  >/dev/null 2>&1 && npm update -g @jackwener/opencli 2>/dev/null
```

**Desktop users without OpenCLI**: since v1.5.0 OpenCLI is the preferred
by the user. The update must never log the user in or read browser cookies:

> "This update introduces the OpenCLI backend. Want to install it? All you need to do
> uses your existing Chrome session; if there is no existing session, I will not log in
> automatically — I will use Cookie-Editor to configure the MCP / legacy tools instead."

If yes: `scrap-master install --system --channels opencli` and guide them through the
extension click. If no, everything keeps working on existing backends.

### Step 4: Coexistence (DO NOT uninstall old tools)

**Never uninstall tools the user already has.** Retired backends (e.g. yt-dlp
working as fallbacks where they still function. Scrap Master routes around
them automatically — removal is the user's call, not yours.

### Step 5: Verify

```bash
scrap-master version
scrap-master doctor
```

Running `scrap-master doctor` (text mode) also makes sure a Scrap Master skill
exists in detected agent skill directories. If the user already has a skill
there, doctor preserves it instead of overwriting local customizations. Use
`scrap-master skill --install` when you explicitly want to refresh the bundled
skill files.

Check the doctor output:

- Every channel shows ✅ / [!] with a clear message, and multi-backend
- If a previously-working channel now shows [X]/error, the message contains
  the exact fix (e.g. a venv-reinstall prescription) — run it, then re-check
- `--json` gives the same data machine-readably (`active_backend` per channel)

### Step 6: Report to user

Tell the user:

1. What version they're on now (`scrap-master version`)
2. How many channels are available, and which backend each multi-backend
   platform is using (from doctor)
3. Anything that needs their action (e.g. a Chrome extension click, or a
4. What changed in this update (release notes shown by `check-update`)

Done.
