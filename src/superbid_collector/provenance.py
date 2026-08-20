from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone

SCHEMA = """
CREATE TABLE IF NOT EXISTS lot_provenance (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  lot_id INTEGER NOT NULL REFERENCES lots(id) ON DELETE CASCADE,
  source_type TEXT NOT NULL,
  source_url TEXT NOT NULL,
  observed_at TEXT NOT NULL,
  fields_json TEXT NOT NULL DEFAULT '{}',
  confidence REAL NOT NULL DEFAULT 0,
  note TEXT,
  UNIQUE(lot_id,source_type,source_url)
);
CREATE INDEX IF NOT EXISTS idx_lot_provenance_lot ON lot_provenance(lot_id,observed_at DESC);
"""

def init_provenance(conn: sqlite3.Connection):
    conn.executescript(SCHEMA); conn.commit()

def save_provenance(conn: sqlite3.Connection, lot_id:int, *, source_type:str, source_url:str, fields:dict|None=None, confidence:float=0.0, note:str|None=None, observed_at:str|None=None):
    init_provenance(conn)
    observed_at=observed_at or datetime.now(timezone.utc).isoformat()
    conn.execute("""INSERT INTO lot_provenance(lot_id,source_type,source_url,observed_at,fields_json,confidence,note) VALUES (?,?,?,?,?,?,?) ON CONFLICT(lot_id,source_type,source_url) DO UPDATE SET observed_at=excluded.observed_at,fields_json=excluded.fields_json,confidence=MAX(lot_provenance.confidence,excluded.confidence),note=COALESCE(excluded.note,lot_provenance.note)""",(lot_id,source_type,source_url,observed_at,json.dumps(fields or {},ensure_ascii=False),max(0.0,min(1.0,float(confidence))),note))
    conn.commit()

def provenance_for_lot(conn:sqlite3.Connection,lot_id:int)->list[dict]:
    init_provenance(conn)
    rows=conn.execute("SELECT source_type,source_url,observed_at,fields_json,confidence,note FROM lot_provenance WHERE lot_id=? ORDER BY confidence DESC,observed_at DESC",(lot_id,)).fetchall()
    out=[]
    for r in rows:
        x=dict(r)
        try: x["fields"]=json.loads(x.pop("fields_json") or "{}")
        except Exception: x["fields"]={}; x.pop("fields_json",None)
        out.append(x)
    return out

def quality_label(source_type:str,confidence:float)->str:
    s=(source_type or "").lower()
    if s in {"sold_confirmation","purchase_record","buyer_record"} and confidence>=.95: return "CONFIRMADO"
    if s in {"superbid_json","superbid_public_json"} and confidence>=.80: return "ALTA"
    if s in {"closing_snapshot","closed_observed"} and confidence>=.60: return "OBSERVADO"
    if "bootstrap" in s or "search_index" in s: return "HISTORICO_INDEXADO"
    return "REFERENCIAL"
