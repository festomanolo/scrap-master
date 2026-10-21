# Twitter Advanced Setup Guide (twitter-cli)

Basic reading via Jina Reader is free and requires no configuration.

Advanced features require twitter-cli (@public-clis/twitter-cli):

- Tweet search (`twitter search`)
- Read full tweets and conversation threads (`twitter tweet`, `twitter thread`)
- User timeline (`twitter timeline`)
- Long-form post reading (`twitter article`)

twitter-cli is a free, open-source tool (installed via pipx), but requires your Twitter account cookie.

## Quick setup

1. Check if twitter-cli is installed:

```bash
which twitter && echo "installed" || echo "not installed"
```

2. Install twitter-cli:

```bash
pipx install twitter-cli
```

3. Confirm the command is installed (no authentication request at this step):

```bash
twitter --help
```

## Get cookies (Cookie-Editor method, recommended)

1. Install the [Cookie-Editor](https://cookie-editor.com/) browser extension
2. Log in to x.com
3. Click the Cookie-Editor icon → Export → Header String
4. Run the configuration command:

```bash
scrap-master configure twitter-cookies
```

This extracts `auth_token` and `ct0` and saves them securely to
`~/.scrap-master/config.yaml` for `scrap-master doctor` to check whether explicit
credentials are present. `doctor` does not run `twitter status`, does not verify
the account in real time, and does not modify the current shell.

By default, only `~/.scrap-master/config.yaml` is written. The following files are only
written when the user explicitly consents and adds `--sync-legacy-twitter`:

- `~/.config/xfetch/session.json`
- `~/.config/bird/credentials.env`

```bash
scrap-master configure twitter-cookies --sync-legacy-twitter
```

`scrap-master uninstall` will mention these legacy copies but will not auto-delete them.
When cleaning up, confirm with the user first, then delete those two files manually.

`twitter` is a standalone upstream command that does not read Scrap Master config files.
When running `twitter status/search/read/...` directly, you must explicitly set
`TWITTER_AUTH_TOKEN` and `TWITTER_CT0` in the current shell or subprocess environment.
Do not rely on automatic browser cookie reads.

## Set cookies manually

If you already know your `auth_token` and `ct0`:

1. Install twitter-cli (if not already): `pipx install twitter-cli`

2. Set environment variables:

```bash
export TWITTER_AUTH_TOKEN="your_auth_token"
export TWITTER_CT0="your_ct0"
```

3. Test:

```bash
twitter search "test" -n 1
```

## Proxy configuration

twitter-cli supports proxy via environment variables:

```bash
export HTTP_PROXY="http://user:pass@host:port"
export HTTPS_PROXY="http://user:pass@host:port"
twitter search "test" -n 1
```

Or use a global proxy tool:

```bash
proxychains twitter search "test" -n 1
```

## Fallback: bird CLI

If you have [bird CLI](https://www.npmjs.com/package/@steipete/bird) installed
(`npm install -g @steipete/bird`), it also works. Scrap Master automatically detects
and uses installed bird. Both tools have similar functionality; twitter-cli is the
current recommended option.
