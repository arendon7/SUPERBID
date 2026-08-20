from superbid_collector.json_adapter import extract_offer_observations


def test_product_location_and_title_fallback_win_over_auction_address():
    payload={"offers":[{
        "id":4972833,"price":9800000,"totalBids":0,"endDate":"2026-08-27 15:36:00",
        "offerDetail":{"initialBidValue":9800000},
        "offerStatus":{"available":True,"closed":False,"sold":False},
        "auction":{"address":{"city":"São Paulo"},"currencyIso":"COP"},
        "product":{"shortDesc":"MAZDA 3 MOD. 2017, PLACA: 2 Ubic.: ACOPI - YUMBO CALI","brand":{},"model":{},"location":{"city":"Yumbo"}},
        "seller":{"name":"Sbs Seguros Colombia S.A."}
    }]}
    o=extract_offer_observations(payload)[0]
    assert o.city=="Yumbo"
    assert o.brand=="MAZDA"
    assert o.line=="3"
    assert o.model_year==2017
