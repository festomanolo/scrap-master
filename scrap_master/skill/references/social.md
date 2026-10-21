# Social Media & Communities


# Search notes

# Read a note's full content + engagement data (use the complete URL from search results, including xsec_token)

# Comments (including nested replies)

# Home feed

# Public notes on a user's profile
```

> Requires Chrome open with the OpenCLI extension installed. OpenCLI may only
> use an existing Chrome session explicitly controlled by the user.
> Scrap Master never logs the user in or reads browser cookies.
> If no existing session is present, do not automate login; switch to backends B/C
> and follow the Cookie-Editor manual export process.

# Have the user manually export cookies via Cookie-Editor first, then import explicitly

# Read-only status check

# Search

# Note detail + comments (get feed_id and xsec_token from search results)
```

> The first call automatically downloads ~150 MB of a headless browser — use `--timeout 120000`.
> Authentication only goes through a manual Cookie-Editor export; after importing, run
> `check_login_status` first. This explicit command saves/imports the user-provided

### General Notes

> browser cookies. OpenCLI may only use an existing, explicitly user-controlled Chrome session.
>
> **Do not fetch directly with a bare note_id.** The correct flow: search/feed first
> to get results, then use the complete URL/ID from those results. All three backends work the same way.
>
> **Rate limiting**: High-frequency requests (bulk search, deep comment pagination) trigger
> CAPTCHAs — platform limits cannot be bypassed. Space operations 2-3 seconds apart.
>
> write operations may return 406 due to signature issues.

## Twitter/X (twitter-cli)

### Authentication prerequisite

Cookies saved by `scrap-master configure twitter-cookies` are used only by
`scrap-master doctor` to check whether explicit credentials are present.
`doctor` does not run `twitter status` and does not configure the current shell.
Before running any `twitter` command, you must explicitly set the following in
the same shell or subprocess environment:

```bash
export TWITTER_AUTH_TOKEN="..."
export TWITTER_CT0="..."
```

### Stable commands

```bash
# Home timeline (most stable)
twitter feed -n 20

# Read a single tweet (including replies)
twitter tweet URL_OR_ID

# Read long-form post / X Article
twitter article URL_OR_ID

# User timeline
twitter user-posts @username -n 20

# User profile
twitter user @username
```

### Potentially unstable commands

```bash
# Tweet search (Twitter frequently changes GraphQL endpoints — may return 404)
twitter search "query" -n 10

# Likes (since 2024 you can only view your own — platform restriction)
twitter likes
```

### Retry chain when search fails (execute in order, stop at first success)

1. Retry once (transient failures are common): `twitter search "query" -n 10`
2. Upgrade and retry: `pipx upgrade twitter-cli && twitter search "query" -n 10`
3. Switch to OpenCLI fallback (desktop, uses browser session): `opencli twitter search "query" -f yaml`
4. If nothing works, use stable alternatives: `twitter feed` / `twitter user-posts @somebody`

### Important notes

> **Installation**: `pipx install twitter-cli` (ensure v0.8.5+)
>
> **Authentication**: Only use Cookie-Editor manual export, then explicitly set environment
> variables `TWITTER_AUTH_TOKEN` + `TWITTER_CT0`. Do not rely on automatic browser reads.
>
> **IP-based rate limiting**: Do not make frequent calls from VPS/datacenter IPs,
> especially for followers/following — account suspension risk. Use residential proxies
> or a local environment.
>
> **OpenCLI fallback**: If OpenCLI is installed on desktop, `opencli twitter search/article/user-posts -f yaml`
> is fully available (browser session, no cookie env vars needed).
>
> **Output format**: Use `--yaml` or `--json` for structured output — more AI-agent-friendly.

# Subtitles (OpenCLI, requires desktop Chrome)
```

> For detailed commands (audio transcription, API fallback), see [references/video.md](video.md).

# node_name examples: python, tech, jobs, qna, programmers
```

### Topic detail

