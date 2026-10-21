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
