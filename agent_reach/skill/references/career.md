# Jobs & Career

LinkedIn, Boss Zhipin.

## LinkedIn

```bash
# Get a person's profile
mcporter call linkedin.get_person_profile linkedin_username="username" sections="experience,education"

# Search people
mcporter call linkedin.search_people keywords="AI engineer" location="Shanghai"

# Get a company's profile
mcporter call linkedin.get_company_profile company_name="openai" sections="posts,jobs"

# Search jobs
mcporter call linkedin.search_jobs keywords="software engineer" location="Remote" max_pages=2
```

> **Login required**: Before first use, run `uvx mcp-server-linkedin@latest --login` to save a valid session.

### Fallback

If MCP is unavailable, use Jina Reader:

```bash
curl -s "https://r.jina.ai/https://linkedin.com/in/username"
```

## Boss Zhipin

When the user says "help me configure Boss Zhipin", follow this section to complete
installation, launch a dedicated Chrome, wait for the user to log in manually, and run
final verification. Do not expose CDP port numbers or other implementation details to the
user upfront, and never enter credentials, scan QR codes, or handle sliders on the user's behalf.

> **Key distinction: login gate ≠ anti-bot security challenge.** After opening zhipin.com,
> the browser may land on one of three pages: the logged-in `web/geek/job` page, the
> login page `web/user/` (QR scan / phone login), or the **security challenge page**
> (URL contains `security-check` / `zhipin-security` / `_security_check`).
> The security challenge is unrelated to login state — **it appears even when logged in**
> (almost guaranteed with a CDP debugging port attached). Never judge login state by the URL.

> **Two credential stores (both required, both serve different channels).**
>
> | Store | Role |
> |---|---|
> | `~/.boss-agent/auth/session.enc` | ① Hard gate: `_get_browser()` unconditionally calls `get_token()` — unreadable means `AuthRequired` before the CDP connection is even attempted. ② **Not** search credentials in CDP mode: when reusing the real Chrome's `contexts[0]`, its cookies are only injected in the "no context" branch and never actually used. ③ httpx channel (low-risk ops: `status`/`detail`/`cities`/`job_card_httpx`) uses its cookies + stoken; code 37's `force_refresh()` writes back to it. |
> | Browser cookies in the dedicated Chrome profile | The actual credentials carried by CDP-mode search/greet and other high-risk operations |
>
> **`boss status` / `status --live` only validates session.enc** — even if it reports
> `logged_in: true`, that does not mean the CDP browser is logged in. Therefore:
> 1. After launching the dedicated Chrome, the **first step is to pause and have the user
>    visually confirm** they are logged in (avatar visible in the top right). Only then
>    proceed to run search commands.
> 2. The `boss` line in `doctor` directly probes the browser for the `wt2` cookie — use
>    that as ground truth.
> 3. **`AUTH_EXPIRED` is ground truth**: if search returns it, go straight to the login
>    runbook (user logs in through the dedicated window → `login --cdp`). Do not
>    interpret this as a security challenge.
> 4. Do not delete `session.enc` to "clear old credentials" — to refresh it, run
>    `login --cdp`.

> **Dependency status**: The required public strict-CDP API comes from boss-agent-cli
> PRs #403–#407 (split from #402/#382 per maintainer request), all merged into upstream
> master. Agent Reach's installer pins to upstream commit
> `4c991b77086a203173bf08a4cb64a23af6514fe6` rather than a moving branch. Switch to a
> version constraint once an official release containing those PRs ships.

Health check (no side effects, no search):

```bash
agent-reach doctor          # boss line: off = not installed or CDP not reachable;
                            # warn = pipeline ready; message shows whether the browser
                            # has the wt2 login cookie (browser is ground truth)
```

Search + JD uses the public API (`browser_source` / `job_card_browser` / `JobItem.lid`).
Because pipx/uv tool environments are isolated, the regular `python` command may not be
able to import an installed tool. Use `uv run --with` to ensure the script and its pinned
dependencies share the same interpreter:

```bash
uv run --isolated --no-project \
  --with 'git+https://github.com/can4hou6joeng4/boss-agent-cli.git@4c991b77086a203173bf08a4cb64a23af6514fe6' \
  python - <<'PY'
from pathlib import Path

from boss_agent_cli.api.client import AccountRiskError, BossClient, EnvironmentRiskError
from boss_agent_cli.auth.manager import AuthManager
from boss_agent_cli.platforms.zhipin import BossPlatform

auth = AuthManager(Path.home() / ".boss-agent")

# Strict CDP mode: reuse the logged-in browser, fail immediately on CDP error, never headless
with BossClient(
    auth,
    cdp_url="http://localhost:9222",
    browser_source="existing-browser",
) as boss:
    raw = boss.search_jobs("LLM", city="Shenzhen", page=1)
    if raw.get("code") != 0:
        code, message = BossPlatform(boss).parse_error(raw)
        raise RuntimeError(f"{code}: {message}")
    items = raw.get("zpData", {}).get("jobList", [])
    for item in items:
        card = boss.job_card_browser(item["securityId"], item["lid"])
        post_desc = card.get("zpData", {}).get("jobCard", {}).get(
            "postDescription", ""
        )
        print(item.get("jobName"), post_desc)

# AccountRiskError / EnvironmentRiskError → stop immediately, no auto-retry.
# Only a code 37 explicitly stating token/stoken expiry is TOKEN_REFRESH_FAILED;
# the client retries at most once, then requires re-login.
PY
```

