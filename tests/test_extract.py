import csv
import json

import pytest

from scrap_master import extract


def test_parse_fields_inline_spec():
    assert extract.parse_fields("name, price:number, tags:list, in stock:bool") == {
        "name": "string", "price": "number", "tags": "list", "in_stock": "boolean"}
