from superbid_collector.storage import Store
from superbid_collector.models import LotObservation,Outcome
from superbid_collector.supabase_sync import sync_core,get_state
class FakeRemote:
 def __init__(self):self.tables={};self.next_id=100
 def upsert(self,table,rows,on_conflict=None,returning=True):
  self.tables.setdefault(table,[]).extend(rows)
  if table=="auction_lots":
   out=[]
   for r in rows:x=dict(r);x["id"]=self.next_id;self.next_id+=1;out.append(x)
   return out
  return []
def test_sync_core_maps_lot_ids(tmp_path):
 s=Store(tmp_path/"x.db");s.init();s.save(LotObservation(external_lot_id="1234567",url="https://www.superbid.com.co/oferta/x-1234567",title="TOYOTA HILUX MOD. 2020",brand="TOYOTA",model_year=2020,displayed_price_cop=60000000,outcome=Outcome.ACTIVE));fake=FakeRemote();counts=sync_core(s.conn,fake);assert counts["auction_lots"]==1 and len(fake.tables["auction_snapshots"])==1 and fake.tables["auction_snapshots"][0]["lot_id"]==100 and get_state(s.conn,"supabase_last_sync_at") is not None
