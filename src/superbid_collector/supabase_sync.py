from __future__ import annotations
import json,os,sqlite3
from datetime import datetime,timezone
import httpx
SYNC_SCHEMA="CREATE TABLE IF NOT EXISTS sync_state (key TEXT PRIMARY KEY,value TEXT,updated_at TEXT NOT NULL);"
def _now():return datetime.now(timezone.utc).isoformat()
def init_sync_state(conn):conn.executescript(SYNC_SCHEMA);conn.commit()
def set_state(conn,key,value):
    init_sync_state(conn);conn.execute("INSERT INTO sync_state(key,value,updated_at) VALUES (?,?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value,updated_at=excluded.updated_at",(key,value,_now()));conn.commit()
def get_state(conn,key):
    init_sync_state(conn);row=conn.execute("SELECT value FROM sync_state WHERE key=?",(key,)).fetchone();return row["value"] if row else None
class SupabaseREST:
    def __init__(self,url=None,service_role_key=None):
        self.url=(url or os.getenv("SUPABASE_URL") or "").rstrip("/");self.key=service_role_key or os.getenv("SUPABASE_SERVICE_ROLE_KEY") or ""
        if not self.url or not self.key:raise RuntimeError("SUPABASE_URL y SUPABASE_SERVICE_ROLE_KEY son requeridos.")
        self.client=httpx.Client(timeout=35,headers={"apikey":self.key,"Authorization":f"Bearer {self.key}","Content-Type":"application/json"})
    def close(self):self.client.close()
    def upsert(self,table,rows,on_conflict=None,returning=True):
        if not rows:return []
        params={"on_conflict":on_conflict} if on_conflict else {};prefer=["resolution=merge-duplicates","return=representation" if returning else "return=minimal"]
        r=self.client.post(f"{self.url}/rest/v1/{table}",params=params,headers={"Prefer":",".join(prefer)},content=json.dumps(rows,ensure_ascii=False,default=str));r.raise_for_status();return r.json() if returning and r.content else []
def _dicts(conn,sql,args=()):return [dict(r) for r in conn.execute(sql,args).fetchall()]
def _lot_map(remote,local_lots):
    if not local_lots:return {}
    payload=[{k:v for k,v in r.items() if k!="id"} for r in local_lots];remote_rows=remote.upsert("auction_lots",payload,on_conflict="source,external_lot_id",returning=True);by_key={(x["source"],str(x["external_lot_id"])):int(x["id"]) for x in remote_rows};return {int(l["id"]):by_key[(l["source"],str(l["external_lot_id"]))] for l in local_lots if (l["source"],str(l["external_lot_id"])) in by_key}
