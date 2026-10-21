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


class ExtractError(ValueError):
    pass


def parse_fields(spec: str) -> Dict[str, str]:
    """Parse "name, price:number, tags:list" (or a JSON object / JSON Schema) into {field: type}."""
    spec = (spec or "").strip()
    if not spec:
        raise ExtractError("no fields given")
    if spec.startswith("{"):
        data = json.loads(spec)
        props = data.get("properties", data)
        return {k: _norm_type(v.get("type", "string") if isinstance(v, dict) else v)
                for k, v in props.items()}
    fields: Dict[str, str] = {}
    for part in re.split(r"[,\n]", spec):
        part = part.strip()
        if not part:
            continue
        name, _, typ = part.partition(":")
        name = name.strip()
        if not re.fullmatch(r"[A-Za-z_][\w ]*", name):
            raise ExtractError(f"bad field name: {name!r}")
        fields[name.replace(" ", "_")] = _norm_type(typ.strip() or "string")
    return fields
