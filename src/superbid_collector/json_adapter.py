from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Iterable
import re

from .models import LotObservation, Outcome
from .canonical import canonical_offer_url

MONEY_KEYS = (
    "amount", "value", "price", "bid_value", "bidAmount", "bid_amount",
    "winnerBidValue", "winner_bid_value", "currentBid", "current_bid",
    "currentMaxBid", "current_max_bid", "currentMinBid", "current_min_bid",
    "maxBid", "max_bid", "minBid", "min_bid",
)


def _first(d: dict, *keys: str, default=None):
    for key in keys:
        if key in d:
            return d[key]
    return default


def _dict(d: dict, *keys: str) -> dict:
    value = _first(d, *keys, default={})
    return value if isinstance(value, dict) else {}


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


def _nested_number(d: dict, paths: tuple[tuple[str, ...], ...]) -> float | None:
    for path in paths:
        cur: Any = d
        ok = True
        for key in path:
            if not isinstance(cur, dict) or key not in cur:
                ok = False
                break
            cur = cur[key]
        if not ok or cur is None or isinstance(cur, bool):
            continue
        if isinstance(cur, (int, float)):
            return float(cur)
        if isinstance(cur, str):
            try:
                return float(cur.replace("%", "").replace(",", ".").strip())
            except ValueError:
                pass
    return None


def _outcome(d: dict) -> Outcome:
    status = _dict(d, "offer_status", "offerStatus")
    if _first(status, "sold") is True:
        return Outcome.SOLD_CONFIRMED
    if _first(status, "closed") is True or _first(status, "closed_to_bids", "closedToBids") is True:
        return Outcome.CLOSED_OBSERVED
    if _first(status, "removed") is True:
        return Outcome.WITHDRAWN
    if _first(status, "available") is True or _first(status, "give_your_bid", "giveYourBid") is True:
        return Outcome.ACTIVE

    txt = " ".join(
        str(_first(d, k, default=""))
        for k in ("status", "status_desc", "statusDesc", "offer_status_desc", "offerStatusDesc")
    ).lower()
    if "condicion" in txt or "conditional" in txt:
        return Outcome.CONDITIONAL
    if "after market" in txt or "post-subasta" in txt or "pós-leilão" in txt:
        return Outcome.AFTER_MARKET
    if "retir" in txt:
        return Outcome.WITHDRAWN
    return Outcome.UNKNOWN


def looks_like_offer(d: dict) -> bool:
    has_id = isinstance(d.get("id"), (int, str))
    signals = (
        "offer_detail", "offerDetail", "offer_status", "offerStatus", "total_bids",
        "totalBids", "total_bidders", "totalBidders", "lot_number", "lotNumber",
        "end_date", "endDate", "winner_bid", "winnerBid",
    )
    return has_id and any(k in d for k in signals)


def _named(value: Any) -> str | None:
    if isinstance(value, str) and value.strip():
        return value.strip()
    if isinstance(value, dict):
        for key in ("name", "desc", "description", "shortDesc", "title"):
            v = value.get(key)
            if isinstance(v, str) and v.strip():
                return v.strip()
    return None


def _product_name(d: dict) -> str | None:
    product = _dict(d, "product")
    for key in ("name", "title", "shortDesc", "description", "desc", "detailedDescription"):
        v = product.get(key)
        if isinstance(v, str) and v.strip():
            return v.strip()
    offer_description = _first(d, "offer_description", "offerDescription")
    if isinstance(offer_description, dict):
        v = _first(offer_description, "offer_description", "offerDescription", "description", "desc")
        if isinstance(v, str) and v.strip():
            return v.strip()
    elif isinstance(offer_description, str) and offer_description.strip():
        return offer_description.strip()
    offer_detail = _dict(d, "offer_detail", "offerDetail")
    for key in ("title", "description", "desc"):
        v = offer_detail.get(key)
        if isinstance(v, str) and v.strip():
            return v.strip()
    return None


def _seller_name(d: dict) -> str | None:
    for container in ("seller", "store", "manager"):
        x = d.get(container)
        if isinstance(x, dict):
            for key in ("name", "desc", "company_name", "companyName"):
                v = x.get(key)
                if isinstance(v, str) and v.strip():
                    return v.strip()
    return None


def _city(d: dict) -> str | None:
    auction = _dict(d, "auction")
    address = _dict(auction, "address")
    city = _named(_first(address, "city"))
    if city:
        return city
    product = _dict(d, "product")
    location = _dict(product, "location")
    return _named(_first(location, "city")) or _named(location)


def offer_dict_to_observation(d: dict, url: str | None = None) -> LotObservation:
    if not looks_like_offer(d):
        raise ValueError("JSON no parece un objeto de oferta Superbid.")

    offer_detail = _dict(d, "offer_detail", "offerDetail")
    auction = _dict(d, "auction")
    product = _dict(d, "product")
    lot_id = str(d["id"])

    initial = _money_from(_first(offer_detail, "initial_bid_value", "initialBidValue"))
    winner_raw = _first(d, "winner_bid", "winnerBid")
    winner = _money_from(winner_raw)
    current = (
        winner
        or _money_from(_first(d, "price"))
        or _money_from(_first(offer_detail, "current_max_bid", "currentMaxBid"))
        or _money_from(_first(offer_detail, "current_min_bid", "currentMinBid"))
    )
    outcome = _outcome(d)

    commission_percent = _nested_number(
        d,
        (
            ("group_offer", "commission_percent"),
            ("groupOffer", "commissionPercent"),
            ("offer_detail", "commission_percent"),
            ("offerDetail", "commissionPercent"),
            ("auction", "commission_percent"),
            ("auction", "commissionPercent"),
            ("commercialCondition", "auctioneerCommissionPercent"),
        ),
    )

    evidence = {
        "parser": "superbid_json_v3_camelcase",
        "source_fields": sorted(k for k in (
            "price", "winner_bid", "winnerBid", "offer_detail", "offerDetail",
            "offer_status", "offerStatus", "total_bids", "totalBids", "total_bidders",
            "totalBidders", "end_date", "endDate", "auction", "group_offer", "groupOffer",
            "commercialCondition",
        ) if k in d),
        "auction_id": auction.get("id"),
        "auction_desc": _first(auction, "desc", "description"),
        "currency_iso": _first(auction, "currency_iso", "currencyIso"),
        "lot_number": _first(d, "lot_number", "lotNumber"),
        "visits": d.get("visits"),
        "total_bidders": _num(_first(d, "total_bidders", "totalBidders")),
        "commission_percent_public": commission_percent,
    }

    brand = _named(product.get("brand"))
    line = _named(product.get("model"))
    closes = _first(d, "end_date", "endDate") or _first(auction, "end_date", "endDate")
    status = _first(d, "offer_status", "offerStatus", "status_id", "statusId", default="")

    return LotObservation(
        external_lot_id=lot_id,
        url=canonical_offer_url(d, url or f"https://www.superbid.com.co/oferta/{lot_id}", lot_id),
        title=_product_name(d),
        brand=brand,
        line=line,
        city=_city(d),
        seller=_seller_name(d),
        initial_bid_cop=initial,
        displayed_price_cop=current,
        displayed_price_label="winner_bid" if winner is not None else "price/current_bid",
        bid_count=_num(_first(d, "total_bids", "totalBids")),
        status_text=str(status),
        outcome=outcome,
        closes_at_text=str(closes) if closes else None,
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
