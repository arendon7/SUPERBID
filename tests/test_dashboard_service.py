from superbid_collector.storage import Store
from superbid_collector.models import LotObservation,Outcome
from superbid_collector.market_storage import add_comparable
from superbid_collector.dashboard_service import active_opportunities
from superbid_collector.valuation import CostProfile
def test_active_opportunity_row(tmp_path):
 s=Store(tmp_path/"d.db");s.init();lid=s.save(LotObservation(external_lot_id="7654321",url="https://www.superbid.com.co/oferta/x-7654321",title="TOYOTA HILUX MOD. 2020",brand="TOYOTA",model_year=2020,city="Medellin",displayed_price_cop=60000000,initial_bid_cop=45000000,closes_at_text="2026-08-20 17:00",outcome=Outcome.ACTIVE))
 for i,p in enumerate([80000000,82000000,84000000,86000000,88000000]):add_comparable(s.conn,lot_id=lid,source="test",external_id=str(i),asking_price_cop=p)
 rows=active_opportunities(s.conn,CostProfile(),10);assert len(rows)==1 and rows[0]["external_lot_id"]=="7654321" and rows[0]["market_reference_cop"] is not None and "decision" in rows[0]
