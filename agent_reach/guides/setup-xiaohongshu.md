# XiaoHongShu Setup Guide

## What it does
Read and search XiaoHongShu (小红书) notes. Desktop preferably uses OpenCLI;
servers use [xiaohongshu-mcp](https://github.com/xpzouying/xiaohongshu-mcp);
xhs-cli is kept as a legacy fallback for users who already have it installed.

## Prerequisites
- OpenCLI: an existing, explicitly user-controlled Chrome session on XiaoHongShu
- xiaohongshu-mcp / legacy tools: Cookie-Editor browser extension

## Authentication boundary

Agent Reach never logs the user in to XiaoHongShu and never reads browser cookies.

OpenCLI only uses an existing Chrome session explicitly controlled by the user.
`agent-reach configure xhs-cookies` does not inject cookies into OpenCLI or Chrome.
If no existing session is present, do not automate login; use a manual Cookie-Editor
export to configure xiaohongshu-mcp or a legacy tool instead:

1. Install the [Cookie-Editor](https://chromewebstore.google.com/detail/cookie-editor/hlkenndednhfkekhgcdicdfddnkalmdm) extension in Chrome
2. Have the user prepare the session they want to export on xiaohongshu.com
3. Click the Cookie-Editor icon → Export → Header String
4. Paste the exported string to the Agent and run:

```bash
agent-reach configure xhs-cookies
agent-reach doctor
```

This explicit command saves/imports the user-provided xiaohongshu.com-domain cookie set.
Confirm the cookie names and scope before proceeding. Cookies from non-xiaohongshu.com
domains are ignored.

If a xiaohongshu-mcp container is running, the configure command imports the cookies into
the container; otherwise it writes to a local owner-only file and prints the path for
manual import.

## Usage examples

Check `agent-reach doctor --json` for `active_backend` first, then pick the right command.
Legacy xhs-cli examples:

Search notes:
```bash
xhs search "query"
```

Read a note's full content:
```bash
xhs read NOTE_ID
```

View comments:
```bash
xhs comments NOTE_ID
```

## FAQ

**Q: Cookies expired?**
A: Export again via Cookie-Editor, then run `agent-reach configure xhs-cookies`
and paste into the hidden input prompt.

**Q: XiaoHongShu reports an IP risk?**
A: Use a residential proxy: `export HTTP_PROXY="http://user:pass@ip:port"`.

**Q: xhs-cli doesn't support my system?**
A: Ensure Python 3.10+ and pipx are installed. Run `pipx install xiaohongshu-cli`.

## Server option: Docker MCP

If you are already using the [xiaohongshu-mcp](https://github.com/xpzouying/xiaohongshu-mcp)
Docker setup, it also works:

```bash
docker run -d \
  --name xiaohongshu-mcp \
  -p 18060:18060 \
  xpzouying/xiaohongshu-mcp

mcporter config add xiaohongshu http://localhost:18060/mcp --scope home
```

This server backend uses the same Cookie-Editor manual export process described above.
