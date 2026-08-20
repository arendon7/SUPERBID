from __future__ import annotations

import os
import re
import unicodedata
from typing import Any

import httpx

from .fetchers import UA
from .json_adapter import offer_dict_to_observation, looks_like_offer
from .operations import enqueue_lot
from .provenance import save_provenance

PUBLIC_OFFERS_ENDPOINT = "https://offer-query.superbid.net/offers/"
DEFAULT_VEHICLE_CATEGORY_IDS = {10000, 10022}  # Autos, Camiones. Motos (10012) is opt-in.


def vehicle_category_ids() -> set[int]:
    raw = os.getenv("SUPERBID_VEHICLE_CATEGORY_IDS", "10000,10022")
    out = set()
    for item in raw.split(","):
        try:
            out.add(int(item.strip()))
        except (TypeError, ValueError):
            continue
    return out or set(DEFAULT_VEHICLE_CATEGORY_IDS)


def public_open_offer_params(page_number: int, page_size: int = 24) -> dict[str, str]:
    return {
        "portalId": os.getenv("SUPERBID_PUBLIC_PORTAL_ID", "[17]"),
        "requestOrigin": os.getenv("SUPERBID_PUBLIC_REQUEST_ORIGIN", "marketplace"),
        "locale": os.getenv("SUPERBID_PUBLIC_LOCALE", "es_CO"),
        "timeZoneId": os.getenv("SUPERBID_PUBLIC_TIMEZONE", "UTC"),
        "searchType": "opened",
        "pageNumber": str(max(1, int(page_number))),
        "pageSize": str(max(1, min(int(page_size), 100))),
        "preOrderBy": "orderByFirstOpenedOffers",
    }


def _headers() -> dict[str, str]:
    return {
        "User-Agent": UA,
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "es-CO,es;q=0.9,en;q=0.7",
        "Origin": "https://www.superbid.com.co",
        "Referer": "https://www.superbid.com.co/",
    }


def offer_category_id(offer: dict) -> int | None:
    product = offer.get("product") if isinstance(offer.get("product"), dict) else {}
    subcategory = product.get("subCategory") if isinstance(product.get("subCategory"), dict) else {}
    category = subcategory.get("category") if isinstance(subcategory.get("category"), dict) else {}
    value = category.get("id")
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def is_vehicle_offer(offer: dict, category_ids: set[int] | None = None) -> bool:
    category_ids = category_ids or vehicle_category_ids()
    return offer_category_id(offer) in category_ids


def _slug(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text or "")
    ascii_text = "".join(ch for ch in normalized if not unicodedata.combining(ch))
    ascii_text = ascii_text.lower()
    ascii_text = re.sub(r"[^a-z0-9]+", "-", ascii_text).strip("-")
    return ascii_text[:180] or "lote"


def public_lot_url(offer: dict) -> str:
    lot_id = str(offer.get("id"))
    product = offer.get("product") if isinstance(offer.get("product"), dict) else {}
    title = product.get("shortDesc") or offer.get("title") or offer.get("description") or f"lote-{lot_id}"
    return f"https://www.superbid.com.co/oferta/{_slug(str(title))}-{lot_id}"


async def fetch_open_offers_page(
    page_number: int,
    *,
    page_size: int = 24,
    client: httpx.AsyncClient | None = None,
) -> dict:
    owns_client = client is None
    if client is None:
        client = httpx.AsyncClient(timeout=30, headers=_headers(), follow_redirects=True)
    try:
        response = await client.get(
            PUBLIC_OFFERS_ENDPOINT,
            params=public_open_offer_params(page_number, page_size),
            headers=_headers(),
        )
        response.raise_for_status()
        payload = response.json()
    finally:
        if owns_client:
            await client.aclose()

    offers = payload.get("offers") if isinstance(payload, dict) else None
    return {
        "status": response.status_code,
        "page_number": page_number,
        "page_size": page_size,
        "total": payload.get("total") if isinstance(payload, dict) else None,
        "offers": offers if isinstance(offers, list) else [],
    }


async def discover_open_vehicles_direct(
    store,
    *,
    max_pages: int | None = None,
    page_size: int | None = None,
    client: httpx.AsyncClient | None = None,
) -> dict:
    max_pages = max_pages or int(os.getenv("SUPERBID_DIRECT_DISCOVERY_MAX_PAGES", "25"))
    page_size = page_size or int(os.getenv("SUPERBID_DIRECT_DISCOVERY_PAGE_SIZE", "24"))
    max_pages = max(1, min(max_pages, 100))
    page_size = max(1, min(page_size, 100))
    categories = vehicle_category_ids()

    owns_client = client is None
    if client is None:
        client = httpx.AsyncClient(timeout=30, headers=_headers(), follow_redirects=True)

    pages_scanned = total_seen = vehicle_seen = queued = saved = 0
    total_reported = None
    seen_ids: set[str] = set()
    try:
        for page_number in range(1, max_pages + 1):
            page = await fetch_open_offers_page(page_number, page_size=page_size, client=client)
            pages_scanned += 1
            offers = page["offers"]
            total_reported = page.get("total") if total_reported is None else total_reported
            if not offers:
                break

            total_seen += len(offers)
            for offer in offers:
                if not isinstance(offer, dict) or not looks_like_offer(offer):
                    continue
                if not is_vehicle_offer(offer, categories):
                    continue
                external_id = str(offer.get("id"))
                if external_id in seen_ids:
                    continue
                seen_ids.add(external_id)
                vehicle_seen += 1

                url = public_lot_url(offer)
                obs = offer_dict_to_observation(offer, url)
                lot_id = store.save(obs)
                saved += 1
                save_provenance(
                    store.conn,
                    lot_id,
                    source_type="superbid_public_http_discovery",
                    source_url=PUBLIC_OFFERS_ENDPOINT,
                    fields={
                        "title": obs.title is not None,
                        "displayed_price_cop": obs.displayed_price_cop is not None,
                        "closes_at_text": obs.closes_at_text is not None,
                        "category_id": offer_category_id(offer),
                    },
                    confidence=0.91,
                    note="Public opened-offers endpoint without auth, cookies, filter or fieldList.",
                )
                enqueue_lot(store.conn, external_id, url, obs.closes_at_text, priority=100)
                queued += 1

            if total_reported is not None and page_number * page_size >= int(total_reported):
                break
    finally:
        if owns_client:
            await client.aclose()

    return {
        "mode": "direct_http_discovery",
        "pages_scanned": pages_scanned,
        "total_reported": total_reported,
        "offers_seen": total_seen,
        "vehicle_lots_seen": vehicle_seen,
        "saved": saved,
        "queued": queued,
        "vehicle_category_ids": sorted(categories),
    }
