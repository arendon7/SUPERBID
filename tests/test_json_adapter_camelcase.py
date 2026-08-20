from superbid_collector.json_adapter import extract_offer_observations
from superbid_collector.models import Outcome


def test_real_contract_camelcase_offer():
    payload={
        "offers":[{
            "id":4972833,
            "endDate":"2026-08-20T21:00:00",
            "lotNumber":7,
            "price":48500000,
            "totalBids":11,
            "offerDetail":{"initialBidValue":32000000,"currentMaxBid":48500000,"currentMinBid":49000000},
            "offerStatus":{"available":False,"closed":True,"closedToBids":True,"sold":False},
            "groupOffer":{"commissionPercent":6.3,"id":99},
            "auction":{"id":785575,"currencyIso":"COP","desc":"Vehículos","address":{"city":"Yumbo"}},
            "product":{"shortDesc":"MAZDA 3 MOD. 2017","brand":{"name":"MAZDA"},"model":{"name":"3"}},
            "seller":{"name":"VENDEDOR PUBLICO"},
            "winnerBid":{}
        }]
    }
    rows=extract_offer_observations(payload,"https://www.superbid.com.co/oferta/x-4972833")
    assert len(rows)==1
    o=rows[0]
    assert o.external_lot_id=="4972833"
    assert o.title=="MAZDA 3 MOD. 2017"
    assert o.brand=="MAZDA"
    assert o.line=="3"
    assert o.city=="Yumbo"
    assert o.initial_bid_cop==32000000
    assert o.displayed_price_cop==48500000
    assert o.bid_count==11
    assert o.outcome==Outcome.CLOSED_OBSERVED
    assert o.closes_at_text=="2026-08-20T21:00:00"
    assert o.evidence["commission_percent_public"]==6.3
    assert o.evidence["parser"]=="superbid_json_v3_camelcase"
