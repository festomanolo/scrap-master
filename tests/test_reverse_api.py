from scrap_master import reverse_api

CALLS = [
    {"method": "GET", "url": "https://api.shop.io/v1/items/123/reviews?page=1&sort=new",
     "status": 200, "headers": {"accept": "application/json"}, "post_data": "", "sample": "{}"},
    {"method": "GET", "url": "https://api.shop.io/v1/items/456/reviews?page=2",
     "status": 200, "headers": {}, "post_data": "", "sample": "{}"},
    {"method": "POST", "url": "https://api.shop.io/v1/search",
     "status": 200, "headers": {}, "post_data": '{"q":"x"}', "sample": "[]"},
]
