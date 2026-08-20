from superbid_collector.storage import Store
from superbid_collector.models import LotObservation,Outcome
from superbid_collector.provenance import save_provenance,provenance_for_lot,quality_label
def test_provenance_roundtrip(tmp_path):
 s=Store(tmp_path/"p.db");s.init();o=LotObservation(external_lot_id="7654321",url="https://www.superbid.com.co/oferta/x-7654321",title="TOYOTA HILUX MOD. 2020",displayed_price_cop=50000000,outcome=Outcome.ACTIVE);lid=s.save(o);save_provenance(s.conn,lid,source_type="superbid_public_json",source_url=o.url,fields={"displayed_price_cop":True},confidence=.9,note="test");rows=provenance_for_lot(s.conn,lid);assert rows[0]["source_type"]=="superbid_public_json" and rows[0]["fields"]["displayed_price_cop"] is True and quality_label("superbid_public_json",.9)=="ALTA"
def test_sold_creates_confirmation_provenance(tmp_path):
 s=Store(tmp_path/"s.db");s.init();lid=s.save(LotObservation(external_lot_id="7654322",url="https://www.superbid.com.co/oferta/x-7654322",displayed_price_cop=70000000,outcome=Outcome.SOLD_CONFIRMED));assert any(x["source_type"]=="sold_confirmation" for x in provenance_for_lot(s.conn,lid))
