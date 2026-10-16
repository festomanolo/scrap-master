"""Least-privilege browser-cookie extraction and URL routing regressions."""

from __future__ import annotations

import sys
from types import SimpleNamespace

import pytest

from scrap_master import cookie_extract


class RecordingConfig:
    def __init__(self):
        self.values = {}

    def set(self, key, value):
        self.values[key] = value


def test_browser_extraction_requires_an_explicit_platform():
    with pytest.raises(ValueError, match="platform"):
        cookie_extract.extract_all("chrome")








@pytest.mark.parametrize(
    ("platform", "manual_key"),
    [
        ("twitter", "twitter-cookies"),
    ],
)
def test_browser_extraction_rejects_cookie_editor_platforms(platform, manual_key):
    with pytest.raises(ValueError, match=rf"Cookie-Editor.*{manual_key}"):
        cookie_extract.extract_all("chrome", platform=platform)






def test_configure_requires_platform_before_reading_browser():
    with pytest.raises(ValueError, match="platform"):
        cookie_extract.configure_from_browser("chrome", RecordingConfig())


def test_invalid_platform_error_does_not_echo_url_secrets():
    with pytest.raises(ValueError) as error:
        cookie_extract.extract_all(
            "chrome",
            platform="https://user:pass@example.test/?access_token=secret",
        )

    message = str(error.value)
    assert "user:pass" not in message
    assert "secret" not in message
    assert "***" in message






