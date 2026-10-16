# Common Troubleshooting

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
> too. MANOLO Scrap automatically detects installed tools.