def sync_core(conn,remote,batch_size=500):
    init_sync_state(conn);counts={};lots=_dicts(conn,"SELECT * FROM lots ORDER BY id");lot_map=_lot_map(remote,lots);counts["auction_lots"]=len(lot_map)
    def batches(items):
        for i in range(0,len(items),batch_size):yield items[i:i+batch_size]
    rows=[]
    for r in _dicts(conn,"SELECT * FROM lot_snapshots ORDER BY id"):
        rid=lot_map.get(int(r["lot_id"]));
        if not rid:continue
        rows.append({"lot_id":rid,"observed_at":r["observed_at"],"displayed_price_cop":r["displayed_price_cop"],"displayed_price_label":r["displayed_price_label"],"bid_count":r["bid_count"],"status_text":r["status_text"],"outcome":r["outcome"],"closes_at_text":r["closes_at_text"],"evidence":json.loads(r["evidence_json"] or "{}")})
    for b in batches(rows):remote.upsert("auction_snapshots",b,on_conflict="lot_id,observed_at",returning=False)
    counts["auction_snapshots"]=len(rows);rows=[]
    for r in _dicts(conn,"SELECT * FROM lot_outcomes"):
        rid=lot_map.get(int(r["lot_id"]));
        if not rid:continue
        rows.append({"lot_id":rid,"outcome":r["outcome"],"closing_price_observed_cop":r["closing_price_observed_cop"],"sale_price_confirmed_cop":r["sale_price_confirmed_cop"],"confidence":r["confidence"],"updated_at":r["updated_at"]})
    remote.upsert("auction_outcomes",rows,on_conflict="lot_id",returning=False);counts["auction_outcomes"]=len(rows);rows=[]
    for r in _dicts(conn,"SELECT * FROM lot_attachments"):
        rid=lot_map.get(int(r["lot_id"]));
        if rid:rows.append({"lot_id":rid,"name":r["name"],"url":r["url"],"kind":r["kind"],"source":r["source"],"discovered_at":r["discovered_at"]})
    for b in batches(rows):remote.upsert("lot_attachments",b,on_conflict="lot_id,url",returning=False)
    counts["lot_attachments"]=len(rows);rows=[]
    for r in _dicts(conn,"SELECT * FROM lot_bid_history"):
        rid=lot_map.get(int(r["lot_id"]));
        if rid:rows.append({"lot_id":rid,"sequence_no":r["sequence_no"],"amount_cop":r["amount_cop"],"bid_at_text":r["bid_at_text"],"observed_at":r["observed_at"]})
    for b in batches(rows):remote.upsert("lot_bid_history",b,on_conflict="lot_id,amount_cop,bid_at_text",returning=False)
    counts["lot_bid_history"]=len(rows);rows=[]
    for r in _dicts(conn,"SELECT * FROM market_comparables"):
        rid=lot_map.get(int(r["lot_id"])) if r["lot_id"] is not None else None;raw=r["raw_json"]
        try:raw=json.loads(raw) if isinstance(raw,str) and raw else None
        except Exception:raw={"raw":raw}
        rows.append({"lot_id":rid,"source":r["source"],"external_id":r["external_id"],"url":r["url"],"observed_at":r["observed_at"],"asking_price_cop":r["asking_price_cop"],"brand":r["brand"],"line":r["line"],"version":r["version"],"model_year":r["model_year"],"mileage_km":r["mileage_km"],"city":r["city"],"seller_type":r["seller_type"],"match_score":r["match_score"],"raw_json":raw})
    for b in batches(rows):remote.upsert("market_comparables",b,on_conflict="source,external_id,observed_at",returning=False)
    counts["market_comparables"]=len(rows);rows=[]
    try:prov_rows=_dicts(conn,"SELECT * FROM lot_provenance")
    except Exception:prov_rows=[]
    for r in prov_rows:
        rid=lot_map.get(int(r["lot_id"]));
        if not rid:continue
        try:fields=json.loads(r["fields_json"] or "{}")
        except Exception:fields={}
        rows.append({"lot_id":rid,"source_type":r["source_type"],"source_url":r["source_url"],"observed_at":r["observed_at"],"fields":fields,"confidence":r["confidence"],"note":r["note"]})
    for b in batches(rows):remote.upsert("lot_provenance",b,on_conflict="lot_id,source_type,source_url",returning=False)
    counts["lot_provenance"]=len(rows);rows=[]
    for r in _dicts(conn,"SELECT * FROM app_settings"):
        try:value=json.loads(r["value_json"])
        except Exception:value={}
        rows.append({"key":r["key"],"value_json":value,"updated_at":r["updated_at"]})
    remote.upsert("app_settings",rows,on_conflict="key",returning=False);counts["app_settings"]=len(rows);rows=[]
    for r in _dicts(conn,"SELECT * FROM discovery_sources"):rows.append({"url":r["url"],"enabled":bool(r["enabled"]),"source_type":r["source_type"],"last_scan_at":r["last_scan_at"],"last_error":r["last_error"],"created_at":r["created_at"]})
    remote.upsert("discovery_sources",rows,on_conflict="url",returning=False);counts["discovery_sources"]=len(rows);rows=[]
    for r in _dicts(conn,"SELECT * FROM collection_queue"):rows.append({"external_lot_id":r["external_lot_id"],"url":r["url"],"status":r["status"],"next_run_at":r["next_run_at"],"last_run_at":r["last_run_at"],"last_success_at":r["last_success_at"],"consecutive_errors":r["consecutive_errors"],"last_error":r["last_error"],"closes_at_text":r["closes_at_text"],"priority":r["priority"],"created_at":r["created_at"],"updated_at":r["updated_at"]})
    remote.upsert("collection_queue",rows,on_conflict="external_lot_id",returning=False);counts["collection_queue"]=len(rows);counts["collection_runs"]="local_only_v09"
    set_state(conn,"supabase_last_sync_at",_now());set_state(conn,"supabase_last_sync_counts",json.dumps(counts,ensure_ascii=False));set_state(conn,"supabase_last_sync_error","");return counts
def sync_once(conn,url=None,key=None):
    remote=SupabaseREST(url,key)
    try:return sync_core(conn,remote)
    except Exception as exc:set_state(conn,"supabase_last_sync_error",str(exc));raise
    finally:remote.close()
