import httpx
import pytest

from superbid_collector.storage import Store
from superbid_collector.direct_discovery import discover_open_vehicles_direct, public_lot_url


def _offer(lot_id: int, category_id: int, title: str, *, shopping: bool = False):
    return {
        "id": lot_id,
        "lotNumber": lot_id % 100,
        "price": 30000000,
        "totalBids": 1,
        "endDate": "2026-08-27 15:36:00",
        "isShopping": shopping,
        "shoppingOfferType": shopping,
        "offerStatus": {"available": True, "giveYourBid": not shopping, "closed": False, "sold": False},
        "offerDetail": {"initialBidValue": 25000000, "currentMaxBid": 30000000},
        "groupOffer": {"commissionPercent": 6.5},
        "auction": {
            "id": 1,
            "desc": "Evento",
            "currencyIso": "COP",
            "modalityDesc": "Shopping" if shopping else "Subasta",
        },
        "seller": {"name": "Vendedor"},
        "product": {
            "shortDesc": title,
            "brand": {},
            "model": {},
            "location": {"city": "Medellin", "country": "Colombia"},
            "productType": {"id": 10, "description": "Autos y Motos"},
            "subCategory": {"category": {"id": category_id, "description": "Categoria"}},
        },
    }


def test_public_lot_url_uses_title_slug_and_stable_id():
    offer = _offer(4972833, 10000, "MAZDA 3 MOD. 2017, PLACA: 2 Ubic.: ACOPI - YUMBO CALI")
    assert public_lot_url(offer) == (
        "https://www.superbid.com.co/oferta/"
        "mazda-3-mod-2017-placa-2-ubic-acopi-yumbo-cali-4972833"
    )


@pytest.mark.asyncio
async def test_direct_discovery_filters_categories_and_shopping(tmp_path):
    page1 = {
        "offers": [
            _offer(5000001, 10000, "TOYOTA COROLLA MOD. 2022"),
            _offer(5000002, 10012, "YAMAHA MOTO MOD. 2024"),
            _offer(5000003, 99999, "EQUIPO INDUSTRIAL"),
            _offer(5000005, 10000, "AUTO SHOPPING", shopping=True),
        ],
        "total": 5,
    }
    page2 = {
        "offers": [_offer(5000004, 10022, "HINO CAMION MOD. 2020")],
        "total": 5,
    }

    def handler(request: httpx.Request):
        assert request.url.host == "offer-query.superbid.net"
        assert request.url.params.get("filter") is None
        assert request.url.params.get("fieldList") is None
        page = int(request.url.params["pageNumber"])
        return httpx.Response(200, json=page1 if page == 1 else page2)

    s = Store(tmp_path / "discover.db")
    s.init()
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        result = await discover_open_vehicles_direct(
            s, max_pages=5, page_size=4, client=client
        )

    assert result["pages_scanned"] == 2
    assert result["offers_seen"] == 5
    assert result["vehicle_auction_lots_seen"] == 2
    assert result["shopping_vehicle_offers_skipped"] == 1
    assert result["queued"] == 2
    ids = {
        row["external_lot_id"]
        for row in s.conn.execute("select external_lot_id from collection_queue").fetchall()
    }
    assert ids == {"5000001", "5000004"}
