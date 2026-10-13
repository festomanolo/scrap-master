# -*- coding: utf-8 -*-
"""Boss Zhipin — search jobs and fetch JDs via boss-agent-cli + CDP Chrome.

The backend is boss-agent-cli (CDP debug port reusing a logged-in real Chrome). Headless is
forbidden (triggers code 36 risk control), so check() only performs four layers of read-only
probing without instantiating BossClient or launching a browser.

Scraping uses the boss-agent-cli public API (search_jobs + job_card_browser +
browser_source="existing-browser"); see skill/references/career.md for call patterns.
check() only handles "installed or not + CDP pipeline ready + browser login cookie present"
diagnostics — it does not search.

Two credential stores (health check must distinguish them — learned from experience).
Both are required but authenticate different channels:

- `~/.boss-agent/auth/session.enc` (`boss status` / `status --live` only validates this)
  1. Hard gate: `_get_browser()` unconditionally calls `get_token()` — unreadable means
     `AuthRequired`, so never delete it — CDP search fails before even connecting to the browser.
  2. But it is **not** the search credential: when CDP connects to the real Chrome and reuses
     `contexts[0]`, its cookies are only injected in the "no contexts" branch and never actually used.
  3. The httpx channel (low-risk ops: status/detail/cities/`job_card_httpx`) does use its
     cookies + stoken; code 37's `force_refresh()` also writes back to it.
- Browser cookies in the dedicated Chrome profile: the actual credentials carried by
  CDP-mode search/greet and other high-risk operations.

So: session.enc valid + browser not logged in = `boss status` reports logged_in but search
returns `AUTH_EXPIRED`. Layer 4 queries the CDP browser directly (Storage.getCookies) —
browser state is ground truth.
"""

import base64
import hashlib
import json
import os
import platform
import socket
import struct
import urllib.request
from urllib.parse import urlparse

from agent_reach.probe import probe_command
from agent_reach.utils.url import host_matches

from .base import Channel

_CDP_URL = "http://localhost:9222"
_CDP_TIMEOUT = 5


def _chrome_launch_command(system: str | None = None) -> str:
    """Return a dedicated-profile Chrome command for the current OS."""
    system = system or platform.system()
    common = (
        "--remote-debugging-address=127.0.0.1 "
        "--remote-debugging-port=9222 "
    )
    url = '"https://www.zhipin.com/web/geek/job"'
    if system == "Darwin":
        return (
            'open -na "Google Chrome" --args '
            + common
            + '--user-data-dir="$HOME/.boss-chrome-profile" '
            + url
        )
    if system == "Windows":
        return (
            "Start-Process chrome.exe -ArgumentList "
            "'--remote-debugging-address=127.0.0.1',"
            "'--remote-debugging-port=9222',"
            '"--user-data-dir=$env:USERPROFILE\\.boss-chrome-profile",'
            "'https://www.zhipin.com/web/geek/job'"
        )
    return (
        "google-chrome "
        + common
        + '--user-data-dir="$HOME/.boss-chrome-profile" '
        + url
    )


def _cdp_json(path: str):
    """GET the local CDP endpoint (system proxy disabled), return parsed JSON; return None on failure.

    CDP is bound to loopback (127.0.0.1) only, so a direct connection is sufficient. An empty
    ProxyHandler explicitly bypasses any configured system/global proxy — routing a localhost
    probe through a proxy is meaningless and may be blocked. This is an intentional
    localhost-only assumption and must not be overridden by the config proxy setting.
    """
    req = urllib.request.Request(f"{_CDP_URL}{path}", method="GET")
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        with opener.open(req, timeout=_CDP_TIMEOUT) as resp:
            return json.loads(resp.read())
    except Exception:
        return None


def _has_zhipin_page(pages) -> bool:
    """Return whether the CDP /json tab list contains a reusable zhipin.com tab (exact hostname check)."""
    for page in pages or []:
        if page.get("type") == "page" and host_matches(page.get("url", ""), "zhipin.com"):
            return True
    return False


_SECURITY_CHECK_MARKERS = ("security-check", "zhipin-security", "_security_check")


def _security_check_blocks_all(pages) -> bool:
    """Return whether all existing zhipin tabs are showing the anti-bot security challenge page (not the login page)."""
    zhipin_urls = [
        page.get("url", "")
        for page in (pages or [])
        if page.get("type") == "page" and host_matches(page.get("url", ""), "zhipin.com")
    ]
    if not zhipin_urls:
        return False
    return all(
        any(marker in url.lower() for marker in _SECURITY_CHECK_MARKERS)
        for url in zhipin_urls
    )


_WS_ACCEPT_GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"


