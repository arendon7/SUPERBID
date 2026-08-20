from __future__ import annotations

import json
from typing import Any
from urllib.parse import parse_qsl, urlsplit

SENSITIVE_FRAGMENTS = (
    "token", "auth", "authorization", "signature", "secret", "apikey", "api_key",
    "reserved", "reserve", "bidder", "buyer", "username", "user_id", "email",
    "phone", "document", "identification", "password", "cookie", "session",
)
EMBEDDED_JSON_KEYS = {"productcustomjson", "customjson", "custom_json", "metadatajson", "metadata_json"}

# Public routing/query values that are safe and useful for reproducing read-only
# Superbid requests. Opaque filters are deliberately excluded.
PUBLIC_RECIPE_KEYS = {
    "portalId", "locale", "requestOrigin", "timeZoneId", "urlSeo",
    "pageNumber", "pageSize", "searchType", "preOrderBy",
}


def sensitive_key(key: str) -> bool:
    k = str(key).strip().lower()
    return any(fragment in k for fragment in SENSITIVE_FRAGMENTS)


def endpoint_signature(url: str) -> dict:
    """Describe an endpoint without exposing query values or URL credentials."""
    p = urlsplit(url)
    query_keys = sorted({k for k, _ in parse_qsl(p.query, keep_blank_values=True) if not sensitive_key(k)})
    return {"scheme": p.scheme, "host": p.hostname, "path": p.path, "query_keys": query_keys}


def public_query_values(url: str) -> dict[str, str]:
    """Return a strict allow-list of non-sensitive public routing parameters.

    Values are bounded to avoid accidentally persisting opaque blobs. In particular,
    `filter`, `fieldList` and all authentication/session-like values are excluded.
    """
    p = urlsplit(url)
    out: dict[str, str] = {}
    for key, value in parse_qsl(p.query, keep_blank_values=True):
        if key not in PUBLIC_RECIPE_KEYS or sensitive_key(key):
            continue
        if len(value) > 300:
            continue
        out[key] = value
    return out


def public_endpoint_recipe(url: str) -> dict:
    p = urlsplit(url)
    return {
        "scheme": p.scheme,
        "host": p.hostname,
        "path": p.path,
        "params": public_query_values(url),
    }


def safe_shape(value: Any, depth: int = 0, max_depth: int = 6) -> Any:
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
        return [safe_shape(value[0], depth + 1, max_depth)]
    if value is None: return "null"
    if isinstance(value, bool): return "bool"
    if isinstance(value, (int, float)): return "number"
    if isinstance(value, str): return "string"
    return type(value).__name__


def embedded_json_shapes(value: Any) -> list[dict]:
    """Parse known embedded JSON strings and return sanitized shapes only."""
    out = []
    def walk(obj):
        if isinstance(obj, dict):
            for k, v in obj.items():
                lk = str(k).lower()
                if lk in EMBEDDED_JSON_KEYS and isinstance(v, str) and v.lstrip().startswith(("{", "[")):
                    try:
                        out.append({"field": str(k), "shape": safe_shape(json.loads(v))})
                    except Exception:
                        out.append({"field": str(k), "shape": "invalid_json"})
                else:
                    walk(v)
        elif isinstance(obj, list):
            for v in obj: walk(v)
    walk(value)
    return out


def safe_observation(obs) -> dict:
    return {
        "external_lot_id": obs.external_lot_id,
        "title": obs.title,
        "brand": obs.brand,
        "line": obs.line,
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
