# -*- coding: utf-8 -*-
"""Tests for channel registry basics and health checks."""

import json
import shutil
import subprocess
from urllib.error import URLError

import pytest

from scrap_master.backends import OpenCLIStatus
from scrap_master.channels import get_all_channels, get_channel
from scrap_master.channels.facebook import FacebookChannel
from scrap_master.channels.instagram import InstagramChannel


class TestChannelRegistry:
    def test_get_channel_by_name(self):
        ch = get_channel("github")
        assert ch is not None
        assert ch.name == "github"

    def test_get_unknown_channel_returns_none(self):
        assert get_channel("not-exists") is None



class TestOpenCLISiteChannels:
    def test_facebook_can_handle_common_urls(self):
        ch = FacebookChannel()
        assert ch.can_handle("https://www.facebook.com/zuck")
        assert ch.can_handle("https://m.facebook.com/groups/123")
        assert ch.can_handle("https://fb.com/some-page")
        assert ch.can_handle("https://fb.watch/abc123")
        assert not ch.can_handle("https://instagram.com/openai")

    def test_instagram_can_handle_common_urls(self):
        ch = InstagramChannel()
        assert ch.can_handle("https://www.instagram.com/openai/")
        assert ch.can_handle("https://instagram.com/p/abc123/")
        assert ch.can_handle("https://instagr.am/p/abc123/")
        assert not ch.can_handle("https://facebook.com/openai")

    def test_opencli_bridge_ready_is_unverified_for_login_platform(
        self, monkeypatch
    ):
        monkeypatch.setattr(
            "scrap_master.backends.opencli_status",
            lambda: OpenCLIStatus(
                installed=True,
                extension_connected=True,
                version="1.8.3",
            ),
        )
        ch = FacebookChannel()
        status, msg = ch.check()
        assert status == "warn"
        assert ch.active_backend is None
        assert "OpenCLI bridge connected" in msg
        assert "login state and actual commands are not verified in real time" in msg
        assert "facebook.com" in msg

        instagram = InstagramChannel()
        status, msg = instagram.check()
        assert status == "warn"
        assert instagram.active_backend is None
        assert "OpenCLI bridge connected" in msg
        assert "instagram.com" in msg

    def test_opencli_missing_reports_off(self, monkeypatch):
        monkeypatch.setattr(
            "scrap_master.backends.opencli_status",
            lambda: OpenCLIStatus(installed=False),
        )
        ch = InstagramChannel()
        status, msg = ch.check()
        assert status == "off"
        assert ch.active_backend is None
        assert "scrap-master install --system --channels opencli" in msg
        assert "instagram.com" in msg

    def test_opencli_installed_without_extension_reports_warn(self, monkeypatch):
        monkeypatch.setattr(
            "scrap_master.backends.opencli_status",
            lambda: OpenCLIStatus(
                installed=True,
                hint="OpenCLI is installed, but the Chrome extension is not installed.",
            ),
        )
        ch = InstagramChannel()
        status, msg = ch.check()
        assert status == "warn"
        assert ch.active_backend is None
        assert "Chrome extension" in msg