def _read_ws_text_frame(sock: socket.socket, initial: bytes = b""):
    """Read the next text frame, return (payload, leftover).

    leftover is any bytes received beyond the current frame that belong to the next frame.
    The caller should pass it as the `initial` argument for the next call (a single recv
    may deliver multiple frames). Returns (None, leftover) on a close frame or disconnection.
    Ignores ping/pong.
    """
    buf = initial
    while True:
        while len(buf) < 2:
            chunk = sock.recv(4096)
            if not chunk:
                return None, buf
            buf += chunk
        opcode = buf[0] & 0x0F
        length = buf[1] & 0x7F
        header_len = 2
        if length == 126:
            while len(buf) < header_len + 2:
                chunk = sock.recv(4096)
                if not chunk:
                    return None, buf
                buf += chunk
            length = struct.unpack(">H", buf[header_len:header_len + 2])[0]
            header_len += 2
        elif length == 127:
            while len(buf) < header_len + 8:
                chunk = sock.recv(4096)
                if not chunk:
                    return None, buf
                buf += chunk
            length = struct.unpack(">Q", buf[header_len:header_len + 8])[0]
            header_len += 8
        while len(buf) < header_len + length:
            chunk = sock.recv(4096)
            if not chunk:
                return None, buf
            buf += chunk
        payload = buf[header_len:header_len + length]
        buf = buf[header_len + length:]
        if opcode == 0x8:  # close
            return None, buf
        if opcode in (0x1, 0x2, 0x0):  # text / binary / continuation
            return payload, buf
        # ping(0x9)/pong(0xA) etc: ignore, continue reading next frame


def _send_ws_text(sock: socket.socket, text: str) -> None:
    payload = text.encode("utf-8")
    mask = os.urandom(4)
    masked = bytes(b ^ mask[i % 4] for i, b in enumerate(payload))
    header = bytes([0x81])  # FIN + text
    n = len(payload)
    if n < 126:
        header += bytes([0x80 | n])
    elif n < 65536:
        header += bytes([0x80 | 126]) + struct.pack(">H", n)
    else:
        header += bytes([0x80 | 127]) + struct.pack(">Q", n)
    sock.sendall(header + mask + masked)


def _cdp_zhipin_login_cookie() -> bool | None:
    """Read-only probe for the zhipin.com login cookie (wt2) in the dedicated Chrome browser.

    True = cookie present; False = no cookie (browser not logged in, CDP search will return
    AUTH_EXPIRED); None = probe failed (CDP WebSocket unreachable etc.), login state unknown.
    Only proves the browser profile was logged in — does not validate server-side cookie validity.
    """
    version = _cdp_json("/json/version")
    ws_url = (version or {}).get("webSocketDebuggerUrl")
    if not ws_url:
        return None
    parsed = urlparse(ws_url)
    host = parsed.hostname or "127.0.0.1"
    port = parsed.port or 80
    path = parsed.path or "/"
    try:
        with socket.create_connection((host, port), timeout=_CDP_TIMEOUT) as sock:
            sock.settimeout(_CDP_TIMEOUT)
            key = base64.b64encode(os.urandom(16)).decode()
            # IPv6 literals need square brackets in the Host header (urlparse().hostname strips them)
            host_header = f"[{host}]:{port}" if ":" in host else f"{host}:{port}"
            handshake = (
                f"GET {path} HTTP/1.1\r\n"
                f"Host: {host_header}\r\n"
                "Upgrade: websocket\r\n"
                "Connection: Upgrade\r\n"
                f"Sec-WebSocket-Key: {key}\r\n"
                "Sec-WebSocket-Version: 13\r\n"
                "\r\n"
            )
            sock.sendall(handshake.encode())
            response = b""
            while b"\r\n\r\n" not in response:
                chunk = sock.recv(4096)
                if not chunk:
                    return None
                response += chunk
            head, _, rest = response.partition(b"\r\n\r\n")
            status_line = head.split(b"\r\n", 1)[0]
            # Strictly parse the status code token: accept "HTTP/1.1 101" (reason phrase may be empty), reject pseudo-codes like 1019
            if status_line.split()[1:2] != [b"101"]:
                return None
            accept = base64.b64encode(
                hashlib.sha1((key + _WS_ACCEPT_GUID).encode()).digest()
            ).decode()
            if accept not in head.decode("latin-1"):
                return None
            _send_ws_text(sock, json.dumps({"id": 1, "method": "Storage.getCookies"}))
            # Chrome may push event frames first (no id); keep reading until we get the id==1 response (with a cap to prevent infinite loops).
            # leftover carries excess bytes from the previous recv to ensure no data is lost when one recv delivers multiple frames.
            buf = rest
            for _ in range(16):
                payload, buf = _read_ws_text_frame(sock, initial=buf)
                if payload is None:
                    return None
                data = json.loads(payload.decode("utf-8"))
                if data.get("id") != 1:
                    continue  # event frames etc: skip, read the next frame
                if "result" not in data:
                    return None
                for cookie in data["result"].get("cookies", []):
                    if cookie.get("name") == "wt2" and "zhipin" in cookie.get("domain", ""):
                        return True
                return False
            return None
    except Exception:
        return None


