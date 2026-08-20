from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import urlsplit

from .fetchers import UA, validate_url
from .json_adapter import extract_offer_observations, looks_like_offer
from .storage import Store
from .attachments import extract_json_attachments, extract_html_attachments
from .bid_history import extract_bid_history
from .storage_extensions import save_attachments, save_bid_history
from .provenance import save_provenance
from .parsers import lot_id_from_url
from .probe_sanitize import endpoint_signature, safe_shape


def _expected_lot_id(url: str) -> str | None:
    try:
        return lot_id_from_url(url)
    except Exception:
        return None


def _iter_dicts(obj):
    if isinstance(obj, dict):
        yield obj
        for value in obj.values():
            yield from _iter_dicts(value)
    elif isinstance(obj, list):
        for value in obj:
            yield from _iter_dicts(value)


def _offer_dict_for(payload, external_lot_id: str):
    for obj in _iter_dicts(payload):
        if looks_like_offer(obj) and str(obj.get("id")) == str(external_lot_id):
            yield obj


def _relevant_html_attachments(items: list[dict]) -> list[dict]:
    # Avoid attaching generic footer privacy/corporate PDFs to every auction lot.
    return [x for x in items if x.get("kind") in {"PERITAJE", "CONDICIONES", "CONTRATO"}]


async def capture_public_json(url: str, seconds: int = 12, dump_dir: str | None = None, db: str | None = None) -> dict:
    validate_url(url)
    try:
        from playwright.async_api import async_playwright
    except ImportError as exc:
        raise RuntimeError('Instale: pip install -e ".[browser]" && playwright install chromium') from exc

    expected = _expected_lot_id(url)
    dumps = Path(dump_dir) if dump_dir else None
    if dumps:
        dumps.mkdir(parents=True, exist_ok=True)

    candidates = []
    observations = {}
    attachments_by_lot: dict[str, list[dict]] = {}
    bids_by_lot: dict[str, list[dict]] = {}
    html_attachments = []
    errors = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(user_agent=UA, locale="es-CO")
        page = await context.new_page()

        async def handle(resp):
            try:
                ct = (resp.headers.get("content-type") or "").lower()
                rt = resp.request.resource_type
                if "json" not in ct and rt not in {"xhr", "fetch"}:
                    return
                candidates.append({
                    "endpoint": endpoint_signature(resp.url),
                    "status": resp.status,
                    "resource_type": rt,
                    "content_type": ct,
                })
                try:
                    payload = await resp.json()
                except Exception:
                    return

                obs_list = extract_offer_observations(payload, source_url=url)
                if expected:
                    obs_list = [o for o in obs_list if str(o.external_lot_id) == expected]
                for obs in obs_list:
                    observations[obs.external_lot_id] = obs

                # Associate lot-specific documents only from the matching offer object,
                # never from a multi-offer recommendation/list payload as a whole.
                if expected:
                    for offer_obj in _offer_dict_for(payload, expected):
                        attachments_by_lot.setdefault(expected, []).extend(extract_json_attachments(offer_obj))
                        bids_by_lot.setdefault(expected, []).extend(extract_bid_history(offer_obj))
                    # Dedicated history/document APIs can carry the lot id in their URL.
                    if expected in resp.url:
                        bids_by_lot.setdefault(expected, []).extend(extract_bid_history(payload))
                elif len(obs_list) == 1:
                    lot_key = obs_list[0].external_lot_id
                    attachments_by_lot.setdefault(lot_key, []).extend(extract_json_attachments(payload))
                    bids_by_lot.setdefault(lot_key, []).extend(extract_bid_history(payload))

                if dumps:
                    safe_dump = {
                        "endpoint": endpoint_signature(resp.url),
                        "shape": safe_shape(payload),
                        "observations": [
                            {
                                "external_lot_id": o.external_lot_id,
                                "outcome": o.outcome.value,
                                "displayed_price_cop": o.displayed_price_cop,
                                "bid_count": o.bid_count,
                                "closes_at_text": o.closes_at_text,
                            }
                            for o in obs_list
                        ],
                    }
                    (dumps / f"{len(candidates):04d}.json").write_text(
                        json.dumps(safe_dump, ensure_ascii=False, indent=2), encoding="utf-8"
                    )
            except Exception as exc:
                errors.append(str(exc))

        page.on("response", handle)
        await page.goto(url, wait_until="domcontentloaded", timeout=60000)
        await page.wait_for_timeout(seconds * 1000)
        try:
            html_attachments = _relevant_html_attachments(
                extract_html_attachments(url, await page.content())
            )
        except Exception as exc:
            errors.append(f"html_attachments: {exc}")
        await browser.close()

    if expected and expected in observations:
        attachments_by_lot.setdefault(expected, []).extend(html_attachments)

    saved = attachments_saved = bids_saved = 0
    if db:
        store = Store(db)
        store.init()
        for obs in observations.values():
            saved_lot_id = store.save(obs)
            fields = {
                "title": obs.title is not None,
                "seller": obs.seller is not None,
                "initial_bid_cop": obs.initial_bid_cop is not None,
                "displayed_price_cop": obs.displayed_price_cop is not None,
                "bid_count": obs.bid_count is not None,
                "closes_at_text": obs.closes_at_text is not None,
                "outcome": obs.outcome.value != "UNKNOWN",
            }
            confidence = .98 if obs.outcome.value == "SOLD_CONFIRMED" else .90
            save_provenance(
                store.conn, saved_lot_id,
                source_type="superbid_public_json", source_url=obs.url,
                fields=fields, confidence=confidence,
                note="Structured public response observed while rendering Superbid.",
            )
            lot_atts = {a["url"]: a for a in attachments_by_lot.get(obs.external_lot_id, [])}
            attachments_saved += save_attachments(store.conn, saved_lot_id, list(lot_atts.values()))
            bids_saved += save_bid_history(store.conn, saved_lot_id, bids_by_lot.get(obs.external_lot_id, []))
            saved += 1

    selected_attachments = []
    selected_bids = []
    for lot_key in observations:
        selected_attachments.extend(attachments_by_lot.get(lot_key, []))
        selected_bids.extend(bids_by_lot.get(lot_key, []))
    selected_attachments = list({a["url"]: a for a in selected_attachments}.values())

    return {
        "page_url": url,
        "expected_lot_id": expected,
        "candidate_responses": candidates,
        "lots_found": [o.model_dump(mode="json") for o in observations.values()],
        "saved": saved,
        "attachments_saved": attachments_saved,
        "bids_saved": bids_saved,
        "attachments_found": selected_attachments,
        "bid_history_found": selected_bids,
        "errors": errors,
    }
