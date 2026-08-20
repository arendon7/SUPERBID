from superbid_collector.network_capture import _expected_lot_id, _offer_dict_for


def test_detail_url_sets_expected_lot():
    assert _expected_lot_id("https://www.superbid.com.co/oferta/mazda-x-4972833")=="4972833"
    assert _expected_lot_id("https://www.superbid.com.co/") is None


def test_offer_dict_scope_returns_only_expected():
    payload={"offers":[
        {"id":4972833,"offerDetail":{"initialBidValue":1}},
        {"id":4973043,"offerDetail":{"initialBidValue":2}},
    ]}
    rows=list(_offer_dict_for(payload,"4972833"))
    assert len(rows)==1
    assert rows[0]["id"]==4972833
