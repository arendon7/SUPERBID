from __future__ import annotations

from typing import Any
from urllib.parse import parse_qsl, urlsplit, urlunsplit

SENSITIVE_FRAGMENTS = (
    "token", "auth", "authorization", "signature", "secret", "apikey", "api_key",
    "reserved", "reserve", "bidder", "buyer", "username", "user_id", "email",
    "phone", "document", "identification", "password", "cookie", "session",
)


def sensitive_key(key: str) -> bool:
    k = str(key).strip().lower()
    return any(fragment in k for fragment in SENSITIVE_FRAGMENTS)


def endpoint_signature(url: str) -> dict:
    """Describe an endpoint without exposing query values or URL credentials."""
    p = urlsplit(url)
    query_keys = sorted({k for k, _ in parse_qsl(p.query, keep_blank_values=True) if not sensitive_key(k)})
    return {
        "scheme": p.scheme,
        "host": p.hostname,
        "path": p.path,
        "query_keys": query_keys,
    }


def safe_shape(value: Any, depth: int = 0, max_depth: int = 4) -> Any:
    """Return JSON structure/key names only; never return scalar source values."""
    if depth >= max_depth:
        return type(value).__name__
    if isinstance(value, dict):
        return {
            str(k): safe_shape(v, depth + 1, max_depth)
            for k, v in sorted(value.items(), key=lambda x: str(x[0]))
            if not sensitive_key(str(k))
        }
    if isinstance(value, list):
        if not value:
            return []
        # One representative item is sufficient for contract discovery.
        return [safe_shape(value[0], depth + 1, max_depth)]
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, (int, float)):
        return "number"
    if isinstance(value, str):
        return "string"
    return type(value).__name__


def safe_observation(obs) -> dict:
    """Whitelisted normalized fields useful for validating the Superbid contract."""
    return {
        "external_lot_id": obs.external_lot_id,
        "title": obs.title,
        "brand": obs.brand,
        "model_year": obs.model_year,
        "city": obs.city,
        "seller": obs.seller,
        "initial_bid_cop": obs.initial_bid_cop,
        "displayed_price_cop": obs.displayed_price_cop,
        "displayed_price_label": obs.displayed_price_label,
        "bid_count": obs.bid_count,
        "outcome": obs.outcome.value,
        "closes_at_text": obs.closes_at_text,
        "evidence": {
            k: v for k, v in (obs.evidence or {}).items()
            if k in {
                "parser", "source_fields", "auction_id", "auction_desc", "currency_iso",
                "lot_number", "visits", "total_bidders", "commission_percent_public",
            }
        },
    }
