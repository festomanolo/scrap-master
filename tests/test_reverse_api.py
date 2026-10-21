from scrap_master import reverse_api

CALLS = [
    {"method": "GET", "url": "https://api.shop.io/v1/items/123/reviews?page=1&sort=new",
     "status": 200, "headers": {"accept": "application/json"}, "post_data": "", "sample": "{}"},
    {"method": "GET", "url": "https://api.shop.io/v1/items/456/reviews?page=2",
     "status": 200, "headers": {}, "post_data": "", "sample": "{}"},
    {"method": "POST", "url": "https://api.shop.io/v1/search",
     "status": 200, "headers": {}, "post_data": '{"q":"x"}', "sample": "[]"},
]


def test_scrub_headers_drops_secrets():
    got = reverse_api.scrub_headers({"Cookie": "s=1", "Authorization": "Bearer x",
                                     "Accept": "application/json", "X-Api-Key": "k"})
    assert got == {"accept": "application/json"}


def test_path_template_replaces_ids():
    assert reverse_api.path_template("/v1/items/123/reviews") == "/v1/items/{id}/reviews"
    assert reverse_api.path_template("/u/3f2a9c1e-1111-2222-3333-444455556666") == "/u/{id}"
    assert reverse_api.path_template("/v1/search") == "/v1/search"


def test_is_api_call():
    assert reverse_api.is_api_call("fetch", "text/html")
    assert reverse_api.is_api_call("document", "application/json; charset=utf-8")
    assert not reverse_api.is_api_call("image", "image/png")


def test_group_endpoints_merges_same_route():
    eps = reverse_api.group_endpoints(CALLS)
    assert [(e["method"], e["path"], e["hits"]) for e in eps] == [
        ("GET", "/v1/items/{id}/reviews", 2), ("POST", "/v1/search", 1)]
    assert eps[0]["params"] == {"page": "1", "sort": "new"}


def test_template_client_is_valid_python_with_methods():
    code = reverse_api.template_client(reverse_api.group_endpoints(CALLS), "api.shop.io")
    ns = {}
    exec(compile(code, "client", "exec"), ns)
    client = ns["Client"]
    assert hasattr(client, "get_v1_items_reviews") and hasattr(client, "post_v1_search")
    assert 'f"https://api.shop.io/v1/items/{id}/reviews"' in code


def test_template_client_numbers_multiple_ids():
    eps = reverse_api.group_endpoints([{**CALLS[0], "url": "https://a.io/u/12/p/34"}])
    code = reverse_api.template_client(eps, "a.io")
    assert "def get_u_p(self, id, id2, **params)" in code and "/u/{id}/p/{id2}" in code


def test_generate_client_falls_back_when_ai_returns_garbage(monkeypatch):
    monkeypatch.setattr(reverse_api, "ai_client", lambda e, s: (_ for _ in ()).throw(SyntaxError()))
    code = reverse_api.generate_client(reverse_api.group_endpoints(CALLS), "api.shop.io")
    assert code.startswith('"""API client for api.shop.io')


def test_ai_client_strips_fences_and_checks_syntax():
    eps = reverse_api.group_endpoints(CALLS)
    code = reverse_api.ai_client(eps, "s", chat=lambda m: "Sure!\n```python\nclass Client: pass\n```")
    assert code == "class Client: pass\n"
