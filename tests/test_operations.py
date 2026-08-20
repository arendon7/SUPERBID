from datetime import datetime,timezone,timedelta
from superbid_collector.storage import Store
from superbid_collector.operations import enqueue_lot,due_lots,mark_queue_result,interval_for_close
def test_queue_lifecycle(tmp_path):
 s=Store(tmp_path/"q.db");s.init();close=(datetime.now(timezone.utc)+timedelta(hours=1)).isoformat();enqueue_lot(s.conn,"1234567","https://www.superbid.com.co/oferta/x-1234567",close);assert len(due_lots(s.conn,10))==1;mark_queue_result(s.conn,"1234567",ok=True,closes_at_text=close,outcome="ACTIVE");r=s.conn.execute("SELECT * FROM collection_queue WHERE external_lot_id='1234567'").fetchone();assert r["status"]=="WATCH" and r["consecutive_errors"]==0
def test_terminal_queue(tmp_path):
 s=Store(tmp_path/"q.db");s.init();enqueue_lot(s.conn,"1234568","https://www.superbid.com.co/oferta/x-1234568");mark_queue_result(s.conn,"1234568",ok=True,outcome="SOLD_CONFIRMED");assert s.conn.execute("SELECT status FROM collection_queue WHERE external_lot_id='1234568'").fetchone()["status"]=="DONE"
def test_intervals():
 assert interval_for_close((datetime.now(timezone.utc)+timedelta(minutes=10)).isoformat())==60;assert interval_for_close((datetime.now(timezone.utc)+timedelta(hours=1)).isoformat())==300
