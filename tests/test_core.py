# -*- coding: utf-8 -*-
"""Tests for ScrapMaster core class."""

import pytest

from scrap_master.config import Config
from scrap_master.core import ScrapMaster


@pytest.fixture
def eyes(tmp_path):
    config = Config(config_path=tmp_path / "config.yaml")
    return ScrapMaster(config=config)


class TestScrapMaster:
    def test_init(self, eyes):
        assert eyes.config is not None

    def test_doctor(self, eyes):
        results = eyes.doctor()
        assert isinstance(results, dict)
        assert "web" in results
        assert "github" in results

    def test_doctor_report(self, eyes):
        report = eyes.doctor_report()
        assert isinstance(report, str)
        assert "Scrap Master" in report
