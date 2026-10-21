# -*- coding: utf-8 -*-
"""Structured extraction — describe the fields you want, get validated records back.

    scrap-master extract https://shop.example/list --fields "name, price:number, tags:list"

Pages are read with the web channel, sent to the configured LLM in chunks, and every
record is checked against the field spec. Bad replies are retried with the errors fed back.
"""

import csv
import json
import re
from pathlib import Path
from typing import Callable, Dict, Iterable, List, Optional, Tuple

from scrap_master import ai

TYPES = ("string", "number", "integer", "boolean", "list", "url")
_ALIASES = {"str": "string", "text": "string", "float": "number", "int": "integer",
            "bool": "boolean", "array": "list", "link": "url"}
CHUNK_CHARS = 12000
MAX_CHUNKS = 8
