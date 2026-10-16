"""Doctor must not trigger upstream browser-cookie refresh or persistence."""

from __future__ import annotations

import json
import subprocess
import time

from scrap_master.channels.reddit import RedditChannel
from scrap_master.channels.twitter import TwitterChannel


def _forbid_subprocess(*_args, **_kwargs):
    raise AssertionError("credential-backed health checks must not execute upstream CLIs")


def test_twitter_doctor_does_not_start_cli_without_explicit_credentials(
    monkeypatch,
):
    monkeypatch.delenv("TWITTER_AUTH_TOKEN", raising=False)
    monkeypatch.delenv("TWITTER_CT0", raising=False)
    monkeypatch.setattr(
        "shutil.which",
        lambda name: "/usr/local/bin/twitter" if name == "twitter" else None,
    )
    monkeypatch.setattr(subprocess, "run", _forbid_subprocess)

    channel = TwitterChannel()
    status, message = channel.check()

    assert status == "warn"
    assert channel.active_backend is None
    assert "Cookie-Editor" in message
    assert "browser" not in message.lower() or "does not" in message.lower()


def test_twitter_doctor_still_avoids_upstream_fallback_with_saved_credentials(
    monkeypatch,
):
    class Config:
        def get(self, key, default=None):
            return {
                "twitter_auth_token": "explicit-auth",
                "twitter_ct0": "explicit-ct0",
            }.get(key, default)

    monkeypatch.setattr(
        "shutil.which",
        lambda name: "/usr/local/bin/twitter" if name == "twitter" else None,
    )
    monkeypatch.setattr(subprocess, "run", _forbid_subprocess)

    status, message = TwitterChannel().check(Config())

    assert status == "warn"
    assert "configured" in message
    assert "will not run" in message


def test_reddit_doctor_does_not_create_or_refresh_missing_credentials(
    isolated_home, monkeypatch
):
    monkeypatch.setattr(
        "shutil.which",
        lambda name: "/usr/local/bin/rdt" if name == "rdt" else None,
    )
    monkeypatch.setattr(subprocess, "run", _forbid_subprocess)

    channel = RedditChannel()
    status, message = channel.check()

    assert status == "warn"
    assert channel.active_backend is None
    assert "Cookie-Editor" in message
    assert not (isolated_home / ".config" / "rdt-cli").exists()


def test_reddit_doctor_reports_stale_saved_credential_without_refresh(
    isolated_home, monkeypatch
):
    credential_path = (
        isolated_home / ".config" / "rdt-cli" / "credential.json"
    )
    credential_path.parent.mkdir(parents=True)
    credential_path.write_text(
        json.dumps(
            {
                "cookies": {"reddit_session": "explicit-cookie"},
                "saved_at": time.time() - 8 * 86400,
            }
        ),
        encoding="utf-8",
    )
    original = credential_path.read_bytes()
    monkeypatch.setattr(
        "shutil.which",
        lambda name: "/usr/local/bin/rdt" if name == "rdt" else None,
    )
    monkeypatch.setattr(subprocess, "run", _forbid_subprocess)

    status, message = RedditChannel().check()

    assert status == "warn"
    assert "over 7 days old" in message
    assert credential_path.read_bytes() == original




