# Search Tools

Exa AI search engine.

## Exa AI Search

High-quality AI search engine, ideal for finding technical documentation, official examples, and relevant web pages.

```bash
mcporter call exa.web_search_exa query="query" numResults=5
mcporter call exa.web_search_exa query="library API code example" numResults=5
```

### Use cases

| Scenario | Parameters |
|----------|------------|
| Web search | `web_search_exa(query: "...", numResults: 5)` |
| Technical / code resources | `web_search_exa(query: "framework name API example", numResults: 5)` |

> The Exa MCP's `get_code_context_exa` is deprecated and not registered by default.
> For code questions, use `web_search_exa`. For precise repository searches, use
> GitHub Search in `dev.md`.

### Strengths

- Strong for English content and technical documentation
- Good at locating official docs and code examples from query keywords
- High result quality

## Comparison with other search tools

| Tool | Source | Best for |
|------|--------|----------|
| Exa | agent-reach | English / technical / code search |
| GitHub Search | agent-reach (dev.md) | Repository / code search |
