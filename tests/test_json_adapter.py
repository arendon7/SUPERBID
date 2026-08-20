import json
from pathlib import Path
from superbid_collector.json_adapter import extract_offer_observations
from superbid_collector.models import Outcome
FIX=Path(__file__).parent/"fixtures"
def payload():return json.loads((FIX/"offer_payload.json").read_text())
def test_structured_payload_is_recognized():
 rows=extract_offer_observations(payload(),"https://www.superbid.com.co/test");o=rows[0];assert len(rows)==1 and o.external_lot_id=="4972833" and o.title=="MAZDA 3 MOD. 2017" and o.initial_bid_cop==32000000 and o.displayed_price_cop==48500000 and o.bid_count==11 and o.outcome==Outcome.ACTIVE and o.city=="Yumbo";assert "reserved_price" not in json.dumps(o.evidence)
def test_nested_payload_scan_and_dedupe():
 p=payload();assert len(extract_offer_observations({"data":{"items":[p,p]}}))==1
def test_sold_status():
 p=payload();p["offer_status"]["sold"]=True;p["winner_bid"]=51000000;o=extract_offer_observations(p)[0];assert o.outcome==Outcome.SOLD_CONFIRMED and o.displayed_price_cop==51000000
