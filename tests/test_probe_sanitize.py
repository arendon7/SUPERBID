from superbid_collector.probe_sanitize import endpoint_signature, safe_shape


def test_endpoint_signature_drops_query_values_and_sensitive_keys():
    out=endpoint_signature("https://api.example.com/offers?pageNumber=2&token=secret&searchType=opened")
    assert out["host"]=="api.example.com"
    assert out["path"]=="/offers"
    assert out["query_keys"]==["pageNumber","searchType"]
    assert "secret" not in str(out)


def test_safe_shape_drops_reserve_bidder_and_auth_data():
    shape=safe_shape({
        "id":1,
        "winner_bid":{"value":10,"bidder":{"name":"x"}},
        "reserved_price":99,
        "authorization":"Bearer x",
        "items":[{"price":10,"token":"x"}],
    })
    blob=str(shape).lower()
    assert "reserved" not in blob
    assert "bidder" not in blob
    assert "authorization" not in blob
    assert "token" not in blob
    assert shape["id"]=="number"
