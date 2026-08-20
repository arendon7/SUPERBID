#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

import httpx

from superbid_collector.attachments import extract_html_attachments, extract_json_attachments
from superbid_collector.json_adapter import extract_offer_observations, looks_like_offer
from superbid_collector.probe_sanitize import (
    endpoint_signature,
    safe_observation,
    safe_shape,
    embedded_json_shapes,
    public_endpoint_recipe,
    safe_public_taxonomy,
)
from superbid_collector.fetchers import UA, validate_url
from superbid_collector.parsers import lot_id_from_url


def _expected(url: str) -> str | None:
    try:
        return lot_id_from_url(url)
    except Exception:
        return None


def _iter_dicts(obj):
    if isinstance(obj, dict):
        yield obj
        for v in obj.values():
            yield from _iter_dicts(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from _iter_dicts(v)


def _base_url(recipe: dict) -> str:
    return urlunsplit((recipe.get("scheme") or "https", recipe.get("host") or "", recipe.get("path") or "", "", ""))


def _headers(referer: str) -> dict[str, str]:
    return {
        "User-Agent": UA,
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "es-CO,es;q=0.9,en;q=0.7",
        "Origin": "https://www.superbid.com.co",
        "Referer": referer,
    }


async def _direct_get(recipe: dict, referer: str) -> tuple[httpx.Response, object | None]:
    async with httpx.AsyncClient(timeout=30, headers=_headers(referer), follow_redirects=True) as client:
        response = await client.get(_base_url(recipe), params=recipe.get("params") or {})
    try:
        payload = response.json()
    except Exception:
        payload = None
    return response, payload


async def _probe_direct_seo(recipe: dict, expected: str | None, referer: str) -> dict:
    result = {
        "attempted": True,
        "endpoint": {k: recipe.get(k) for k in ("scheme", "host", "path")},
        "params": recipe.get("params") or {},
        "opaque_filter_used": False,
        "browser_cookies_used": False,
    }
    try:
        response, payload = await _direct_get(recipe, referer)
        result["status"] = response.status_code
        result["content_type"] = (response.headers.get("content-type") or "").split(";")[0]
        if payload is not None:
            result["shape"] = safe_shape(payload)
            found = extract_offer_observations(payload, source_url=referer)
            if expected:
                found = [o for o in found if o.external_lot_id == expected]
            result["lots_recognized"] = len(found)
            result["observations"] = [safe_observation(o) for o in found]
        else:
            result["lots_recognized"] = 0
            result["observations"] = []
    except Exception as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"
        result["lots_recognized"] = 0
        result["observations"] = []
    return result


async def _probe_direct_offers(recipe: dict, referer: str) -> dict:
    result = {
        "attempted": True,
        "endpoint": {k: recipe.get(k) for k in ("scheme", "host", "path")},
        "params": recipe.get("params") or {},
        "opaque_filter_used": False,
        "field_list_used": False,
        "browser_cookies_used": False,
    }
    try:
        response, payload = await _direct_get(recipe, referer)
        result["status"] = response.status_code
        result["content_type"] = (response.headers.get("content-type") or "").split(";")[0]
        if payload is not None:
            result["shape"] = safe_shape(payload)
            found = extract_offer_observations(payload, source_url=referer)
            result["total"] = payload.get("total") if isinstance(payload, dict) else None
            result["lots_recognized"] = len(found)
            result["sample"] = [safe_observation(o) for o in found[:10]]
        else:
            result["lots_recognized"] = 0
            result["sample"] = []
    except Exception as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"
        result["lots_recognized"] = 0
        result["sample"] = []
    return result


async def _probe_direct_categories(recipe: dict, referer: str) -> dict:
    result = {
        "attempted": True,
        "endpoint": {k: recipe.get(k) for k in ("scheme", "host", "path")},
        "params": recipe.get("params") or {},
        "opaque_filter_used": False,
        "browser_cookies_used": False,
    }
    try:
        response, payload = await _direct_get(recipe, referer)
        result["status"] = response.status_code
        result["content_type"] = (response.headers.get("content-type") or "").split(";")[0]
        if payload is not None:
            result["shape"] = safe_shape(payload)
            result["taxonomy"] = safe_public_taxonomy(payload)
        else:
            result["taxonomy"] = None
    except Exception as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"
        result["taxonomy"] = None
    return result


async def run(url: str, seconds: int, output: Path) -> int:
    validate_url(url)
    from playwright.async_api import async_playwright

    expected = _expected(url)
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "target": endpoint_signature(url),
        "expected_lot_id": expected,
        "page": {}, "responses": [], "observations": [], "attachments": [],
        "embedded_json_shapes": [],
        "direct_http": {"attempted": False},
        "direct_offers": {"attempted": False},
        "direct_categories": {"attempted": False},
        "errors": [],
    }
    observations = {}
    attachments = {}
    embedded = []
    seo_recipe = None
    offers_recipe = None
    categories_recipe = None

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(user_agent=UA, locale="es-CO")
        page = await context.new_page()

        async def handle(resp):
            nonlocal seo_recipe, offers_recipe, categories_recipe
            try:
                ct = (resp.headers.get("content-type") or "").lower()
                rt = resp.request.resource_type
                if "json" not in ct and rt not in {"xhr", "fetch"}:
                    return
                entry = {
                    "endpoint": endpoint_signature(resp.url),
                    "status": resp.status,
                    "resource_type": rt,
                    "content_type": ct.split(";")[0],
                }
                parsed = urlsplit(resp.url)
                if parsed.hostname == "offer-query.superbid.net":
                    if parsed.path == "/seo/offers/":
                        seo_recipe = public_endpoint_recipe(resp.url)
                        entry["public_recipe"] = seo_recipe
                    elif parsed.path == "/offers/":
                        offers_recipe = public_endpoint_recipe(resp.url)
                        entry["public_recipe"] = offers_recipe
                    elif parsed.path == "/categories/":
                        categories_recipe = public_endpoint_recipe(resp.url)
                        entry["public_recipe"] = categories_recipe
                try:
                    payload = await resp.json()
                except Exception:
                    payload = None
                if payload is not None:
                    entry["shape"] = safe_shape(payload)
                    found = extract_offer_observations(payload, source_url=url)
                    if expected:
                        found = [o for o in found if o.external_lot_id == expected]
                    for obs in found:
                        observations[obs.external_lot_id] = safe_observation(obs)

                    if expected:
                        for obj in _iter_dicts(payload):
                            raw_id = obj.get("id") if isinstance(obj, dict) else None
                            if looks_like_offer(obj) and str(raw_id) == expected:
                                for att in extract_json_attachments(obj):
                                    key = f'{att.get("kind")}:{att.get("name")}:{endpoint_signature(att.get("url") or "").get("path")}'
                                    attachments[key] = {
                                        "kind": att.get("kind"), "name": att.get("name"), "source": att.get("source"),
                                        "endpoint": endpoint_signature(att.get("url") or ""),
                                    }
                                embedded.extend(embedded_json_shapes(obj))
                report["responses"].append(entry)
            except Exception as exc:
                report["errors"].append(f"response: {type(exc).__name__}: {exc}")

        page.on("response", handle)
        try:
            response = await page.goto(url, wait_until="domcontentloaded", timeout=60000)
            await page.wait_for_timeout(max(3, min(seconds, 45)) * 1000)
            report["page"] = {
                "status": response.status if response else None,
                "title": await page.title(),
                "final_url": endpoint_signature(page.url),
            }
            for att in extract_html_attachments(url, await page.content()):
                if att.get("kind") not in {"PERITAJE", "CONDICIONES", "CONTRATO"}:
                    continue
                key = f'{att.get("kind")}:{att.get("name")}:{endpoint_signature(att.get("url") or "").get("path")}'
                attachments[key] = {
                    "kind": att.get("kind"), "name": att.get("name"), "source": att.get("source"),
                    "endpoint": endpoint_signature(att.get("url") or ""),
                }
        except Exception as exc:
            report["errors"].append(f"page: {type(exc).__name__}: {exc}")
        finally:
            await browser.close()

    if seo_recipe:
        report["direct_http"] = await _probe_direct_seo(seo_recipe, expected, url)
    if offers_recipe:
        report["direct_offers"] = await _probe_direct_offers(offers_recipe, url)
    if categories_recipe:
        report["direct_categories"] = await _probe_direct_categories(categories_recipe, url)

    unique = {}
    for row in report["responses"]:
        key = json.dumps(row["endpoint"], sort_keys=True) + ":" + row["resource_type"]
        unique[key] = row
    report["responses"] = list(unique.values())
    report["observations"] = list(observations.values())
    report["attachments"] = list(attachments.values())
    shapes = {json.dumps(x, sort_keys=True): x for x in embedded}
    report["embedded_json_shapes"] = list(shapes.values())
    report["summary"] = {
        "candidate_responses": len(report["responses"]),
        "lots_recognized": len(report["observations"]),
        "attachments_recognized": len(report["attachments"]),
        "direct_http_status": report["direct_http"].get("status"),
        "direct_http_lots_recognized": report["direct_http"].get("lots_recognized", 0),
        "direct_offers_status": report["direct_offers"].get("status"),
        "direct_offers_lots_recognized": report["direct_offers"].get("lots_recognized", 0),
        "direct_offers_total": report["direct_offers"].get("total"),
        "direct_categories_status": report["direct_categories"].get("status"),
        "errors": len(report["errors"]),
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report["summary"], ensure_ascii=False))
    return 0 if report["page"].get("status") else 2


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("url")
    ap.add_argument("--seconds", type=int, default=15)
    ap.add_argument("--output", default="probe-output/report.json")
    args = ap.parse_args()
    raise SystemExit(asyncio.run(run(args.url, args.seconds, Path(args.output))))


if __name__ == "__main__":
    main()