class TestRedditChannel:
    """Multiple backends: OpenCLI > rdt-cli, with no zero-config path."""

    @staticmethod
    def _isolate(monkeypatch, opencli=None):
        """Isolate the OpenCLI candidate (None = not installed) to focus on the rdt-cli path."""
        from scrap_master.channels.reddit import RedditChannel
        monkeypatch.setattr(RedditChannel, "_check_opencli", lambda self: opencli)

    def test_reports_off_when_nothing_installed(self, monkeypatch):
        self._isolate(monkeypatch)
        monkeypatch.setattr(shutil, "which", lambda _: None)
        from scrap_master.channels.reddit import RedditChannel
        status, msg = RedditChannel().check()
        assert status == "off"
        # Honest wording: state there is no zero-config path, recommend OpenCLI + the rdt git source
        assert "no zero-config path" in msg
        assert "opencli" in msg
        assert "git+https://github.com/public-clis/rdt-cli.git" in msg

    def test_opencli_ready_wins(self, monkeypatch):
        self._isolate(monkeypatch, opencli=("ok", "OpenCLI available (reuses the browser login session)"))
        monkeypatch.setattr(shutil, "which", lambda _: None)
        from scrap_master.channels.reddit import RedditChannel
        ch = RedditChannel()
        status, msg = ch.check()
        assert status == "ok"
        assert ch.active_backend == "OpenCLI"

    def test_saved_rdt_cookie_is_unverified_not_active(
        self, monkeypatch, isolated_home
    ):
        self._isolate(monkeypatch)
        monkeypatch.setattr(shutil, "which", lambda _: "/usr/local/bin/rdt")
        credential_path = (
            isolated_home / ".config" / "rdt-cli" / "credential.json"
        )
        credential_path.parent.mkdir(parents=True)
        credential_path.write_text(
            json.dumps(
                {
                    "cookies": {"reddit_session": "explicit"},
                    "saved_at": __import__("time").time(),
                }
            ),
            encoding="utf-8",
        )
        monkeypatch.setattr(
            subprocess,
            "run",
            lambda *_args, **_kwargs: pytest.fail(
                "Doctor must not execute rdt status"
            ),
        )
        from scrap_master.channels.reddit import RedditChannel
        ch = RedditChannel()
        status, msg = ch.check()
        assert status == "warn"
        assert "not verified in real time" in msg
        assert ch.active_backend is None

    def test_reports_warn_when_cookie_is_missing(self, monkeypatch):
        self._isolate(monkeypatch)
        monkeypatch.setattr(shutil, "which", lambda _: "/usr/local/bin/rdt")
        from scrap_master.channels.reddit import RedditChannel
        ch = RedditChannel()
        status, msg = ch.check()
        assert status == "warn"
        assert "Cookie-Editor" in msg
        assert "chromewebstore.google.com" in msg
        assert ch.active_backend is None







class TestYouTubeChannel:
    def test_reports_error_with_reinstall_hint_when_broken(self, monkeypatch):
        """yt-dlp found by which but exec raises FileNotFoundError -> error + reinstall prescription."""
        monkeypatch.setattr(shutil, "which", lambda _: "/usr/local/bin/yt-dlp")

        def fake_run(cmd, **kwargs):
            raise FileNotFoundError(cmd[0])

        monkeypatch.setattr(subprocess, "run", fake_run)
        from scrap_master.channels.youtube import YouTubeChannel
        ch = YouTubeChannel()
        status, msg = ch.check()
        assert status == "error"
        assert "cannot execute" in msg
        assert "uv tool install --force yt-dlp" in msg
        assert ch.active_backend is None


