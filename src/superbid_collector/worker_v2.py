from __future__ import annotations
import asyncio,json,os,time
from .storage import Store
from .discovery import discover_from_source,sources
from .network_capture import capture_public_json
from .operations import due_lots,mark_queue_result,start_run,finish_run
DB=os.getenv("SUPERBID_DB","superbid.db");DISCOVERY_INTERVAL=int(os.getenv("SUPERBID_DISCOVERY_INTERVAL","3600"));IDLE_SECONDS=int(os.getenv("SUPERBID_IDLE_SECONDS","30"));CAPTURE_SECONDS=int(os.getenv("SUPERBID_CAPTURE_SECONDS","12"));QUEUE_BATCH=int(os.getenv("SUPERBID_QUEUE_BATCH","20"))
async def capture_due(store:Store):
    rows=due_lots(store.conn,QUEUE_BATCH);results=[]
    for q in rows:
        rid=start_run(store.conn,"LOT",q["url"])
        try:
            r=await capture_public_json(q["url"],seconds=CAPTURE_SECONDS,db=store.path);matched=next((lot for lot in r.get("lots_found") or [] if str(lot.get("external_lot_id"))==str(q["external_lot_id"])),None);mark_queue_result(store.conn,q["external_lot_id"],ok=True,closes_at_text=(matched or {}).get("closes_at_text"),outcome=(matched or {}).get("outcome"));finish_run(store.conn,rid,ok=True,lots_found=len(r.get("lots_found") or []),lots_saved=r.get("saved",0),attachments_saved=r.get("attachments_saved",0),bids_saved=r.get("bids_saved",0));results.append({"id":q["external_lot_id"],"ok":True})
        except Exception as exc:
            mark_queue_result(store.conn,q["external_lot_id"],ok=False,error=str(exc));finish_run(store.conn,rid,ok=False,error=str(exc));results.append({"id":q["external_lot_id"],"ok":False,"error":str(exc)})
        await asyncio.sleep(2)
    return results
async def discovery_cycle(store:Store):
    out=[]
    for src in sources(store):
        try:r=await discover_from_source(store,src["url"],CAPTURE_SECONDS);out.append({"url":src["url"],"lots":len(r.get("lots_found") or [])})
        except Exception as exc:out.append({"url":src["url"],"error":str(exc)})
        await asyncio.sleep(3)
    return out
def main():
    store=Store(DB);store.init();last_discovery=0.0;print(json.dumps({"worker":"v2_started","db":DB},ensure_ascii=False))
    while True:
        now=time.time()
        if now-last_discovery>=DISCOVERY_INTERVAL:
            try:print(json.dumps({"discovery":asyncio.run(discovery_cycle(store))},ensure_ascii=False))
            except Exception as exc:print(json.dumps({"discovery_error":str(exc)},ensure_ascii=False))
            last_discovery=now
        try:
            q=asyncio.run(capture_due(store))
            if q:print(json.dumps({"captures":q},ensure_ascii=False))
        except Exception as exc:print(json.dumps({"queue_error":str(exc)},ensure_ascii=False))
        time.sleep(IDLE_SECONDS)
if __name__=="__main__":main()