```bash
# Get trending topics
topics = ch.get_hot_topics(limit=10)
for t in topics:
    print(f"[{t['node_title']}] {t['title']} ({t['replies']} replies)")

# Get node topics
node_topics = ch.get_node_topics("python", limit=5)

# Get topic detail + replies
topic = ch.get_topic(1234567)
print(topic["title"], "—", topic["author"])

# Get user profile
user = ch.get_user("Livid")
```


## Reddit (multi-backend, login required)

**Reddit has no zero-config path**: anonymous `.json` endpoints are blocked (403), and official API applications since late 2025 are manually reviewed and rarely approved for personal projects. Both backends require a logged-in session. Run `scrap-master doctor --json` to check the `active_backend` for Reddit. Access from mainland China requires a proxy.

### Backend A: OpenCLI (preferred on desktop — reuses browser session)

```bash
# Search posts
opencli reddit search "query" -f yaml

# Read full post + comments
opencli reddit read POST_ID -f yaml

# Browse subreddit / trending / popular
opencli reddit subreddit LocalLLaMA -f yaml
opencli reddit hot -f yaml
opencli reddit popular -f yaml

# Subreddit metadata (subscriber count, description)
opencli reddit subreddit-info LocalLLaMA -f yaml
```

> Requires Chrome open and logged in to reddit.com.

### Backend B: rdt-cli (legacy/server fallback — upstream unmaintained since March 2026)

```bash
rdt search "query" --limit 10   # search posts
rdt read POST_ID                # read full post + comments
rdt sub python --limit 20       # browse subreddit
rdt popular --limit 10          # browse trending
rdt all --limit 10              # browse /r/all
```

> **Installation**: `pipx install 'git+https://github.com/public-clis/rdt-cli.git'`
> (PyPI version is outdated — install from GitHub for v0.4.2+). Run `rdt login` before
> searching or reading. On servers without a browser, set cookies manually per `doctor` instructions.
> Use `--yaml` output for AI-agent-friendly results.

### Advanced option: official API + PRAW (existing credentials only)

Users who registered a Reddit script app before late 2025 (having client_id/client_secret)
can use PRAW with the official API (100 QPM, free). New applications require manual review
and are rarely approved for personal projects — **do not recommend this route to new users**.

## Facebook (OpenCLI — login required)

Facebook goes through OpenCLI, which reuses the user's facebook.com login session in Chrome.
Run `scrap-master doctor --json` first to check the `active_backend` for Facebook — it should be `OpenCLI`.
Do not default to Jina/Exa/Graph API.

```bash
# Search users / pages / posts
opencli facebook search "query" -f yaml

# User or page profile
opencli facebook profile zuck -f yaml

# Current account's News Feed
opencli facebook feed --limit 10 -f yaml

# Group list / recent activity visible to current account
opencli facebook groups --limit 20 -f yaml
```

> Requires Chrome open with the OpenCLI extension installed and logged in to facebook.com.
> Facebook Groups currently only supports reading the group list and recent activity visible
> to the current account — arbitrary group posts and comments are not guaranteed.

## Instagram (OpenCLI — login required)

Instagram goes through OpenCLI, which reuses the user's instagram.com login session in Chrome.
Run `scrap-master doctor --json` first — `active_backend` should be `OpenCLI`.
Do not default to instaloader; historically cookies/401/429 are unstable there.

```bash
# Search users (not a global post keyword search)
opencli instagram search "query" -f yaml

# User profile
opencli instagram profile nasa -f yaml

# User's recent posts
opencli instagram user nasa --limit 12 -f yaml

# Explore / Discover
opencli instagram explore --limit 20 -f yaml

# Current account's saved posts
opencli instagram saved --limit 20 -f yaml
```

> Requires Chrome open with the OpenCLI extension installed and logged in to instagram.com.
> `instagram search` is a user search, not a global keyword post search. To read posts, find
> the username first, then use `instagram user USERNAME`. On 429 / login required errors,
> have the user re-login in Chrome and reduce call frequency.
