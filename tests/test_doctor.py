# -*- coding: utf-8 -*-
"""Tests for doctor module."""

import hashlib
import json
import os
import shutil
import subprocess
from argparse import Namespace
from pathlib import Path

import pytest

import scrap_master.doctor as doctor
from scrap_master.config import Config


class _StubChannel:
    def __init__(self, name, description, tier, status, message, backends=None,
                 active_backend=None):
        self.name = name
        self.description = description
        self.tier = tier
        self._status = status
        self._message = message
        self.backends = backends or []
        self.active_backend = active_backend

    def check(self, config=None):
        return self._status, self._message


@pytest.fixture
def tmp_config(tmp_path):
    return Config(config_path=tmp_path / "config.yaml")


class TestDoctor:
    def test_check_all_collects_channel_results(self, tmp_config, monkeypatch):
        monkeypatch.setattr(
            doctor,
            "get_all_channels",
            lambda: [
                _StubChannel("web", "Web", 0, "ok", "Web pages can be fetched", ["requests"],
                             active_backend="requests"),
                _StubChannel("github", "GitHub", 0, "warn", "gh not installed", ["gh"]),
                _StubChannel("exa_search", "Web semantic search", 1, "off", "mcporter not configured", ["Exa"]),
            ],
        )

        results = doctor.check_all(tmp_config)

        assert results == {
            "web": {
                "status": "ok",
                "name": "Web",
                "message": "Web pages can be fetched",
                "tier": 0,
                "backends": ["requests"],
                "active_backend": "requests",
            },
            "github": {
                "status": "warn",
                "name": "GitHub",
                "message": "gh not installed",
                "tier": 0,
                "backends": ["gh"],
                "active_backend": None,
            },
            "exa_search": {
                "status": "off",
                "name": "Web semantic search",
                "message": "mcporter not configured",
                "tier": 1,
                "backends": ["Exa"],
                "active_backend": None,
            },
        }



def test_stale_active_backend_does_not_leak_into_errored_result(monkeypatch):
    """The previous run's active_backend on a channel singleton must not leak into this run's error result."""
    from scrap_master import doctor

    class _ExplodingChannel:
        name = "boom"
        description = "Exploding channel"
        tier = 0
        backends = ["a", "b"]
        active_backend = "a"  # leftover from the previous successful run

        def check(self, config=None):
            raise RuntimeError("boom")

    monkeypatch.setattr(doctor, "get_all_channels", lambda: [_ExplodingChannel()])
    results = doctor.check_all(config=None)
    assert results["boom"]["status"] == "error"
    assert results["boom"]["active_backend"] is None


def test_channel_exception_credentials_are_scrubbed(monkeypatch):
    """Doctor is the final trust boundary for unexpected channel errors."""

    class _ExplodingChannel:
        name = "secret"
        description = "Sensitive channel"
        tier = 0
        backends = ["secret-backend"]
        active_backend = None

        def check(self, config=None):
            raise RuntimeError(
                "request https://alice:password@example.test/data"
                "?access_token=top-secret failed"
            )

    monkeypatch.setattr(doctor, "get_all_channels", lambda: [_ExplodingChannel()])

    message = doctor.check_all(config=None)["secret"]["message"]

    assert "alice" not in message
    assert "password" not in message
    assert "top-secret" not in message
    assert "https://***@example.test/data?access_token=***" in message


def test_channel_success_message_credentials_are_scrubbed(monkeypatch):
    """Expected channel messages must pass through the same trust boundary."""
    channel = _StubChannel(
        "configured",
        "Configured channel",
        0,
        "warn",
        (
            "upstream returned https://alice:password@example.test/data"
            "?api_key=top-secret"
        ),
        ["upstream"],
    )
    monkeypatch.setattr(doctor, "get_all_channels", lambda: [channel])

    message = doctor.check_all(config=None)["configured"]["message"]

    assert "alice" not in message
    assert "password" not in message
    assert "top-secret" not in message
    assert "https://***@example.test/data?api_key=***" in message


def _snapshot_user_roots() -> tuple:
    entries = []
    seen = set()
    for variable in (
        "HOME",
        "USERPROFILE",
        "XDG_CONFIG_HOME",
        "APPDATA",
        "LOCALAPPDATA",
    ):
        root = Path(os.environ[variable])
        if root in seen:
            continue
        seen.add(root)
        if not root.exists():
            entries.append((variable, ".", "missing"))
            continue
        for path in sorted(root.rglob("*")):
            relative = path.relative_to(root).as_posix()
            if path.is_symlink():
                detail = ("symlink", os.readlink(path))
            elif path.is_dir():
                detail = ("directory", path.stat().st_mode & 0o777)
            elif path.is_file():
                detail = (
                    "file",
                    path.stat().st_mode & 0o777,
                    hashlib.sha256(path.read_bytes()).hexdigest(),
                )
            else:
                detail = ("other",)
            entries.append((variable, relative, detail))
    return tuple(entries)


