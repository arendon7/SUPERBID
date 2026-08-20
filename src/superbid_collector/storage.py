from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from .models import LotObservation
from .market_storage import init_market_schema
from .storage_extensions import init_extensions
from .settings import init_settings
from .operations import init_operations
from .provenance import init_provenance, save_provenance


SCHEMA = """
PRAGMA journal_mode=WAL;

CREATE TABLE IF NOT EXISTS lots (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  source TEXT NOT NULL,
  external_lot_id TEXT NOT NULL,
  url TEXT NOT NULL,
  title TEXT,
  brand TEXT,
  line TEXT,
  version TEXT,
  model_year INTEGER,
  plate TEXT,
  plate_is_partial INTEGER NOT NULL DEFAULT 0,
  mileage_km INTEGER,
  engine_cc INTEGER,
  fuel TEXT,
  transmission TEXT,
  drivetrain TEXT,
  city TEXT,
  seller TEXT,
  initial_bid_cop INTEGER,
  first_seen_at TEXT NOT NULL,
  last_seen_at TEXT NOT NULL,
  UNIQUE(source, external_lot_id)
);

CREATE TABLE IF NOT EXISTS lot_snapshots (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  lot_id INTEGER NOT NULL REFERENCES lots(id) ON DELETE CASCADE,
  observed_at TEXT NOT NULL,
  displayed_price_cop INTEGER,
  displayed_price_label TEXT,
  bid_count INTEGER,
  status_text TEXT,
  outcome TEXT NOT NULL,
  closes_at_text TEXT,
  evidence_json TEXT,
  UNIQUE(lot_id, observed_at)
);

CREATE TABLE IF NOT EXISTS lot_outcomes (
  lot_id INTEGER PRIMARY KEY REFERENCES lots(id) ON DELETE CASCADE,
  outcome TEXT NOT NULL,
  closing_price_observed_cop INTEGER,
  sale_price_confirmed_cop INTEGER,
  confidence REAL NOT NULL DEFAULT 0,
  updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_lots_vehicle ON lots(brand, model_year);
CREATE INDEX IF NOT EXISTS idx_snapshots_lot_time ON lot_snapshots(lot_id, observed_at DESC);
"""


class Store:
    def __init__(self, path: str | Path):
        self.path = str(path)
        self.conn = sqlite3.connect(self.path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys=ON")

    def init(self) -> None:
        self.conn.executescript(SCHEMA)
        init_market_schema(self.conn)
        init_extensions(self.conn)
        init_settings(self.conn)
        init_operations(self.conn)
        init_provenance(self.conn)
        self.conn.commit()

    def save(self, obs: LotObservation) -> int:
        ts = obs.observed_at.isoformat()
        self.conn.execute(
            """
            INSERT INTO lots (
              source, external_lot_id, url, title, brand, line, version,
              model_year, plate, plate_is_partial, mileage_km, engine_cc,
              fuel, transmission, drivetrain, city, seller, initial_bid_cop,
              first_seen_at, last_seen_at
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            ON CONFLICT(source, external_lot_id) DO UPDATE SET
              url=excluded.url,
              title=COALESCE(excluded.title, lots.title),
              brand=COALESCE(excluded.brand, lots.brand),
              line=COALESCE(excluded.line, lots.line),
              version=COALESCE(excluded.version, lots.version),
              model_year=COALESCE(excluded.model_year, lots.model_year),
              plate=COALESCE(excluded.plate, lots.plate),
              plate_is_partial=excluded.plate_is_partial,
              mileage_km=COALESCE(excluded.mileage_km, lots.mileage_km),
              engine_cc=COALESCE(excluded.engine_cc, lots.engine_cc),
              fuel=COALESCE(excluded.fuel, lots.fuel),
              transmission=COALESCE(excluded.transmission, lots.transmission),
              drivetrain=COALESCE(excluded.drivetrain, lots.drivetrain),
              city=COALESCE(excluded.city, lots.city),
              seller=COALESCE(excluded.seller, lots.seller),
              initial_bid_cop=COALESCE(excluded.initial_bid_cop, lots.initial_bid_cop),
              last_seen_at=excluded.last_seen_at
            """,
            (
                obs.source, obs.external_lot_id, obs.url, obs.title, obs.brand,
                obs.line, obs.version, obs.model_year, obs.plate,
                int(obs.plate_is_partial), obs.mileage_km, obs.engine_cc,
                obs.fuel, obs.transmission, obs.drivetrain, obs.city, obs.seller,
                obs.initial_bid_cop, ts, ts,
            ),
        )
        row = self.conn.execute(
            "SELECT id FROM lots WHERE source=? AND external_lot_id=?",
            (obs.source, obs.external_lot_id),
        ).fetchone()
        lot_id = int(row["id"])

        self.conn.execute(
            """
            INSERT OR IGNORE INTO lot_snapshots (
              lot_id, observed_at, displayed_price_cop, displayed_price_label,
              bid_count, status_text, outcome, closes_at_text, evidence_json
            ) VALUES (?,?,?,?,?,?,?,?,?)
            """,
            (
                lot_id, ts, obs.displayed_price_cop, obs.displayed_price_label,
                obs.bid_count, obs.status_text, obs.outcome.value,
                obs.closes_at_text, json.dumps(obs.evidence, ensure_ascii=False),
            ),
        )

        closing_observed = (
            obs.displayed_price_cop
            if obs.outcome.value in {"CLOSED_OBSERVED", "SOLD_CONFIRMED", "CONDITIONAL", "AFTER_MARKET"}
            else None
        )
        sale_confirmed = obs.displayed_price_cop if obs.outcome.value == "SOLD_CONFIRMED" else None
        confidence = 1.0 if obs.outcome.value == "SOLD_CONFIRMED" else (0.65 if closing_observed else 0.0)

        self.conn.execute(
            """
            INSERT INTO lot_outcomes (
              lot_id, outcome, closing_price_observed_cop,
              sale_price_confirmed_cop, confidence, updated_at
            ) VALUES (?,?,?,?,?,?)
            ON CONFLICT(lot_id) DO UPDATE SET
              outcome=excluded.outcome,
              closing_price_observed_cop=COALESCE(excluded.closing_price_observed_cop, lot_outcomes.closing_price_observed_cop),
              sale_price_confirmed_cop=COALESCE(excluded.sale_price_confirmed_cop, lot_outcomes.sale_price_confirmed_cop),
              confidence=MAX(lot_outcomes.confidence, excluded.confidence),
              updated_at=excluded.updated_at
            """,
            (lot_id, obs.outcome.value, closing_observed, sale_confirmed, confidence, ts),
        )

        self.conn.commit()

        if obs.outcome.value == "SOLD_CONFIRMED":
            save_provenance(
                self.conn,lot_id,
                source_type="sold_confirmation",
                source_url=obs.url,
                fields={"sale_price_confirmed_cop": obs.displayed_price_cop is not None},
                confidence=1.0 if obs.displayed_price_cop is not None else 0.95,
                note="Explicit sold/adjudicated status observed in source."
            )
        elif obs.outcome.value in {"CLOSED_OBSERVED","CONDITIONAL","AFTER_MARKET"}:
            save_provenance(
                self.conn,lot_id,
                source_type="closing_snapshot",
                source_url=obs.url,
                fields={"closing_price_observed_cop": obs.displayed_price_cop is not None},
                confidence=0.65,
                note="Closing value observed; not promoted to confirmed sale without explicit evidence."
            )

        return lot_id