class BossChannel(Channel):
    name = "boss"
    description = "Boss Zhipin job search and JD"
    backends = ["boss-agent-cli (CDP)"]
    tier = 2

    def can_handle(self, url: str) -> bool:
        return host_matches(url, "zhipin.com")

    def check(self, config=None):
        self.active_backend = None

        # Layer 1: is boss-agent-cli installed?
        probe = probe_command("boss", ["--version"], timeout=10)
        if probe.status == "missing":
            return "off", (
                "boss-agent-cli is not installed. Obtain user approval first, then run:\n"
                "  agent-reach install --system --channels=boss\n"
                "After installation, have the user manually log in to zhipin.com in the dedicated Chrome."
            )
        if probe.status == "broken":
            return "error", (
                "boss command exists but cannot execute — installation is broken. Reinstall:\n"
                "  agent-reach install --system --channels=boss"
            )
        if not probe.ok:
            return "warn", f"boss command probe failed ({probe.status}), please check the installation"

        # Layer 2: is the CDP port reachable?
        if _cdp_json("/json/version") is None:
            return "off", (
                "CDP debug port is not reachable. Launch the debugging Chrome first:\n"
                f"  {_chrome_launch_command()}\n"
                "  Then have the user log in to zhipin.com manually in that window.\n"
                "Bound to 127.0.0.1 only; any local process that can reach port 9222 has full control over this Chrome."
            )

        # Layer 3: are there reusable Boss tabs?
        pages = _cdp_json("/json")
        if pages is None:
            return "warn", "CDP port is reachable but /json tab enumeration failed"
        if not _has_zhipin_page(pages):
            return "warn", (
                "CDP is reachable but no existing zhipin.com tab was found (this does not mean not logged in: cookies may still be valid; "
                "boss-agent-cli will open a new tab on its own). Recommend logging in to zhipin.com in Chrome first."
            )

        # Layer 4: browser login cookie (wt2). Browser is ground truth —
        # `boss status` only validates local session.enc, which does not reflect browser login state.
        browser_cookie = _cdp_zhipin_login_cookie()
        if browser_cookie is False:
            return "warn", (
                "CDP pipeline ready, but the dedicated Chrome browser has no zhipin.com login cookie (wt2) — "
                "browser is not logged in, searches will return AUTH_EXPIRED. Note: `boss status` logged_in "
                "only represents local session.enc credentials, not browser login state. Have the user confirm login "
                "in the Chrome window (this should be done first after launching CDP Chrome), then run: "
                "`boss --cdp-url http://localhost:9222 login --cdp` to sync the login state."
            )

        cookie_note = (
            "browser login cookie (wt2) present" if browser_cookie else "browser login cookie probe failed, login state unknown"
        )

        if _security_check_blocks_all(pages):
            return "warn", (
                f"CDP pipeline ready, but all existing zhipin tabs are on the security challenge page "
                "(security-check / zhipin-security). This is a Boss anti-bot challenge, unrelated to login state — "
                "it appears even when logged in; do not ask the user to re-login based on this; "
                "just have the user solve the slider manually."
                f"Browser login state reference: {cookie_note}."
                "Do not use `boss status` to determine CDP browser login state (it only validates local session.enc)."
            )

        # All four layers passed: CDP pipeline ready, mark the active backend (base contract)
        self.active_backend = self.backends[0]
        return "warn", (
            f"CDP pipeline ready (port 9222 up + reusable zhipin tab found, {cookie_note}). "
            "Doctor does not perform actual searches, validate cookie server-side validity, or verify upstream boss-agent-cli #403-#407 API; "
            "Run `boss --cdp-url http://localhost:9222 login --cdp` first to sync the existing login state; "
            "For searching, use `boss --browser-source existing-browser --cdp-url http://localhost:9222 search ...` "
            "to ensure it stops immediately rather than degrading to headless when CDP is unavailable."
            "If search returns AUTH_EXPIRED, follow the login runbook (user logs in the dedicated window + login --cdp); "
            "do not interpret it as a security challenge."
        )
