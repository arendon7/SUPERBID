from __future__ import annotations

import os
from typing import Any

import httpx

from .attachments import extract_json_attachments
from .bid_history import extract_bid_history
from .fetchers import UA, validate_url
from .json_adapter import extract_offer_observations, looks_like_offer
from .parsers import lot_id_from_url
from .provenance import save_provenance
from .storage import Store
from .storage_extensions import save_attachments, save_bid_history

PUBLIC_SEO_ENDPOINT = "https://offer-query.superbid.net/seo/offers/"


def public_lot_params(lot_url: str) -> dict[str, str]:
    """Build the stateless public recipe confirmed by the v0.13 live probe."""
    validate_url(lot_url)
    return {
        "portalId": os.getenv("SUPERBID_PUBLIC_PORTAL_ID", "[17]"),
        "locale": os.getenv("SUPERBID_PUBLIC_LOCALE", "es_CO"),
        "timeZoneId": os.getenv("SUPERBID_PUBLIC_TIMEZONE", "UTC"),
        "requestOrigin": os.getenv("SUPERBID_PUBLIC_REQUEST_ORIGIN", "marketplace"),
        "urlSeo": lot_url,
    }


def _iter_dicts(obj: Any):
    if isinstance(obj, dict):
        yield obj
        for value in obj.values():
            yield from _iter_dicts(value)
    elif isinstance(obj, list):
        for value in obj:
            yield from _iter_dicts(value)


def _target_offer(payload: Any, external_lot_id: str) -> dict | None:
    for obj in _iter_dicts(payload):
        if looks_like_offer(obj) and str(obj.get("id")) == str(external_lot_id):
            return obj
    return None


async def fetch_public_lot(
    lot_url: str,
    *,
    client: httpx.AsyncClient | None = None,
) -> dict:
    """Fetch one public lot without browser state, cookies or opaque filters."""
    expected = lot_id_from_url(lot_url)
    params = public_lot_params(lot_url)
    headers = {
        "User-Agent": UA,
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "es-CO,es;q=0.9,en;q=0.7",
        "Origin": "https://www.superbid.com.co",
        "Referer": lot_url,
    }

    owns_client = client is None
    if client is None:
        client = httpx.AsyncClient(timeout=30, headers=headers, follow_redirects=True)

    try:
        response = await client.get(PUBLIC_SEO_ENDPOINT, params=params, headers=headers)
        response.raise_for_status()
        payload = response.json()
    finally:
        if owns_client:
            await client.aclose()

    observations = [
        obs for obs in extract_offer_observations(payload, source_url=lot_url)
        if obs.external_lot_id == expected
    ]
    if len(observations) != 1:
        raise RuntimeError(
            f"Public SEO endpoint returned {len(observations)} matching observations for lot {expected}."
        )

    target = _target_offer(payload, expected)
    attachments = extract_json_attachments(target) if target else []
    bids = extract_bid_history(target) if target else []

    return {
        "status": response.status_code,
        "endpoint": PUBLIC_SEO_ENDPOINT,
        "external_lot_id": expected,
        "observation": observations[0],
        "attachments": attachments,
        "bid_history": bids,
    }


async def capture_direct_public(lot_url: str, *, db: str | None = None) -> dict:
    result = await fetch_public_lot(lot_url)
    obs = result["observation"]
    saved = attachments_saved = bids_saved = 0

    if db:
        store = Store(db)
        store.init()
        lot_id = store.save(obs)
        fields = {
            "title": obs.title is not None,
            "seller": obs.seller is not None,
            "initial_bid_cop": obs.initial_bid_cop is not None,
            "displayed_price_cop": obs.displayed_price_cop is not None,
            "bid_count": obs.bid_count is not None,
            "closes_at_text": obs.closes_at_text is not None,
            "outcome": obs.outcome.value != "UNKNOWN",
        }
        save_provenance(
            store.conn,
            lot_id,
            source_type="superbid_public_http",
            source_url=lot_url,
            fields=fields,
            confidence=0.97 if obs.outcome.value == "SOLD_CONFIRMED" else 0.93,
            note="Stateless read-only public SEO endpoint; no cookies, auth or opaque filter.",
        )
        attachments_saved = save_attachments(store.conn, lot_id, result["attachments"])
        bids_saved = save_bid_history(store.conn, lot_id, result["bid_history"])
        saved = 1

    return {
        "mode": "direct_http",
        "status": result["status"],
        "lots_found": [obs.model_dump(mode="json")],
        "saved": saved,
        "attachments_saved": attachments_saved,
        "bids_saved": bids_saved,
        "errors": [],
    }
