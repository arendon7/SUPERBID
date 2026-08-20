from __future__ import annotations

import asyncio
import json
import os
import time

from .storage import Store
from .discovery import discover_from_source, sources
from .network_capture import capture_public_json
from .direct_public_api import capture_direct_public
from .direct_discovery import discover_open_vehicles_direct, PUBLIC_OFFERS_ENDPOINT
from .operations import due_lots, mark_queue_result, start_run, finish_run

DB = os.getenv("SUPERBID_DB", "superbid.db")
DISCOVERY_INTERVAL = int(os.getenv("SUPERBID_DISCOVERY_INTERVAL", "3600"))
IDLE_SECONDS = int(os.getenv("SUPERBID_IDLE_SECONDS", "30"))
CAPTURE_SECONDS = int(os.getenv("SUPERBID_CAPTURE_SECONDS", "12"))
QUEUE_BATCH = int(os.getenv("SUPERBID_QUEUE_BATCH", "20"))
DIRECT_HTTP_ENABLED = os.getenv("SUPERBID_DIRECT_HTTP_ENABLED", "1").strip().lower() not in {"0", "false", "no"}
DIRECT_DISCOVERY_ENABLED = os.getenv("SUPERBID_DIRECT_DISCOVERY_ENABLED", "1").strip().lower() not in {"0", "false", "no"}
BROWSER_DISCOVERY_ALWAYS = os.getenv("SUPERBID_BROWSER_DISCOVERY_ALWAYS", "0").strip().lower() in {"1", "true", "yes"}


async def _capture_monitored_lot(url: str, db: str) -> tuple[dict, str]:
    direct_error = None
    if DIRECT_HTTP_ENABLED:
        try:
            result = await capture_direct_public(url, db=db)
            return result, "direct_http"
        except Exception as exc:
            direct_error = str(exc)

    result = await capture_public_json(url, seconds=CAPTURE_SECONDS, db=db)
    if direct_error:
        result.setdefault("errors", []).append(f"direct_http_fallback: {direct_error}")
    return result, "playwright_fallback"


async def capture_due(store: Store):
    rows = due_lots(store.conn, QUEUE_BATCH)
    results = []
    for q in rows:
        rid = start_run(store.conn, "LOT", q["url"])
        try:
            r, mode = await _capture_monitored_lot(q["url"], store.path)
            matched = None
            for lot in r.get("lots_found") or []:
                if str(lot.get("external_lot_id")) == str(q["external_lot_id"]):
                    matched = lot
                    break
            outcome = (matched or {}).get("outcome")
            mark_queue_result(
                store.conn,
                q["external_lot_id"],
                ok=True,
                closes_at_text=(matched or {}).get("closes_at_text"),
                outcome=outcome,
            )
            finish_run(
                store.conn,
                rid,
                ok=True,
                lots_found=len(r.get("lots_found") or []),
                lots_saved=r.get("saved", 0),
                attachments_saved=r.get("attachments_saved", 0),
                bids_saved=r.get("bids_saved", 0),
            )
            results.append({
                "id": q["external_lot_id"],
                "ok": True,
                "mode": mode,
                "errors": r.get("errors") or [],
            })
        except Exception as exc:
            mark_queue_result(
                store.conn,
                q["external_lot_id"],
                ok=False,
                error=str(exc),
            )
            finish_run(store.conn, rid, ok=False, error=str(exc))
            results.append({"id": q["external_lot_id"], "ok": False, "error": str(exc)})
        await asyncio.sleep(2)
    return results


async def _browser_discovery_sources(store: Store) -> list[dict]:
    out = []
    for src in sources(store):
        try:
            r = await discover_from_source(
                store,
                src["url"],
                CAPTURE_SECONDS,
                src.get("source_type") or "listing",
            )
            out.append({"mode": "playwright", "url": src["url"], "lots": len(r.get("lots_found") or [])})
        except Exception as exc:
            out.append({"mode": "playwright", "url": src["url"], "error": str(exc)})
        await asyncio.sleep(3)
    return out


async def discovery_cycle(store: Store):
    out = []
    direct_ok = False

    if DIRECT_DISCOVERY_ENABLED:
        rid = start_run(store.conn, "DISCOVERY_HTTP", PUBLIC_OFFERS_ENDPOINT)
        try:
            result = await discover_open_vehicles_direct(store)
            direct_ok = True
            finish_run(
                store.conn,
                rid,
                ok=True,
                lots_found=result.get("vehicle_auction_lots_seen", 0),
                lots_saved=result.get("saved", 0),
            )
            out.append(result)
        except Exception as exc:
            finish_run(store.conn, rid, ok=False, error=str(exc))
            out.append({"mode": "direct_http_discovery", "error": str(exc)})

    if BROWSER_DISCOVERY_ALWAYS or not direct_ok:
        out.extend(await _browser_discovery_sources(store))

    return out


def main():
    store = Store(DB)
    store.init()
    last_discovery = 0.0
    print(json.dumps({
        "worker": "v2_started",
        "db": DB,
        "direct_http_enabled": DIRECT_HTTP_ENABLED,
        "direct_discovery_enabled": DIRECT_DISCOVERY_ENABLED,
        "browser_discovery_always": BROWSER_DISCOVERY_ALWAYS,
    }, ensure_ascii=False))

    while True:
        now = time.time()
        if now - last_discovery >= DISCOVERY_INTERVAL:
            try:
                d = asyncio.run(discovery_cycle(store))
                print(json.dumps({"discovery": d}, ensure_ascii=False))
            except Exception as exc:
                print(json.dumps({"discovery_error": str(exc)}, ensure_ascii=False))
            last_discovery = now

        try:
            q = asyncio.run(capture_due(store))
            if q:
                print(json.dumps({"captures": q}, ensure_ascii=False))
        except Exception as exc:
            print(json.dumps({"queue_error": str(exc)}, ensure_ascii=False))
        time.sleep(IDLE_SECONDS)


if __name__ == "__main__":
    main()
