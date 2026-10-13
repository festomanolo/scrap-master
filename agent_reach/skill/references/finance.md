# Financial Data

Xueqiu stock quotes, search, and trending content. Data may be delayed — not financial advice.

## Check status first

```bash
agent-reach doctor --json
```

If `xueqiu.active_backend` has a value, use that backend. A `null` value only means Doctor
did not complete a live content check. Xueqiu requires a logged-in session or minimal
cookie — do not treat HTTP 400 as "stock does not exist".

## OpenCLI (preferred when desktop Chrome has a logged-in session)

```bash
# Verify current login state
opencli xueqiu whoami -f yaml

# Stock search and live quotes
opencli xueqiu search "NVIDIA" -f yaml
opencli xueqiu stock NVDA -f yaml

# Trending content and trending stocks
opencli xueqiu hot -f yaml
opencli xueqiu hot-stock -f yaml

# List all read-only commands
opencli xueqiu --help
```

OpenCLI only reuses an existing, explicitly user-controlled browser session.
Do not run `opencli xueqiu login` automatically. If no existing session is present,
have the user log in to Chrome first, or explicitly import the minimum required cookies:

```bash
agent-reach configure --from-browser chrome --platform xueqiu
```

This only reads and saves `xq_a_token` — it does not collect cookies from other platforms.

## Validation and failure handling

- Success means getting a stock name, ticker, price, or non-empty content list.
  An exit code of 0 with all fields empty is not a success.
- HTTP 400 is usually a session/cookie issue, not a missing stock ticker.
- If `whoami` succeeds but `stock`/`hot` fails, report as a parsing or platform API issue —
  do not misdiagnose as "not logged in".
