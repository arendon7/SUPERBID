import httpx
import pytest

from superbid_collector.direct_public_api import fetch_public_lot, public_lot_params


LOT_URL = "https://www.superbid.com.co/oferta/mazda-3-mod-2017-placa-2-ubic-acopi-yumbo-cali-4972833"


def _payload():
    return {
        "offers": [{
            "id": 4972833,
            "lotNumber": 7,
            "price": 9800000,
            "totalBids": 0,
            "endDate": "2026-08-27 15:36:00",
            "offerStatus": {
                "available": True,
                "giveYourBid": True,
                "closed": False,
                "sold": False,
            },
            "offerDetail": {
                "initialBidValue": 9800000,
                "currentMaxBid": 9800000,
                "currentMinBid": 9800000,
            },
            "groupOffer": {"commissionPercent": 6.5},
            "auction": {
                "id": 785575,
                "desc": "SBS Seguros",
                "currencyIso": "COP",
                "address": {"city": "Sao Paulo"},
            },
            "seller": {"name": "Sbs Seguros Colombia S.A."},
            "product": {
                "shortDesc": "MAZDA 3 MOD. 2017, PLACA: 2 Ubic.: ACOPI - YUMBO CALI",
                "brand": {},
                "model": {},
                "location": {"city": "Yumbo", "state": "Valle del Cauca", "country": "Colombia"},
                "galleryJson": [],
                "productCustomJson": "",
            },
        }],
        "total": 1,
    }


def test_public_lot_params_are_stateless_and_filter_free():
    params = public_lot_params(LOT_URL)
    assert params["portalId"] == "[17]"
    assert params["locale"] == "es_CO"
    assert params["timeZoneId"] == "UTC"
    assert params["requestOrigin"] == "marketplace"
    assert params["urlSeo"] == LOT_URL
    assert "filter" not in params


@pytest.mark.asyncio
async def test_fetch_public_lot_without_filter_or_cookies():
    def handler(request: httpx.Request):
        assert request.url.host == "offer-query.superbid.net"
        assert request.url.path == "/seo/offers/"
        assert request.url.params.get("filter") is None
        assert request.url.params.get("portalId") == "[17]"
        assert request.url.params.get("urlSeo") == LOT_URL
        assert "cookie" not in {k.lower() for k in request.headers.keys()}
        return httpx.Response(200, json=_payload())

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        result = await fetch_public_lot(LOT_URL, client=client)

    obs = result["observation"]
    assert result["status"] == 200
    assert obs.external_lot_id == "4972833"
    assert obs.brand == "MAZDA"
    assert obs.line == "3"
    assert obs.model_year == 2017
    assert obs.city == "Yumbo"
    assert obs.displayed_price_cop == 9800000
    assert obs.closes_at_text == "2026-08-27 15:36:00"
    assert obs.evidence["commission_percent_public"] == 6.5
