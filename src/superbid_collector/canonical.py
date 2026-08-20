from __future__ import annotations

from urllib.parse import urljoin


def canonical_offer_url(d: dict, fallback: str, lot_id: str) -> str:
    for key in ("url","offer_url","detail_url","link","permalink"):
        v=d.get(key)
        if isinstance(v,str) and v.strip():
            v=v.strip()
            if v.startswith(("http://","https://")): return v
            if v.startswith("/"): return urljoin("https://www.superbid.com.co",v)
    slug=d.get("slug")
    if isinstance(slug,str) and slug.strip():
        return f"https://www.superbid.com.co/oferta/{slug.strip()}"
    return fallback