class TestGitHubChannel:
    def test_reports_error_with_reinstall_hint_when_broken(self, monkeypatch):
        """When gh --version is broken, give a binary reinstall prescription."""
        monkeypatch.setattr(shutil, "which", lambda _: "/usr/local/bin/gh")

        def fake_run(cmd, **kwargs):
            assert cmd[-1:] == ["--version"]
            raise FileNotFoundError(cmd[0])

        monkeypatch.setattr(subprocess, "run", fake_run)
        from scrap_master.channels.github import GitHubChannel
        ch = GitHubChannel()
        status, msg = ch.check()
        assert status == "error"
        assert "cannot execute" in msg
        assert "brew reinstall gh" in msg
        assert ch.active_backend is None

    def test_explicit_auth_is_unverified_and_never_marked_active(
        self, monkeypatch
    ):
        monkeypatch.setattr(shutil, "which", lambda _: "/usr/local/bin/gh")
        monkeypatch.setenv("GH_TOKEN", "configured-secret")

        def fake_run(cmd, **kwargs):
            assert cmd[-1:] == ["--version"]
            assert "auth" not in cmd
            assert kwargs["env"]["GH_TELEMETRY"] == "false"
            assert kwargs["env"]["DO_NOT_TRACK"] == "true"
            return subprocess.CompletedProcess(cmd, 0, "gh version 2.92.0", "")

        monkeypatch.setattr(subprocess, "run", fake_run)
        from scrap_master.channels.github import GitHubChannel
        ch = GitHubChannel()
        status, msg = ch.check()
        assert status == "warn"
        assert "explicit authentication config" in msg
        assert "configured-secret" not in msg
        assert ch.active_backend is None

    def test_no_auth_metadata_remains_warn_and_inactive(
        self, monkeypatch, tmp_path
    ):
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(shutil, "which", lambda _: "/usr/local/bin/gh")
        monkeypatch.delenv("GH_TOKEN", raising=False)
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)

        def fake_run(cmd, **kwargs):
            assert cmd[-1:] == ["--version"]
            assert "auth" not in cmd
            return subprocess.CompletedProcess(cmd, 0, "gh version 2.92.0", "")

        monkeypatch.setattr(subprocess, "run", fake_run)
        from scrap_master.channels.github import GitHubChannel
        ch = GitHubChannel()
        status, msg = ch.check()
        assert status == "warn"
        assert "gh auth login" in msg
        assert ch.active_backend is None

    def test_hosts_metadata_is_read_without_exposing_token(
        self, monkeypatch, isolated_home
    ):
        monkeypatch.setattr(shutil, "which", lambda _: "/usr/local/bin/gh")
        monkeypatch.delenv("GH_TOKEN", raising=False)
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        hosts = isolated_home / ".config" / "gh" / "hosts.yml"
        hosts.parent.mkdir(parents=True)
        hosts.write_text(
            "github.com:\n"
            "  user: alice\n"
            "  oauth_token: super-secret-token\n",
            encoding="utf-8",
        )
        monkeypatch.setattr(
            subprocess,
            "run",
            lambda cmd, **kwargs: subprocess.CompletedProcess(
                cmd, 0, "gh version 2.92.0", ""
            ),
        )

        from scrap_master.channels.github import GitHubChannel

        status, message = GitHubChannel().check()

        assert status == "warn"
        assert "explicit authentication config" in message
        assert "alice" not in message
        assert "super-secret-token" not in message

    def test_hosts_metadata_refuses_ancestor_symlink(
        self, monkeypatch, isolated_home
    ):
        monkeypatch.setattr(shutil, "which", lambda _: "/usr/local/bin/gh")
        monkeypatch.delenv("GH_TOKEN", raising=False)
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        real_config = isolated_home / "real-config"
        hosts = real_config / "gh" / "hosts.yml"
        hosts.parent.mkdir(parents=True)
        hosts.write_text(
            "github.com:\n  oauth_token: do-not-read\n",
            encoding="utf-8",
        )
        (isolated_home / ".config").symlink_to(
            real_config,
            target_is_directory=True,
        )
        monkeypatch.setattr(
            subprocess,
            "run",
            lambda cmd, **kwargs: subprocess.CompletedProcess(
                cmd, 0, "gh version 2.92.0", ""
            ),
        )

        from scrap_master.channels.github import GitHubChannel

        channel = GitHubChannel()
        status, message = channel.check()

        assert status == "warn"
        assert "cannot be confirmed safely" in message
        assert "do-not-read" not in message
        assert channel.active_backend is None


