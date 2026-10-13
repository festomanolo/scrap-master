# Exa Search Setup Guide

## What it does
Exa is an AI semantic search engine. Integrated via MCP — **free, no API key required**. Once configured, it unlocks:
- Full web semantic search
- Reddit search (via `site:reddit.com`)
- Twitter search (via `site:x.com`)

## Steps the Agent can do automatically

After the user explicitly approves, `agent-reach install --env=auto --system` completes the following steps.
The default command without `--system` only does a read-only check.

### 1. Install mcporter
```bash
npm install -g mcporter
```

### 2. Register the Exa MCP
```bash
mcporter config add exa https://mcp.exa.ai/mcp --scope home
```

### 3. Verify
```bash
agent-reach doctor | grep "Search"
mcporter call exa.web_search_exa query="test" numResults=1
```

## Steps the user must do manually

**None.** Exa integrates via MCP — free, no sign-up, no API key required.

If `agent-reach install --system` didn't configure Exa due to a network issue, just run the two commands above manually.

## FAQ

**Q: Are there search request limits?**
A: The MCP endpoint is provided by Exa directly (mcp.exa.ai) and is currently free without limits. If that changes, agent-reach updates will adapt accordingly.

**Q: What is mcporter?**
A: A CLI bridge for the MCP protocol, used to call MCP servers. Agent Reach uses it to connect to Exa and XiaoHongShu.
