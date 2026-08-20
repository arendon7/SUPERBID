from __future__ import annotations

import json
import sqlite3
from dataclasses import asdict
from .valuation import CostProfile

SCHEMA = """
CREATE TABLE IF NOT EXISTS app_settings (
  key TEXT PRIMARY KEY,
  value_json TEXT NOT NULL,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""

DEFAULT_KEY = "default_cost_profile"


def init_settings(conn: sqlite3.Connection):
    conn.executescript(SCHEMA)
    conn.commit()


def get_cost_profile(conn: sqlite3.Connection) -> CostProfile:
    init_settings(conn)
    row = conn.execute(
        "SELECT value_json FROM app_settings WHERE key=?",
        (DEFAULT_KEY,),
    ).fetchone()
    if not row:
        return CostProfile()
    try:
        data = json.loads(row[0])
        return CostProfile(**data)
    except Exception:
        return CostProfile()


def set_cost_profile(conn: sqlite3.Connection, profile: CostProfile):
    init_settings(conn)
    conn.execute(
        """
        INSERT INTO app_settings(key,value_json,updated_at)
        VALUES (?,?,CURRENT_TIMESTAMP)
        ON CONFLICT(key) DO UPDATE SET
          value_json=excluded.value_json,
          updated_at=CURRENT_TIMESTAMP
        """,
        (DEFAULT_KEY, json.dumps(asdict(profile), ensure_ascii=False)),
    )
    conn.commit()