class TestLinkedInChannel:
    def test_setup_hint_uses_current_stdio_contract(self, monkeypatch):
        monkeypatch.setattr(shutil, "which", lambda _: None)

        from scrap_master.channels.linkedin import LinkedInChannel

        channel = LinkedInChannel()
        status, message = channel.check()

        assert status == "off"
        assert channel.backends[0] == "mcp-server-linkedin"
        assert "docs.astral.sh/uv/getting-started/installation" in message
        assert "uvx mcp-server-linkedin@latest --login" in message
        assert (
            "mcporter config add linkedin --command uvx "
            "--arg mcp-server-linkedin@latest --env UV_HTTP_TIMEOUT=300 "
            "--scope home"
        ) in message
        assert "pip install linkedin-scraper-mcp" not in message
        assert "localhost:3000/mcp" not in message

    def test_configured_linkedin_warns_when_uvx_is_missing(
        self, monkeypatch, tmp_path
    ):
        monkeypatch.chdir(tmp_path)
        config_path = tmp_path / "config" / "mcporter.json"
        config_path.parent.mkdir()
        config_path.write_text(
            json.dumps(
                {
                    "mcpServers": {
                        "linkedin": {
                            "command": "uvx",
                            "args": ["mcp-server-linkedin@latest"],
                        }
                    },
                    "imports": [],
                }
            ),
            encoding="utf-8",
        )
        monkeypatch.setattr(
            shutil,
            "which",
            lambda name: "/usr/local/bin/mcporter"
            if name == "mcporter"
            else None,
        )

        from scrap_master.channels.linkedin import LinkedInChannel

        status, message = LinkedInChannel().check()

        assert status == "warn"
        assert "uvx is not installed" in message
        assert "docs.astral.sh/uv/getting-started/installation" in message

    def test_mcporter_is_never_executed(
        self, monkeypatch, tmp_path
    ):
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(shutil, "which", lambda _: "/usr/local/bin/mcporter")
        monkeypatch.setattr(
            subprocess,
            "run",
            lambda *_args, **_kwargs: pytest.fail(
                "Doctor must not execute mcporter"
            ),
        )
        from scrap_master.channels.linkedin import LinkedInChannel
        ch = LinkedInChannel()
        status, msg = ch.check()
        assert status == "off"
        assert ch.active_backend is None

    @pytest.mark.parametrize(
        "server_name",
        [
            "linkedin",
            "linkedin-scraper",
            "linkedin-scraper-mcp",
            "mcp-server-linkedin",
        ],
    )
    def test_configured_linkedin_name_is_not_false_positive_active(
        self, monkeypatch, tmp_path, server_name
    ):
        monkeypatch.chdir(tmp_path)
        config_path = tmp_path / "config" / "mcporter.json"
        config_path.parent.mkdir()
        config_path.write_text(
            json.dumps(
                {
                    "mcpServers": {
                        server_name: {"command": "linkedin-mcp"}
                    },
                    "imports": [],
                }
            ),
            encoding="utf-8",
        )
        monkeypatch.setattr(shutil, "which", lambda _: "/usr/local/bin/mcporter")
        monkeypatch.setattr(
            subprocess,
            "run",
            lambda *_args, **_kwargs: pytest.fail(
                "Doctor must not execute mcporter"
            ),
        )
        from scrap_master.channels.linkedin import LinkedInChannel
        ch = LinkedInChannel()
        status, msg = ch.check()
        assert status == "warn"
        assert "has not started" in msg
        assert ch.active_backend is None

    def test_config_metadata_containing_linkedin_is_not_a_backend(
        self, monkeypatch, tmp_path
    ):
        monkeypatch.chdir(tmp_path)
        config_path = tmp_path / "config" / "mcporter.json"
        config_path.parent.mkdir()
        config_path.write_text(
            json.dumps(
                {
                    "mcpServers": {
                        "unrelated": {
                            "baseUrl": "http://linkedin-project.test/mcp"
                        }
                    },
                    "imports": [],
                }
            ),
            encoding="utf-8",
        )
        monkeypatch.setattr(shutil, "which", lambda _: "/usr/local/bin/mcporter")
        from scrap_master.channels.linkedin import LinkedInChannel

        ch = LinkedInChannel()
        status, _ = ch.check()
        assert status == "off"
        assert ch.active_backend is None

    def test_off_without_backend_when_linkedin_not_configured(
        self, monkeypatch, tmp_path
    ):
        monkeypatch.chdir(tmp_path)
        config_path = tmp_path / "config" / "mcporter.json"
        config_path.parent.mkdir()
        config_path.write_text(
            json.dumps(
                {
                    "mcpServers": {"exa": {"baseUrl": "https://example.test"}},
                    "imports": [],
                }
            ),
            encoding="utf-8",
        )
        monkeypatch.setattr(shutil, "which", lambda _: "/usr/local/bin/mcporter")
        from scrap_master.channels.linkedin import LinkedInChannel
        ch = LinkedInChannel()
        status, msg = ch.check()
        assert status == "off"
        assert ch.active_backend is None


