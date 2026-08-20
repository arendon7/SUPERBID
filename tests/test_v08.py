from superbid_collector.storage import Store
from superbid_collector.health import operational_health
from superbid_collector.bootstrap import bootstrap
def test_operational_health(tmp_path):
 s=Store(tmp_path/"h.db");s.init();h=operational_health(s.conn);assert h["ok"] is True and "queue" in h
def test_bootstrap_db(tmp_path,monkeypatch):
 db=tmp_path/"b.db";monkeypatch.setenv("SUPERBID_DISCOVERY_URLS","");s=bootstrap(str(db));assert s.conn.execute("select count(*) c from discovery_sources").fetchone()["c"]==0
