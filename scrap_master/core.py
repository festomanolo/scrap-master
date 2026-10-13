# -*- coding: utf-8 -*-
"""
ScrapMaster — installer, doctor, and configuration tool.

Scrap Master helps AI agents install and configure upstream platform tools
(twitter-cli, yt-dlp, mcporter, gh CLI, etc.). After installation, agents
call the upstream tools directly — no wrapper layer needed.

Usage:
    from scrap_master.doctor import check_all, format_report
    from scrap_master.config import Config

    config = Config()
    results = check_all(config)
    print(format_report(results))
"""

from typing import Dict, Optional

from scrap_master.config import Config


class ScrapMaster:
    """One toolkit to read, search and scrape data from the entire internet.

    This class provides health-check functionality.
    For reading/searching, use the upstream tools directly
    (see SKILL.md for commands).
    """

    def __init__(self, config: Optional[Config] = None):
        self.config = config or Config()

    def doctor(self) -> Dict[str, dict]:
        """Check all channel availability."""
        from scrap_master.doctor import check_all
        return check_all(self.config)

    def doctor_report(self) -> str:
        """Get formatted health report."""
        from scrap_master.doctor import check_all, format_report
        return format_report(check_all(self.config))