class TestExaSearchChannel:
    def test_mcporter_is_never_executed(self, monkeypatch, tmp_path):
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(shutil, "which", lambda _: "/usr/local/bin/mcporter")
        monkeypatch.setattr(
            subprocess,
            "run",
            lambda *_args, **_kwargs: pytest.fail(
                "Doctor must not execute mcporter"
            ),
        )
        from scrap_master.channels.exa_search import ExaSearchChannel
        ch = ExaSearchChannel()
        status, msg = ch.check()
        assert status == "off"
        assert ch.active_backend is None

    def test_configured_exa_is_not_false_positive_active(
        self, monkeypatch, tmp_path
    ):
        monkeypatch.chdir(tmp_path)
        config_path = tmp_path / "config" / "mcporter.json"
        config_path.parent.mkdir()
        config_path.write_text(
            json.dumps(
                {
                    "mcpServers": {
                        "exa": {"baseUrl": "https://mcp.example.test"}
                    },
                    "imports": [],
                }
            ),
            encoding="utf-8",
        )
        monkeypatch.setattr(shutil, "which", lambda _: "/usr/local/bin/mcporter")
        from scrap_master.channels.exa_search import ExaSearchChannel
        ch = ExaSearchChannel()
        status, msg = ch.check()
        assert status == "warn"
        assert "has not started" in msg
        assert ch.active_backend is None

    def test_config_metadata_containing_exa_is_not_a_backend(
        self, monkeypatch, tmp_path
    ):
        monkeypatch.chdir(tmp_path)
        config_path = tmp_path / "config" / "mcporter.json"
        config_path.parent.mkdir()
        config_path.write_text(
            json.dumps(
                {
                    "mcpServers": {
                        "unrelated": {
                            "baseUrl": "https://example.test/exa-project"
                        }
                    },
                    "imports": [],
                }
            ),
            encoding="utf-8",
        )
        monkeypatch.setattr(shutil, "which", lambda _: "/usr/local/bin/mcporter")
        from scrap_master.channels.exa_search import ExaSearchChannel

        ch = ExaSearchChannel()
        status, _ = ch.check()
        assert status == "off"
        assert ch.active_backend is None

    def test_invalid_mcporter_json_is_reported_as_error_not_unconfigured(
        self, monkeypatch, tmp_path
    ):
        monkeypatch.chdir(tmp_path)
        config_path = tmp_path / "config" / "mcporter.json"
        config_path.parent.mkdir()
        config_path.write_text("not-json", encoding="utf-8")
        monkeypatch.setattr(shutil, "which", lambda _: "/usr/local/bin/mcporter")
        monkeypatch.setattr(
            subprocess,
            "run",
            lambda *_args, **_kwargs: pytest.fail(
                "Doctor must not execute mcporter"
            ),
        )
        from scrap_master.channels.exa_search import ExaSearchChannel

        ch = ExaSearchChannel()
        status, message = ch.check()
        assert status == "error"
        assert "JSON" in message
        assert ch.active_backend is None




class TestRSSChannel:
    """can_handle URL patterns + the three check() branches (ok / off / error)."""

    def test_can_handle_feed_urls(self):
        from scrap_master.channels.rss import RSSChannel
        ch = RSSChannel()
        assert ch.can_handle("https://example.com/feed")
        assert ch.can_handle("https://example.com/rss")
        assert ch.can_handle("https://example.com/feed.xml")
        assert ch.can_handle("https://blog.example.com/atom.xml")
        assert ch.can_handle("https://example.com/index.atom")

    def test_can_handle_is_case_insensitive(self):
        from scrap_master.channels.rss import RSSChannel
        ch = RSSChannel()
        assert ch.can_handle("https://example.com/FEED")
        assert ch.can_handle("https://example.com/Atom.XML")


    def test_check_ok_when_feedparser_importable(self, monkeypatch):
        import sys
        import types

        monkeypatch.setitem(sys.modules, "feedparser", types.ModuleType("feedparser"))
        from scrap_master.channels.rss import RSSChannel
        ch = RSSChannel()
        status, msg = ch.check()
        assert status == "ok"
        assert ch.active_backend == "feedparser"

    def test_check_off_when_feedparser_missing(self, monkeypatch):
        """feedparser not installed → off + pip install prescription."""
        import sys

        # None in sys.modules makes `import feedparser` raise ImportError
        monkeypatch.setitem(sys.modules, "feedparser", None)
        from scrap_master.channels.rss import RSSChannel
        ch = RSSChannel()
        status, msg = ch.check()
        assert status == "off"
        assert "pip install feedparser" in msg
        assert ch.active_backend is None

    def test_check_error_when_import_crashes(self, monkeypatch):
        """Installed but crashes at import time (half-broken install) → error + reinstall prescription."""
        import builtins

        real_import = builtins.__import__

        def crashing_import(name, *args, **kwargs):
            if name == "feedparser":
                raise RuntimeError("broken install")
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", crashing_import)
        from scrap_master.channels.rss import RSSChannel
        ch = RSSChannel()
        status, msg = ch.check()
        assert status == "error"
        assert "--force-reinstall" in msg
        assert ch.active_backend is None

    def test_check_failure_resets_stale_active_backend(self, monkeypatch):
        """A previously healthy instance must not keep a stale active_backend."""
        import sys

        from scrap_master.channels.rss import RSSChannel
        ch = RSSChannel()
        ch.active_backend = "feedparser"  # pretend an earlier check() succeeded
        monkeypatch.setitem(sys.modules, "feedparser", None)
        status, _ = ch.check()
        assert status == "off"
        assert ch.active_backend is None
