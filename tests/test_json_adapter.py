import json
from pathlib import Path

from superbid_collector.json_adapter import extract_offer_observations
from superbid_collector.models import Outcome

FIX = Path(__file__).parent / "fixtures"


def test_structured_payload_is_recognized():
    payload = json.loads((FIX / "offer_payload.json").read_text())
    rows = extract_offer_observations(payload, "https://www.superbid.com.co/test")
    assert len(rows) == 1
    o = rows[0]
    assert o.external_lot_id == "4972833"
    assert o.title == "MAZDA 3 MOD. 2017"
    assert o.initial_bid_cop == 32000000
    assert o.displayed_price_cop == 48500000
    assert o.bid_count == 11
    assert o.outcome == Outcome.ACTIVE
    assert o.city == "Yumbo"
    assert "reserved_price" not in json.dumps(o.evidence)


def test_nested_payload_scan_and_dedupe():
    payload = json.loads((FIX / "offer_payload.json").read_text())
    nested = {"data": {"items": [payload, payload]}}
    rows = extract_offer_observations(nested)
    assert len(rows) == 1


def test_sold_status():
    payload = json.loads((FIX / "offer_payload.json").read_text())
    payload["offer_status"]["sold"] = True
    payload["winner_bid"] = 51000000
    rows = extract_offer_observations(payload)
    assert rows[0].outcome == Outcome.SOLD_CONFIRMED
    assert rows[0].displayed_price_cop == 51000000


def test_winner_bid_object_and_public_commission():
    payload={
        "id":4979999,
        "winner_bid":{"value":51500000,"bidder":"identity-not-persisted"},
        "total_bids":14,"total_bidders":5,
        "offer_status":{"sold":True,"closed":True},
        "offer_detail":{"initial_bid_value":40000000,"reserved_price":99999999},
        "group_offer":{"commission_percent":6.3},
        "end_date":"2026-08-20 18:00:00",
        "product":{"name":"TOYOTA COROLLA MOD. 2022"}
    }
    rows=extract_offer_observations(payload)
    assert rows[0].displayed_price_cop==51500000
    assert rows[0].displayed_price_label=="winner_bid"
    assert rows[0].evidence["total_bidders"]==5
    assert rows[0].evidence["commission_percent_public"]==6.3
    blob=json.dumps(rows[0].evidence).lower()
    assert "reserved_price" not in blob
    assert "identity-not-persisted" not in blob
    assert '"bidder":' not in blob
