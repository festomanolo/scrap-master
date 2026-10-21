import csv
import json

import pytest

from scrap_master import extract


def test_parse_fields_inline_spec():
    assert extract.parse_fields("name, price:number, tags:list, in stock:bool") == {
        "name": "string", "price": "number", "tags": "list", "in_stock": "boolean"}


def test_parse_fields_json_schema():
    spec = json.dumps({"properties": {"title": {"type": "string"}, "year": {"type": "integer"}}})
    assert extract.parse_fields(spec) == {"title": "string", "year": "integer"}


def test_load_fields_from_file(tmp_path):
    p = tmp_path / "s.json"
    p.write_text('{"url": "link"}')
    assert extract.load_fields(str(p)) == {"url": "url"}


@pytest.mark.parametrize("spec", ["", "price:money", "1bad"])
def test_parse_fields_rejects_bad_specs(spec):
    with pytest.raises(extract.ExtractError):
        extract.parse_fields(spec)


@pytest.mark.parametrize(("value", "typ", "want"), [
    ("TSh 12,500.50", "number", 12500.5),
    ("3 items", "integer", 3),
    (4.0, "number", 4),
    ("yes", "boolean", True),
    ("a, b,", "list", ["a", "b"]),
    (" https://x.org ", "url", "https://x.org"),
    ("", "string", None),
])
def test_coerce(value, typ, want):
    assert extract.coerce(value, typ) == want


@pytest.mark.parametrize(("value", "typ"), [("n/a", "number"), (True, "integer"),
                                            ("maybe", "boolean"), ("x.org", "url")])
def test_coerce_rejects(value, typ):
    with pytest.raises(extract.ExtractError):
        extract.coerce(value, typ)
