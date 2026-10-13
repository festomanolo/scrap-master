# Common Troubleshooting

## Xueqiu: API returns 400

**Symptom:** `scrap-master doctor` shows Xueqiu ⚠️ with `HTTP Error 400`

**Cause:** The Xueqiu API requires a login cookie and cannot be accessed anonymously.

**Solution:** Log in to xueqiu.com in Chrome, then run:

```bash
scrap-master configure --from-browser chrome --platform xueqiu
```

Run `scrap-master doctor` again to confirm it recovers to ✅. Repeat when the cookie expires.

---

## Boss Zhipin: `boss status` says logged in, but search returns `AUTH_EXPIRED`

**Symptom:** `boss status` / `status --live` returns `logged_in: true` (sometimes with a
username), but `boss ... search` immediately returns
`{"code": "AUTH_EXPIRED", "message": "user not logged in"}`.
The dedicated Chrome may also be showing a URL with `_security_check`, which looks like an
anti-bot slider.

**Cause:** Boss has two login state stores that authenticate different channels:

| Store | Who uses it |
|---|---|
| `~/.boss-agent/auth/session.enc` | `boss status` / `status --live`; httpx channel low-risk ops (`detail` / `cities` / `job_card_httpx`). CDP search reads it too (missing = immediate "not logged in"), but when reusing the real Chrome context, its cookies never actually take effect |
| Browser cookies in `~/.boss-chrome-profile` | The actual credentials carried by `existing-browser` strict-CDP mode search/greet and other high-risk operations |

`boss status` only validates the local session.enc. When the local store holds stale
credentials from days ago but the dedicated Chrome profile itself is not logged in, it still
reports `logged_in: true` — that is not proof the session is valid.
The `_security_check` page is an anti-bot challenge that **appears even when logged in** —
do not use it to judge login state. The two factors combined make it easy to misdiagnose
"browser not logged in" as "stuck on the slider".

> Do not delete either store. If session.enc is missing, CDP search fails before even
> connecting to the browser. To refresh it, run `login --cdp` — never delete it manually.

**Determination order:**

1. `AUTH_EXPIRED` is ground truth — it appears when the browser is not logged in, regardless
   of what `boss status` says.
2. The `boss` line in `scrap-master doctor` directly probes the browser for the `wt2` cookie —
   use that as ground truth.
3. `boss status` is supplementary only; the page URL is never used as evidence.

**Solution:** Visually confirm and manually log in to zhipin.com in the dedicated Chrome
window, then sync the login state:

```bash
boss --cdp-url http://localhost:9222 login --cdp
scrap-master doctor    # boss line message should show "browser login cookie (wt2) present"
```

> After launching the dedicated Chrome, always have the user visually confirm login state
> first — never use `boss status` as a substitute for that step.

---

## Twitter/X: twitter-cli connection failure

**Symptom:** `twitter search` or other commands return errors

**Cause:** twitter-cli requires `TWITTER_AUTH_TOKEN` and `TWITTER_CT0` environment variables
to access the Twitter API. The values saved by `scrap-master configure twitter-cookies` are
only for `doctor` to check whether credentials are present; doctor does not run upstream
authentication and does not configure the current shell. If your network requires a proxy to
reach x.com, you also need to configure a proxy.

**Solution:**

### Option 1: Set environment variables and proxy

```bash
export TWITTER_AUTH_TOKEN="..."
export TWITTER_CT0="..."
export HTTP_PROXY="http://user:pass@host:port"
export HTTPS_PROXY="http://user:pass@host:port"
twitter search "test" -n 1
```

### Option 2: Use a global proxy tool

Have the proxy tool take over all network traffic so twitter-cli requests go through it:

```bash
# macOS — ClashX / Surge with "enhanced mode"
# Linux — proxychains or tun2socks
proxychains twitter search "test" -n 1
```

### Option 3: Use Exa search instead of twitter-cli

When twitter-cli is unavailable, use Exa to search Twitter content directly:

```bash
mcporter call exa.web_search_exa query="site:x.com search_term" numResults=5
```

### Option 4: Check authentication

```bash
twitter check
```

> If it returns "Missing credentials", you need to set `TWITTER_AUTH_TOKEN` and `TWITTER_CT0`
> in the process environment where you run this command.
>
> **Fallback:** If you have bird CLI installed (`npm install -g @steipete/bird`), it works
> too. Scrap Master automatically detects installed tools.
