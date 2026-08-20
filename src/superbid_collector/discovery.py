from __future__ import annotations
from datetime import datetime,timezone
from .network_capture import capture_public_json
from .operations import enqueue_lot,start_run,finish_run

async def discover_from_source(store,source_url:str,seconds:int=12)->dict:
    run_id=start_run(store.conn,"DISCOVERY",source_url)
    try:
        result=await capture_public_json(source_url,seconds=seconds,db=store.path,dump_dir=None);lots=result.get("lots_found") or []
        for lot in lots:enqueue_lot(store.conn,str(lot["external_lot_id"]),lot.get("url") or source_url,lot.get("closes_at_text"),priority=100)
        finish_run(store.conn,run_id,ok=True,lots_found=len(lots),lots_saved=result.get("saved",0),attachments_saved=result.get("attachments_saved",0),bids_saved=result.get("bids_saved",0));store.conn.execute("UPDATE discovery_sources SET last_scan_at=?,last_error=NULL WHERE url=?",(datetime.now(timezone.utc).isoformat(),source_url));store.conn.commit();return result
    except Exception as exc:
        finish_run(store.conn,run_id,ok=False,error=str(exc));store.conn.execute("UPDATE discovery_sources SET last_scan_at=?,last_error=? WHERE url=?",(datetime.now(timezone.utc).isoformat(),str(exc),source_url));store.conn.commit();raise

def add_discovery_source(store,url:str,source_type:str="listing"):
    now=datetime.now(timezone.utc).isoformat();store.conn.execute("INSERT INTO discovery_sources(url,enabled,source_type,created_at) VALUES (?,1,?,?) ON CONFLICT(url) DO UPDATE SET enabled=1,source_type=excluded.source_type",(url,source_type,now));store.conn.commit()

def sources(store)->list[dict]:return [dict(r) for r in store.conn.execute("SELECT * FROM discovery_sources WHERE enabled=1 ORDER BY id").fetchall()]
