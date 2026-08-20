from __future__ import annotations
from datetime import datetime,timezone
import sqlite3
def operational_health(conn:sqlite3.Connection)->dict:
    q=conn.execute("SELECT COUNT(*) total,SUM(CASE WHEN status='WATCH' THEN 1 ELSE 0 END) watching,SUM(CASE WHEN status='DONE' THEN 1 ELSE 0 END) done,SUM(CASE WHEN consecutive_errors>=3 THEN 1 ELSE 0 END) unhealthy FROM collection_queue").fetchone()
    latest=conn.execute("SELECT started_at,finished_at,ok,error,run_type,target FROM collection_runs ORDER BY started_at DESC LIMIT 1").fetchone()
    latest_success=conn.execute("SELECT finished_at FROM collection_runs WHERE ok=1 AND finished_at IS NOT NULL ORDER BY finished_at DESC LIMIT 1").fetchone()
    return {"ok":True,"time_utc":datetime.now(timezone.utc).isoformat(),"queue":dict(q) if q else {},"latest_run":dict(latest) if latest else None,"latest_success_at":latest_success["finished_at"] if latest_success else None}
