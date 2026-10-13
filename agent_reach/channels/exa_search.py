# -*- coding: utf-8 -*-
"""Exa Search — check if mcporter + Exa MCP is available."""

import shutil

from .base import Channel
from .mcporter import McporterConfigError, inspect_mcporter_config


class ExaSearchChannel(Channel):
    name = "exa_search"
    description = "Web semantic search"
    backends = ["Exa via mcporter"]
    tier = 0

    def can_handle(self, url: str) -> bool:
        return False  # Search-only channel

    def check(self, config=None):
        self.active_backend = None
        if not shutil.which("mcporter"):
            return "off", (
                "Requires mcporter + Exa MCP. Install:\n"
                "  npm install -g mcporter\n"
                "  mcporter config add exa https://mcp.exa.ai/mcp --scope home"
            )
        try:
            inspection = inspect_mcporter_config()
        except McporterConfigError as exc:
            return "error", f"mcporter config check failed: {exc}"
        if "exa" in inspection.server_names:
            return "warn", (
                "Exa is configured in mcporter, but Doctor has not started the remote service to "
                "verify connectivity — cannot claim availability based on config alone."
            )
        if inspection.imports_unchecked:
            return "warn", (
                "Exa not found in local mcporter config; config also has editor imports enabled. "
                "Doctor did not expand them to avoid broadening credential access — not verified."
            )
        return "off", (
            "mcporter is installed but Exa is not configured. Run:\n"
            "  mcporter config add exa https://mcp.exa.ai/mcp --scope home"
        )
