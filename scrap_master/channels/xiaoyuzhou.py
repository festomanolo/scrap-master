# -*- coding: utf-8 -*-
"""Xiaoyuzhou Podcast — transcribe podcasts via Groq Whisper API."""

import os

from scrap_master.config import Config
from scrap_master.probe import probe_command

from .base import Channel


class XiaoyuzhouChannel(Channel):
    name = "xiaoyuzhou"
    description = "Xiaoyuzhou Podcast transcription"
    backends = ["groq-whisper", "ffmpeg"]
    tier = 1

    def can_handle(self, url: str) -> bool:
        from scrap_master.utils.url import host_matches

        return host_matches(url, "xiaoyuzhoufm.com")

    def check(self, config=None):
        self.active_backend = None

        # Check ffmpeg — really execute it: a stale pip-installed ffmpeg shim
        # passes shutil.which() but cannot run
        probe = probe_command("ffmpeg", ["-version"], timeout=10, package="ffmpeg")
        if probe.status == "missing":
            return "off", (
                "ffmpeg is required (audio transcoding and segmentation). Install:\n"
                "  Ubuntu/Debian: apt install -y ffmpeg\n"
                "  macOS: brew install ffmpeg"
            )
        if not probe.ok:
            return "error", (
                "ffmpeg cannot execute. Reinstall: brew install ffmpeg (macOS) / apt install ffmpeg (Linux)"
            )

        # Check script exists
        script = os.path.expanduser("~/.scrap-master/tools/xiaoyuzhou/transcribe.sh")
        if not os.path.isfile(script):
            return "off", (
                "Transcription script not installed. Run:\n"
                "  scrap-master install --env=auto --system --channels=xiaoyuzhou\n"
                "  or manually copy transcribe.sh to ~/.scrap-master/tools/xiaoyuzhou/"
            )

        # Check GROQ_API_KEY — prefer env var, fall back to Scrap Master config
        has_key = bool(os.environ.get("GROQ_API_KEY"))
        if not has_key:
            try:
                cfg = config if config is not None else Config()
                has_key = bool(cfg.get("groq_api_key"))
            except Exception:
                has_key = False
        if not has_key:
            return "warn", (
                "Groq API key is required (free). Steps:\n"
                "  1. Sign up at https://console.groq.com\n"
                "  2. Run: scrap-master configure groq-key (hidden input)"
            )

        self.active_backend = "groq-whisper"
        return "ok", "Fully available (podcast download + Whisper transcription)"
