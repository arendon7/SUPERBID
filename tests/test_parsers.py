from pathlib import Path
from superbid_collector.parsers import parse_lot_html,lot_id_from_url,money_to_int
from superbid_collector.models import Outcome
FIX=Path(__file__).parent/"fixtures"
def test_lot_id():assert lot_id_from_url("https://www.superbid.com.co/oferta/abc-4731041")=="4731041"
def test_money():assert money_to_int("$ 190.900.000")==190900000
def test_active_fixture():
 o=parse_lot_html("https://www.superbid.com.co/oferta/toyota-hilux-4731041",(FIX/"lot_active.html").read_text());assert o.external_lot_id=="4731041" and o.brand=="TOYOTA" and o.model_year==2025 and o.initial_bid_cop==190900000 and o.displayed_price_cop==201500000 and o.outcome==Outcome.ACTIVE and o.city.lower().startswith("girardota")
def test_conditional_fixture():
 o=parse_lot_html("https://www.superbid.com.co/oferta/renault-duster-4368811",(FIX/"lot_conditional.html").read_text());assert o.displayed_price_cop==41100000 and o.outcome==Outcome.CONDITIONAL
