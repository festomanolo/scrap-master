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


def test_validate_drops_unknown_fields_and_empty_records():
    fields = {"name": "string", "price": "number"}
    recs, errors = extract.validate({"records": [{"name": "A", "price": "5", "x": 1}, {}, 7]}, fields)
    assert recs == [{"name": "A", "price": 5}]
    assert errors == ["record 2 is not an object"]


def test_chunks_respects_size_and_limit():
    text = "\n".join("x" * 50 for _ in range(100))
    parts = extract.chunks(text, size=200, limit=3)
    assert len(parts) == 3 and all(len(p) <= 200 for p in parts)


def test_extract_text_retries_with_error_feedback():
    replies = iter(['{"records": [{"price": "free"}]}', '{"records": [{"price": 0}]}'])
    seen = []

    def chat(messages, json_mode=False):
        seen.append(messages)
        return next(replies)

    assert extract.extract_text("page", {"price": "number"}, chat=chat) == [{"price": 0}]
    assert "Fix these problems" in seen[1][-1]["content"]


def test_extract_urls_adds_source_and_skips_failures():
    def reader(url):
        if "bad" in url:
            raise OSError("down")
        return "Item A"

    recs = extract.extract_urls(["https://a.org", "https://bad.org"], {"name": "string"},
                                reader=reader, chat=lambda m, json_mode=False: '{"records":[{"name":"A"}]}')
    assert recs == [{"name": "A", "source": "https://a.org"}]


def test_write_records_formats(tmp_path):
    recs = [{"name": "A", "tags": ["x", "y"]}, {"name": "B", "tags": []}]
    assert json.loads(extract.write_records(recs, tmp_path / "r.json").read_text()) == recs
    lines = extract.write_records(recs, tmp_path / "r.jsonl").read_text().splitlines()
    assert [json.loads(line) for line in lines] == recs
    rows = list(csv.DictReader(extract.write_records(recs, tmp_path / "r.csv").open()))
    assert rows[0] == {"name": "A", "tags": "x; y"}
    with pytest.raises(extract.ExtractError):
        extract.write_records(recs, tmp_path / "r.xml")
