from __future__ import annotations
import sqlite3
from datetime import datetime,timezone
EXT_SCHEMA="""
CREATE TABLE IF NOT EXISTS lot_attachments (id INTEGER PRIMARY KEY AUTOINCREMENT,lot_id INTEGER NOT NULL REFERENCES lots(id) ON DELETE CASCADE,name TEXT,url TEXT NOT NULL,kind TEXT NOT NULL,source TEXT,discovered_at TEXT NOT NULL,UNIQUE(lot_id,url));
CREATE TABLE IF NOT EXISTS lot_bid_history (id INTEGER PRIMARY KEY AUTOINCREMENT,lot_id INTEGER NOT NULL REFERENCES lots(id) ON DELETE CASCADE,sequence_no INTEGER,amount_cop INTEGER NOT NULL,bid_at_text TEXT,observed_at TEXT NOT NULL,UNIQUE(lot_id,amount_cop,bid_at_text));
CREATE INDEX IF NOT EXISTS idx_attachments_lot_kind ON lot_attachments(lot_id,kind);
CREATE INDEX IF NOT EXISTS idx_bid_history_lot ON lot_bid_history(lot_id,sequence_no,observed_at);
"""
def init_extensions(conn:sqlite3.Connection): conn.executescript(EXT_SCHEMA); conn.commit()
def save_attachments(conn,lot_id:int,attachments:list[dict]):
    init_extensions(conn); now=datetime.now(timezone.utc).isoformat(); added=0
    for a in attachments:
        cur=conn.execute("INSERT OR IGNORE INTO lot_attachments (lot_id,name,url,kind,source,discovered_at) VALUES (?,?,?,?,?,?)",(lot_id,a.get("name"),a["url"],a.get("kind","OTRO"),a.get("source"),now)); added+=max(cur.rowcount,0)
    conn.commit(); return added
def save_bid_history(conn,lot_id:int,bids:list[dict]):
    init_extensions(conn); now=datetime.now(timezone.utc).isoformat(); added=0
    for b in bids:
        cur=conn.execute("INSERT OR IGNORE INTO lot_bid_history (lot_id,sequence_no,amount_cop,bid_at_text,observed_at) VALUES (?,?,?,?,?)",(lot_id,b.get("sequence_no"),b["amount_cop"],b.get("bid_at_text"),now)); added+=max(cur.rowcount,0)
    conn.commit(); return added
