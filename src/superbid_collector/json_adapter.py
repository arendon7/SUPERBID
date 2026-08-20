from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Iterable
import re

from .models import LotObservation, Outcome
from .canonical import canonical_offer_url

MONEY_KEYS = (
    "amount", "value", "price", "bid_value", "bid_amount", "winner_bid_value",
    "current_bid", "current_max_bid", "current_min_bid", "max_bid", "min_bid",
)


def _walk(obj: Any) -> Iterable[dict]:
    if isinstance(obj, dict):
        yield obj
        for v in obj.values():
            yield from _walk(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from _walk(v)


def _num(v):
    if v is None or isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return int(v)
    if isinstance(v, str):
        # Monetary strings from the platform can include punctuation/currency labels.
        digits = re.sub(r"[^\d]", "", v)
        return int(digits) if digits else None
    return None


def _money_from(value: Any) -> int | None:
    direct = _num(value)
    if direct is not None:
        return direct
    if isinstance(value, dict):
        for key in MONEY_KEYS:
            if key in value:
                candidate = _money_from(value.get(key))
                if candidate is not None:
                    return candidate
    return None


def _nested_number(d: dict, *path: str) -> float | None:
    cur: Any = d
    for key in path:
        if not isinstance(cur, dict):
            return None
        cur = cur.get(key)
    if isinstance(cur, bool) or cur is None:
        return None
    if isinstance(cur, (int, float)):
        return float(cur)
    if isinstance(cur, str):
        try:
            return float(cur.replace("%", "").replace(",", ".").strip())
        except ValueError:
            return None
    return None


def _outcome(d: dict) -> Outcome:
    status = d.get("offer_status") or {}
    if not isinstance(status, dict):
        status = {}
    if status.get("sold") is True:
        return Outcome.SOLD_CONFIRMED
    if status.get("closed") is True or status.get("closed_to_bids") is True:
        return Outcome.CLOSED_OBSERVED
    if status.get("available") is True or status.get("give_your_bid") is True:
        return Outcome.ACTIVE
    txt = " ".join(str(d.get(k, "")) for k in ("status", "status_desc", "offer_status_desc")).lower()
    if "condicion" in txt or "conditional" in txt:
        return Outcome.CONDITIONAL
    if "after market" in txt or "post-subasta" in txt or "pós-leilão" in txt:
        return Outcome.AFTER_MARKET
    if "retir" in txt:
        return Outcome.WITHDRAWN
    return Outcome.UNKNOWN


def looks_like_offer(d: dict) -> bool:
    has_id = isinstance(d.get("id"), (int, str))
    has_auction_signal = any(k in d for k in (
        "offer_detail", "offer_status", "total_bids", "total_bidders",
        "lot_number", "end_date", "winner_bid",
    ))
    return has_id and has_auction_signal


def _product_name(d: dict) -> str | None:
    product = d.get("product")
    if isinstance(product, dict):
        for k in ("name", "title", "description", "desc"):
            if isinstance(product.get(k), str) and product[k].strip():
                return product[k].strip()
    offer_detail = d.get("offer_detail")
    if isinstance(offer_detail, dict):
        for k in ("title", "description", "desc"):
            if isinstance(offer_detail.get(k), str) and offer_detail[k].strip():
                return offer_detail[k].strip()
    for k in ("name", "title", "offer_description", "description"):
        if isinstance(d.get(k), str) and d[k].strip():
            return d[k].strip()
    return None


def _seller_name(d: dict) -> str | None:
    for container in ("seller", "store", "manager"):
        x = d.get(container)
        if isinstance(x, dict):
            for k in ("name", "desc", "company_name"):
                if isinstance(x.get(k), str) and x[k].strip():
                    return x[k].strip()
    return None


def offer_dict_to_observation(d: dict, url: str | None = None) -> LotObservation:
    if not looks_like_offer(d):
        raise ValueError("JSON no parece un objeto de oferta Superbid.")

    offer_detail = d.get("offer_detail") if isinstance(d.get("offer_detail"), dict) else {}
    auction = d.get("auction") if isinstance(d.get("auction"), dict) else {}
    address = auction.get("address") if isinstance(auction.get("address"), dict) else {}
    lot_id = str(d["id"])

    initial = _money_from(offer_detail.get("initial_bid_value"))
    winner = _money_from(d.get("winner_bid"))
    current = winner or _money_from(d.get("price")) or _money_from(offer_detail.get("current_max_bid")) or _money_from(offer_detail.get("current_min_bid"))
    outcome = _outcome(d)

    commission_percent = (
        _nested_number(d, "group_offer", "commission_percent")
        or _nested_number(d, "offer_detail", "commission_percent")
        or _nested_number(d, "auction", "commission_percent")
    )

    evidence = {
        "parser": "superbid_json_v2",
        "source_fields": sorted(k for k in (
            "price", "winner_bid", "offer_detail", "offer_status", "total_bids",
            "total_bidders", "end_date", "auction", "group_offer",
        ) if k in d),
        "auction_id": auction.get("id"),
        "auction_desc": auction.get("desc"),
        "currency_iso": auction.get("currency_iso"),
        "lot_number": d.get("lot_number"),
        "visits": d.get("visits"),
        "total_bidders": _num(d.get("total_bidders")),
        "commission_percent_public": commission_percent,
        "public_status": d.get("offer_status"),
    }

    # Never copy reserved_price/reserve values into evidence.
    return LotObservation(
        external_lot_id=lot_id,
        url=canonical_offer_url(d, url or f"https://www.superbid.com.co/oferta/{lot_id}", lot_id),
        title=_product_name(d),
        city=address.get("city") if isinstance(address.get("city"), str) else None,
        seller=_seller_name(d),
        initial_bid_cop=initial,
        displayed_price_cop=current,
        displayed_price_label="winner_bid" if winner is not None else "price/current_bid",
        bid_count=_num(d.get("total_bids")),
        status_text=str(d.get("offer_status") or d.get("status_id") or ""),
        outcome=outcome,
        closes_at_text=str(d.get("end_date")) if d.get("end_date") else None,
        observed_at=datetime.now(timezone.utc),
        evidence=evidence,
    )


def extract_offer_observations(payload: Any, source_url: str | None = None) -> list[LotObservation]:
    seen = set()
    out = []
    for d in _walk(payload):
        if not looks_like_offer(d):
            continue
        try:
            obs = offer_dict_to_observation(d, source_url)
        except Exception:
            continue
        if obs.external_lot_id in seen:
            continue
        seen.add(obs.external_lot_id)
        out.append(obs)
    return out
