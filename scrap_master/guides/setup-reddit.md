# Reddit Setup Guide

## What it does

Reddit blocks almost all non-browser direct access (including datacenter and ISP proxy IPs) — the JSON API returns 403.

Scrap Master uses **rdt-cli** (or **OpenCLI** on desktop) to enable Reddit search and reading:
- **Search**: `rdt search "query"`
- **Read full post + comments**: `rdt read POST_ID`

Free, no proxy required, no API key. Requires login authentication (`rdt login`, which automatically extracts cookies from your browser).

## Steps the Agent can do automatically

1. Check if rdt-cli is available:
```bash
which rdt && echo "installed" || echo "not installed"
```

2. If not installed, install it automatically (PyPI version lags upstream — install from GitHub):
```bash
pipx install 'git+https://github.com/public-clis/rdt-cli.git'
```

Or install with one command:
```bash
scrap-master install --env=auto --system --channels=reddit
```

## Usage examples

Search Reddit content:
```bash
rdt search "python best practices" -n 5
```

Read a full post and comments:
```bash
rdt read POST_ID
```

## Steps the user must do manually

None. After the user explicitly approves, rdt-cli is installed via:
`scrap-master install --env=auto --system --channels=reddit`

## Fallback: Exa search

If Exa is configured (via mcporter), you can also search Reddit content through it:

```bash
mcporter call exa.web_search_exa query="site:reddit.com python best practices" numResults=5
```

rdt-cli is the recommended approach — no extra configuration needed.
