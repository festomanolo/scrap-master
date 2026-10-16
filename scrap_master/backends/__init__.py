# -*- coding: utf-8 -*-
"""Cross-channel backends.

A backend here is an upstream runtime that serves MULTIPLE channels
(e.g. OpenCLI covers reddit/twitter/facebook through one
browser session), as opposed to the per-platform tools probed inside
each channel file.
"""

from .opencli import (  # noqa: F401
    OPENCLI_EXTENSION_URL,
    OPENCLI_PACKAGE,
    OpenCLIStatus,
    opencli_status,
    opencli_summary,
)
