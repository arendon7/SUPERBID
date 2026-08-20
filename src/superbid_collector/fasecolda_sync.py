from __future__ import annotations

import sqlite3

from .fasecolda import fasecolda_record_key
from .supabase_sync import SupabaseREST


def _dicts(conn: sqlite3.Connection, sql: str):
    return [dict(r) for r in conn.execute(sql).fetchall()]


def sync_fasecolda(conn: sqlite3.Connection, remote: SupabaseREST, batch_size: int = 500) -> int:
    """Replicate local Fasecolda guide rows idempotently using deterministic record_key."""
    rows = []
    for r in _dicts(conn, "SELECT * FROM fasecolda_values ORDER BY id"):
        record_key = r.get("record_key") or fasecolda_record_key(
            source_file=r["source_file"], code=r["code"] or "",
            homologous_code=r["homologous_code"] or "", brand=r["brand"] or "",
            vehicle_class=r["vehicle_class"] or "", reference1=r["reference1"] or "",
            reference2=r["reference2"] or "", reference3=r["reference3"] or "",
            service=r["service"] or "", model_year=int(r["model_year"]),
        )
        rows.append({
            "record_key": record_key, "source_file": r["source_file"],
            "imported_at": r["imported_at"], "code": r["code"],
            "homologous_code": r["homologous_code"], "brand": r["brand"],
            "vehicle_class": r["vehicle_class"], "reference1": r["reference1"],
            "reference2": r["reference2"], "reference3": r["reference3"],
            "service": r["service"], "model_year": r["model_year"],
            "value_cop": r["value_cop"],
        })
    for i in range(0, len(rows), batch_size):
        remote.upsert("fasecolda_values", rows[i:i + batch_size], on_conflict="record_key", returning=False)
    return len(rows)
