from superbid_collector.storage import Store
from superbid_collector.models import LotObservation,Outcome
from superbid_collector.history import historical_rows,grouped_history
def test_history_export_logic(tmp_path):
 s=Store(tmp_path/"h.db");s.init();s.save(LotObservation(external_lot_id="1234567",url="https://www.superbid.com.co/oferta/toyota-hilux-1234567",title="TOYOTA HILUX MOD. 2020",brand="TOYOTA",model_year=2020,initial_bid_cop=50000000,displayed_price_cop=70000000,outcome=Outcome.SOLD_CONFIRMED));rows=historical_rows(s.conn,brand="TOYOTA");assert len(rows)==1 and rows[0]["historical_value_cop"]==70000000;assert grouped_history(s.conn,brand="TOYOTA")[0]["median_cop"]==70000000
