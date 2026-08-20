from __future__ import annotations

import sqlite3
from datetime import datetime, timezone

MARKET_SCHEMA = """
CREATE TABLE IF NOT EXISTS market_comparables (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  lot_id INTEGER REFERENCES lots(id) ON DELETE CASCADE,
  source TEXT NOT NULL,
  external_id TEXT,
  url TEXT,
  observed_at TEXT NOT NULL,
  asking_price_cop INTEGER NOT NULL,
  brand TEXT,
  line TEXT,
  version TEXT,
  model_year INTEGER,
  mileage_km INTEGER,
  city TEXT,
  seller_type TEXT,
  match_score REAL,
  raw_json TEXT,
  UNIQUE(source, external_id, observed_at)
);
CREATE TABLE IF NOT EXISTS fasecolda_values (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  source_file TEXT NOT NULL,
  imported_at TEXT NOT NULL,
  code TEXT,
  homologous_code TEXT,
  brand TEXT,
  vehicle_class TEXT,
  reference1 TEXT,
  reference2 TEXT,
  reference3 TEXT,
  service TEXT,
  model_year INTEGER NOT NULL,
  value_cop INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_market_lot ON market_comparables(lot_id, observed_at DESC);
CREATE INDEX IF NOT EXISTS idx_fasecolda_vehicle ON fasecolda_values(brand, reference1, model_year);
"""

def init_market_schema(conn: sqlite3.Connection):
    conn.executescript(MARKET_SCHEMA); conn.commit()

def add_comparable(conn: sqlite3.Connection, *, lot_id:int|None, source:str, external_id:str|None, asking_price_cop:int, url:str|None=None, brand:str|None=None, line:str|None=None, version:str|None=None, model_year:int|None=None, mileage_km:int|None=None, city:str|None=None, seller_type:str|None=None, match_score:float|None=None, raw_json:str|None=None):
    init_market_schema(conn)
    conn.execute("""INSERT OR IGNORE INTO market_comparables (lot_id,source,external_id,url,observed_at,asking_price_cop,brand,line,version,model_year,mileage_km,city,seller_type,match_score,raw_json) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",(lot_id,source,external_id,url,datetime.now(timezone.utc).isoformat(),asking_price_cop,brand,line,version,model_year,mileage_km,city,seller_type,match_score,raw_json))
    conn.commit()
