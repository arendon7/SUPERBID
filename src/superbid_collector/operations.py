from __future__ import annotations

import sqlite3
from datetime import datetime, timezone, timedelta
from urllib.parse import urlparse

from dateutil import parser as dtparser


OPS_SCHEMA = """
CREATE TABLE IF NOT EXISTS discovery_sources (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  url TEXT NOT NULL UNIQUE,
  enabled INTEGER NOT NULL DEFAULT 1,
  source_type TEXT NOT NULL DEFAULT 'listing',
  last_scan_at TEXT,
  last_error TEXT,
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS collection_queue (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  external_lot_id TEXT NOT NULL UNIQUE,
  url TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'WATCH',
  next_run_at TEXT NOT NULL,
  last_run_at TEXT,
  last_success_at TEXT,
  consecutive_errors INTEGER NOT NULL DEFAULT 0,
  last_error TEXT,
  closes_at_text TEXT,
  priority INTEGER NOT NULL DEFAULT 100,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS collection_runs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  run_type TEXT NOT NULL,
  target TEXT,
  started_at TEXT NOT NULL,
  finished_at TEXT,
  ok INTEGER,
  lots_found INTEGER NOT NULL DEFAULT 0,
  lots_saved INTEGER NOT NULL DEFAULT 0,
  attachments_saved INTEGER NOT NULL DEFAULT 0,
  bids_saved INTEGER NOT NULL DEFAULT 0,
  error TEXT
);

CREATE INDEX IF NOT EXISTS idx_queue_due
ON collection_queue(status,next_run_at,priority);

CREATE INDEX IF NOT EXISTS idx_runs_started
ON collection_runs(started_at DESC);
"""


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def init_operations(conn: sqlite3.Connection):
    conn.executescript(OPS_SCHEMA)
    conn.commit()


def parse_close(text: str | None) -> datetime | None:
    if not text:
        return None
    try:
        d = dtparser.parse(text, dayfirst=True, fuzzy=True)
        if d.tzinfo is None:
            d = d.replace(tzinfo=timezone(timedelta(hours=-5)))
        return d.astimezone(timezone.utc)
    except Exception:
        return None


def interval_for_close(closes_at_text: str | None) -> int:
    d = parse_close(closes_at_text)
    if not d:
        return 4 * 3600
    remaining = (d - datetime.now(timezone.utc)).total_seconds()
    if remaining <= -2 * 3600:
        return 24 * 3600
    if remaining <= 0:
        return 60
    if remaining <= 15 * 60:
        return 60
    if remaining <= 2 * 3600:
        return 5 * 60
    if remaining <= 24 * 3600:
        return 30 * 60
    return 4 * 3600


def enqueue_lot(conn: sqlite3.Connection, external_lot_id: str, url: str, closes_at_text: str | None = None, priority: int = 100):
    init_operations(conn)
    now = datetime.now(timezone.utc)
    conn.execute("""
        INSERT INTO collection_queue(external_lot_id,url,status,next_run_at,closes_at_text,priority,created_at,updated_at)
        VALUES (?,?, 'WATCH', ?, ?, ?, ?, ?)
        ON CONFLICT(external_lot_id) DO UPDATE SET
          url=excluded.url,
          closes_at_text=COALESCE(excluded.closes_at_text,collection_queue.closes_at_text),
          priority=MIN(collection_queue.priority,excluded.priority),
          updated_at=excluded.updated_at
    """,(external_lot_id,url,now.isoformat(),closes_at_text,priority,now.isoformat(),now.isoformat()))
    conn.commit()


def due_lots(conn: sqlite3.Connection, limit: int = 50) -> list[dict]:
    init_operations(conn)
    rows = conn.execute("SELECT * FROM collection_queue WHERE status='WATCH' AND next_run_at<=? ORDER BY priority ASC,next_run_at ASC LIMIT ?",(now_iso(),limit)).fetchall()
    return [dict(r) for r in rows]


def mark_queue_result(conn: sqlite3.Connection, external_lot_id: str, *, ok: bool, closes_at_text: str | None = None, outcome: str | None = None, error: str | None = None):
    init_operations(conn)
    now = datetime.now(timezone.utc)
    row = conn.execute("SELECT * FROM collection_queue WHERE external_lot_id=?",(external_lot_id,)).fetchone()
    if not row:
        return
    close_text = closes_at_text or row["closes_at_text"]
    terminal = outcome in {"SOLD_CONFIRMED","NOT_SOLD","WITHDRAWN","NO_BID"}
    if terminal:
        status = "DONE"
        next_run = (now + timedelta(days=30)).isoformat()
    else:
        status = "WATCH"
        next_run = (now + timedelta(seconds=interval_for_close(close_text))).isoformat()
    errors = 0 if ok else int(row["consecutive_errors"] or 0) + 1
    if not ok:
        backoff = min(4*3600, 60 * (2 ** min(errors, 6)))
        next_run = (now + timedelta(seconds=backoff)).isoformat()
    conn.execute("""
        UPDATE collection_queue SET
          status=?,next_run_at=?,last_run_at=?,
          last_success_at=CASE WHEN ? THEN ? ELSE last_success_at END,
          consecutive_errors=?,last_error=?,closes_at_text=COALESCE(?,closes_at_text),
          updated_at=?
        WHERE external_lot_id=?
    """,(status,next_run,now.isoformat(),1 if ok else 0,now.isoformat(),errors,error,closes_at_text,now.isoformat(),external_lot_id))
    conn.commit()


def start_run(conn, run_type: str, target: str | None):
    init_operations(conn)
    cur = conn.execute("INSERT INTO collection_runs(run_type,target,started_at) VALUES (?,?,?)",(run_type,target,now_iso()))
    conn.commit()
    return int(cur.lastrowid)


def finish_run(conn, run_id: int, *, ok: bool, lots_found=0, lots_saved=0, attachments_saved=0, bids_saved=0, error: str | None=None):
    conn.execute("""
        UPDATE collection_runs SET finished_at=?,ok=?,lots_found=?,lots_saved=?,attachments_saved=?,bids_saved=?,error=? WHERE id=?
    """,(now_iso(),1 if ok else 0,lots_found,lots_saved,attachments_saved,bids_saved,error,run_id))
    conn.commit()
