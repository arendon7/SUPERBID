#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path

from superbid_collector.attachments import extract_html_attachments, extract_json_attachments
from superbid_collector.json_adapter import extract_offer_observations
from superbid_collector.probe_sanitize import endpoint_signature, safe_observation, safe_shape
from superbid_collector.fetchers import UA, validate_url


async def run(url: str, seconds: int, output: Path) -> int:
    validate_url(url)
    from playwright.async_api import async_playwright

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "target": endpoint_signature(url),
        "page": {},
        "responses": [],
        "observations": [],
        "attachments": [],
        "errors": [],
    }
    observations = {}
    attachments = {}

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
                entry = {
                    "endpoint": endpoint_signature(resp.url),
                    "status": resp.status,
                    "resource_type": rt,
                    "content_type": ct.split(";")[0],
                }
                try:
                    payload = await resp.json()
                except Exception:
                    payload = None
                if payload is not None:
                    entry["shape"] = safe_shape(payload)
                    for obs in extract_offer_observations(payload, source_url=url):
                        observations[obs.external_lot_id] = safe_observation(obs)
                    for att in extract_json_attachments(payload):
                        key = f'{att.get("kind")}:{att.get("name")}'
                        attachments[key] = {
                            "kind": att.get("kind"),
                            "name": att.get("name"),
                            "source": att.get("source"),
                            "endpoint": endpoint_signature(att.get("url") or ""),
                        }
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
            html = await page.content()
            for att in extract_html_attachments(url, html):
                key = f'{att.get("kind")}:{att.get("name")}'
                attachments[key] = {
                    "kind": att.get("kind"),
                    "name": att.get("name"),
                    "source": att.get("source"),
                    "endpoint": endpoint_signature(att.get("url") or ""),
                }
        except Exception as exc:
            report["errors"].append(f"page: {type(exc).__name__}: {exc}")
        finally:
            await browser.close()

    # Deduplicate endpoint signatures without keeping raw URLs.
    unique = {}
    for row in report["responses"]:
        key = json.dumps(row["endpoint"], sort_keys=True) + ":" + row["resource_type"]
        unique[key] = row
    report["responses"] = list(unique.values())
    report["observations"] = list(observations.values())
    report["attachments"] = list(attachments.values())
    report["summary"] = {
        "candidate_responses": len(report["responses"]),
        "lots_recognized": len(report["observations"]),
        "attachments_recognized": len(report["attachments"]),
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