### Environment check and recovery runbook (run before scraping)

If `agent-reach doctor` reports boss as `off` or `warn`, follow this runbook — do not guess from source code:

1. **Is the CDP port reachable?**
   ```bash
   curl -s http://localhost:9222/json/version   # 'Browser' field present = port is up
   ```

2. **Debugging Chrome is not running / was closed**: Launch the dedicated Chrome per your OS
   (session is isolated — does not affect your daily browser):
   ```bash
   # macOS
   open -na "Google Chrome" --args --remote-debugging-address=127.0.0.1 \
     --remote-debugging-port=9222 --user-data-dir="$HOME/.boss-chrome-profile" \
     "https://www.zhipin.com/web/geek/job"

   # Linux
   google-chrome --remote-debugging-address=127.0.0.1 \
     --remote-debugging-port=9222 --user-data-dir="$HOME/.boss-chrome-profile" \
     "https://www.zhipin.com/web/geek/job"
   ```

   Windows PowerShell:
   ```powershell
   Start-Process chrome.exe -ArgumentList '--remote-debugging-address=127.0.0.1','--remote-debugging-port=9222',"--user-data-dir=$env:USERPROFILE\.boss-chrome-profile",'https://www.zhipin.com/web/geek/job'
   ```

   Bind to loopback only. Any local process that can reach port 9222 has full control
   over that Chrome — never expose it to LAN or the internet. Reuse this dedicated profile
   long-term to keep a stable login state; never delete or recreate it for each run, and
   never default to switching to the user's daily Chrome. Close the dedicated window when not in use.

   **After launch, the first step is to pause and have the user visually confirm they are
   logged in (avatar in the top right). Do not use `boss status` as a substitute — it only
   validates the local session.enc, not the browser.**

3. **User logs in manually (browser is not logged in)**: The ground truth is the browser
   cookie probe in `doctor` (no `wt2` = browser not logged in), followed by user visual
   confirmation. `boss status` is supplementary only. Have the user log in or scan QR in
   this dedicated window. After the user confirms, save the CDP login state:
   ```bash
   boss --cdp-url http://localhost:9222 login --cdp
   ```

   If the window shows a security challenge page (`security-check` / `zhipin-security`),
   that is an anti-bot challenge — not a login page. Wait for it to pass automatically or
   have the user solve the slider manually. Do not treat it as "not logged in" and restart
   the QR scan flow.

4. **Check whether the session is valid** (browser cookie probe + stoken expiry):
   ```bash
   agent-reach doctor     # check the browser wt2 cookie probe result in the boss line
   boss status            # reflects local session.enc only — supplementary
   ```

5. **Error code handling** (during search or JD fetch):
   - `AUTH_EXPIRED` (user not logged in) → **ground truth**: CDP browser is not logged in
     (regardless of what `boss status` says). Go straight to step 3's login flow +
     `login --cdp`. Do not interpret as a security challenge.
   - code 36 (ACCOUNT_RISK) → stop immediately, handle manually on the BOSS website, no auto-retry.
   - code 9 (RATE_LIMITED) → wait and retry.
   - code 37 + `environment anomaly` text → `ENVIRONMENT_RISK`, stop immediately — no token refresh, no re-login, no auto-retry.
   - Only a code 37 with text explicitly stating token/stoken expiry is `TOKEN_REFRESH_FAILED`; the client auto-retries once, then re-login is required.

When the user asks to start searching, the Agent must use strict CDP mode (global options before the subcommand):

```bash
boss --browser-source existing-browser --cdp-url http://localhost:9222 search "LLM" --city Guangzhou --page 1
```

Do not page through results silently. Boss-agent-cli PR #383 adds a 5–10 second persistent
list budget for ordinary cross-process searches; until that PR ships, the Agent should call
serially with reduced frequency.

> **Throttle waits are expected, not hangs**: when consecutive searches hit the throttle,
> boss-agent-cli silently waits 5–10 seconds (TTY shows "throttle wait Ns…"; when
> Agent Reach calls with `--json`, that message is not visible). Do not retry, spawn a
> new browser, or switch profiles during the wait window.
