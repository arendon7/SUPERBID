from urllib.parse import parse_qs, urlsplit
from superbid_collector.discovery_urls import build_paginated_urls, is_paginated_source

def test_paginated_urls_preserve_filters():
    urls=build_paginated_urls(
        "https://example.superbid.com/category/cars?searchType=opened&orderBy=endDate",
        max_pages=3,page_size=40
    )
    assert len(urls)==3
    q1=parse_qs(urlsplit(urls[0]).query)
    q3=parse_qs(urlsplit(urls[2]).query)
    assert q1["searchType"]==["opened"]
    assert q1["orderBy"]==["endDate"]
    assert q1["pageNumber"]==["1"]
    assert q1["pageSize"]==["40"]
    assert q3["pageNumber"]==["3"]

def test_paginated_source_type():
    assert is_paginated_source("paginated")
    assert not is_paginated_source("listing")
