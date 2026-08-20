from __future__ import annotations
import json
from pathlib import Path
from .fetchers import UA,validate_url
from .json_adapter import extract_offer_observations
from .storage import Store
from .attachments import extract_json_attachments,extract_html_attachments
from .bid_history import extract_bid_history
from .storage_extensions import save_attachments,save_bid_history
from .provenance import save_provenance

async def capture_public_json(url:str,seconds:int=12,dump_dir:str|None=None,db:str|None=None)->dict:
    validate_url(url)
    try:from playwright.async_api import async_playwright
    except ImportError as exc:raise RuntimeError('Instale: pip install -e ".[browser]" && playwright install chromium') from exc
    dumps=Path(dump_dir) if dump_dir else None
    if dumps:dumps.mkdir(parents=True,exist_ok=True)
    candidates=[];observations={};payload_attachments=[];payload_bids=[];html_attachments=[];errors=[]
    async with async_playwright() as p:
        browser=await p.chromium.launch(headless=True);context=await browser.new_context(user_agent=UA,locale="es-CO");page=await context.new_page()
        async def handle(resp):
            try:
                ct=(resp.headers.get("content-type") or "").lower();rt=resp.request.resource_type
                if "json" not in ct and rt not in {"xhr","fetch"}:return
                candidates.append({"url":resp.url,"status":resp.status,"resource_type":rt,"content_type":ct})
                try:payload=await resp.json()
                except Exception:return
                if dumps:(dumps/f"{len(candidates):04d}.json").write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding="utf-8")
                for obs in extract_offer_observations(payload,source_url=url):observations[obs.external_lot_id]=obs
                payload_attachments.extend(extract_json_attachments(payload));payload_bids.extend(extract_bid_history(payload))
            except Exception as exc:errors.append(str(exc))
        page.on("response",handle);await page.goto(url,wait_until="domcontentloaded",timeout=45000);await page.wait_for_timeout(seconds*1000)
        try:html_attachments=extract_html_attachments(url,await page.content())
        except Exception as exc:errors.append(f"html_attachments: {exc}")
        await browser.close()
    saved=attachments_saved=bids_saved=0
    if db:
        store=Store(db);store.init();lot_ids=[]
        for obs in observations.values():
            saved_lot_id=store.save(obs);lot_ids.append(saved_lot_id);fields={"title":obs.title is not None,"seller":obs.seller is not None,"initial_bid_cop":obs.initial_bid_cop is not None,"displayed_price_cop":obs.displayed_price_cop is not None,"bid_count":obs.bid_count is not None,"closes_at_text":obs.closes_at_text is not None,"outcome":obs.outcome.value!="UNKNOWN"};confidence=.98 if obs.outcome.value=="SOLD_CONFIRMED" else .90;save_provenance(store.conn,saved_lot_id,source_type="superbid_public_json",source_url=obs.url,fields=fields,confidence=confidence,note="Structured public response observed while rendering Superbid.");saved+=1
        if len(lot_ids)==1:
            merged={a["url"]:a for a in payload_attachments+html_attachments};attachments_saved=save_attachments(store.conn,lot_ids[0],list(merged.values()));bids_saved=save_bid_history(store.conn,lot_ids[0],payload_bids)
    return {"page_url":url,"candidate_responses":candidates,"lots_found":[o.model_dump(mode="json") for o in observations.values()],"saved":saved,"attachments_saved":attachments_saved,"bids_saved":bids_saved,"attachments_found":payload_attachments+html_attachments,"bid_history_found":payload_bids,"errors":errors}
