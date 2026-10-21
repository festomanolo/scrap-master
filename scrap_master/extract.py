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


def load_fields(spec: str) -> Dict[str, str]:
    """Like parse_fields, but also accepts a path to a .json schema file."""
    path = Path(spec).expanduser()
    if spec.endswith(".json") and path.is_file():
        return parse_fields(path.read_text(encoding="utf-8"))
    return parse_fields(spec)


def _norm_type(typ: str) -> str:
    typ = str(typ).lower().strip()
    typ = _ALIASES.get(typ, typ)
    if typ not in TYPES:
        raise ExtractError(f"unknown type {typ!r} (use one of: {', '.join(TYPES)})")
    return typ


def coerce(value, typ: str):
    """Convert a model value to the declared type; raise ExtractError when impossible."""
    if value is None or value == "":
        return None
    if typ == "string":
        return str(value).strip()
    if typ in ("number", "integer"):
        if isinstance(value, bool):
            raise ExtractError(f"{value!r} is not a {typ}")
        if isinstance(value, (int, float)):
            num = float(value)
        else:
            m = re.search(r"-?\d[\d,]*(?:\.\d+)?", str(value))
            if not m:
                raise ExtractError(f"{value!r} is not a {typ}")
            num = float(m.group(0).replace(",", ""))
        return int(num) if typ == "integer" or num.is_integer() else num
    if typ == "boolean":
        if isinstance(value, bool):
            return value
        text = str(value).strip().lower()
        if text in ("true", "yes", "y", "1"):
            return True
        if text in ("false", "no", "n", "0"):
            return False
        raise ExtractError(f"{value!r} is not a boolean")
    if typ == "list":
        if isinstance(value, list):
            return [v for v in value if v not in (None, "")]
        return [s.strip() for s in str(value).split(",") if s.strip()]
    if typ == "url":
        text = str(value).strip()
        if not re.match(r"https?://", text):
            raise ExtractError(f"{value!r} is not an http(s) URL")
        return text
    raise ExtractError(f"unknown type {typ!r}")


def validate(records, fields: Dict[str, str]) -> Tuple[List[dict], List[str]]:
    """Keep only declared fields, coerce types, drop empty records. Returns (records, errors)."""
    if isinstance(records, dict):
        records = records.get("records", [records])
    if not isinstance(records, list):
        return [], ["reply must be a list of records"]
    clean, errors = [], []
    for i, rec in enumerate(records):
        if not isinstance(rec, dict):
            errors.append(f"record {i} is not an object")
            continue
        out = {}
        for name, typ in fields.items():
            try:
                out[name] = coerce(rec.get(name), typ)
            except ExtractError as e:
                errors.append(f"record {i}.{name}: {e}")
                out[name] = None
        if any(v not in (None, []) for v in out.values()):
            clean.append(out)
    return clean, errors


def chunks(text: str, size: int = CHUNK_CHARS, limit: int = MAX_CHUNKS) -> List[str]:
    """Split text on line boundaries into at most `limit` chunks of about `size` chars."""
    parts, buf = [], ""
    for line in text.splitlines(keepends=True):
        if buf and len(buf) + len(line) > size:
            parts.append(buf)
            buf = ""
        buf += line[:size]
    if buf.strip():
        parts.append(buf)
    return parts[:limit]


EXTRACT_PROMPT = """You extract structured data from web page text.
Task: {instruction}
Return ONLY a JSON object: {{"records": [ ... ]}} where every record has exactly these fields:
{schema}
Use null when a value is missing. Do not invent data that is not in the text.
If nothing matches, return {{"records": []}}."""
