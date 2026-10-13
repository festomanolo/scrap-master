# -*- coding: utf-8 -*-
"""Shared channel helper for OpenCLI browser-session-only platforms."""

from scrap_master.utils.url import host_matches

from .base import Channel


class OpenCLISiteChannel(Channel):
    """A platform served directly by OpenCLI.

    These channels are intentionally thin: Scrap Master only installs,
    health-checks, and routes. Agents call `opencli <site> ...` directly.
    """

    site: str = ""
    domains: tuple[str, ...] = ()
    usage: str = ""
    login_hint: str = ""

    backends = ["OpenCLI"]
    tier = 1

    def can_handle(self, url: str) -> bool:
        return host_matches(url, *self.domains)

    def check(self, config=None):
        from scrap_master.backends import opencli_status

        self.active_backend = None
        st = opencli_status()
        if not st.installed:
            return "off", (
                f"No backend installed for {self.description}. Install:\n"
                "  scrap-master install --system --channels opencli\n"
                f"Then log in to {self.login_hint} in Chrome"
            )
        if st.broken:
            return "error", st.hint

        if st.ready:
            return "warn", (
                f"OpenCLI bridge connected, but {self.description} login state and actual commands "
                "are not verified in real time; Doctor does not run platform commands, so "
                f"this is not marked as available. Log in to {self.login_hint} in Chrome first."
            )
        return "warn", st.hint
