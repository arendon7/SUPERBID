from __future__ import annotations

import os
from datetime import datetime, timezone

from .network_capture import capture_public_json
from .operations import enqueue_lot, start_run, finish_run
from .discovery_urls import build_paginated_urls, is_paginated_source


def _max_pages() -> int:
    try:
        return max(1, min(int(os.getenv("SUPERBID_DISCOVERY_MAX_PAGES", "10")), 100))
    except ValueError:
        return 10


def _page_size() -> int:
    try:
        return max(1, min(int(os.getenv("SUPERBID_DISCOVERY_PAGE_SIZE", "30")), 200))
    except ValueError:
        return 30


async def _capture_source_page(store, source_url: str, seconds: int) -> dict:
    return await capture_public_json(source_url, seconds=seconds, db=store.path, dump_dir=None)


async def discover_from_source(store, source_url: str, seconds: int = 12, source_type: str = "listing") -> dict:
    """Discover lots from a single source or a configured paginated category/search page.

    Pagination stops after the first empty page after page 1. This prevents repeatedly
    scanning a fixed max-page window after inventory becomes sparse.
    """
    run_id = start_run(store.conn, "DISCOVERY", source_url)
    pages = build_paginated_urls(source_url, max_pages=_max_pages(), page_size=_page_size()) if is_paginated_source(source_type) else [source_url]
    aggregate = {"lots_found": [], "saved": 0, "attachments_saved": 0, "bids_saved": 0, "errors": [], "pages_scanned": 0}
    seen = set()
    try:
        for index, page_url in enumerate(pages, start=1):
            result = await _capture_source_page(store, page_url, seconds)
            aggregate["pages_scanned"] += 1
            page_lots = result.get("lots_found") or []
            aggregate["saved"] += int(result.get("saved", 0) or 0)
            aggregate["attachments_saved"] += int(result.get("attachments_saved", 0) or 0)
            aggregate["bids_saved"] += int(result.get("bids_saved", 0) or 0)
            aggregate["errors"].extend(result.get("errors") or [])
            for lot in page_lots:
                external_id = str(lot["external_lot_id"])
                if external_id in seen:
                    continue
                seen.add(external_id)
                aggregate["lots_found"].append(lot)
                enqueue_lot(store.conn, external_id, lot.get("url") or page_url, lot.get("closes_at_text"), priority=100)
            if is_paginated_source(source_type) and index > 1 and not page_lots:
                break

        finish_run(store.conn, run_id, ok=True, lots_found=len(aggregate["lots_found"]), lots_saved=aggregate["saved"], attachments_saved=aggregate["attachments_saved"], bids_saved=aggregate["bids_saved"])
        store.conn.execute("UPDATE discovery_sources SET last_scan_at=?,last_error=NULL WHERE url=?", (datetime.now(timezone.utc).isoformat(), source_url))
        store.conn.commit()
        return aggregate
    except Exception as exc:
        finish_run(store.conn, run_id, ok=False, error=str(exc))
        store.conn.execute("UPDATE discovery_sources SET last_scan_at=?,last_error=? WHERE url=?", (datetime.now(timezone.utc).isoformat(), str(exc), source_url))
        store.conn.commit()
        raise


def add_discovery_source(store, url: str, source_type: str = "listing"):
    now = datetime.now(timezone.utc).isoformat()
    store.conn.execute(
        """INSERT INTO discovery_sources(url,enabled,source_type,created_at) VALUES (?,1,?,?)
        ON CONFLICT(url) DO UPDATE SET enabled=1,source_type=excluded.source_type""",
        (url, source_type, now),
    )
    store.conn.commit()


def sources(store) -> list[dict]:
    return [dict(r) for r in store.conn.execute("SELECT * FROM discovery_sources WHERE enabled=1 ORDER BY id").fetchall()]
