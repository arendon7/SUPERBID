from __future__ import annotations
import csv,io,os,sqlite3
from pathlib import Path as _Path
from fastapi import FastAPI,Query
from fastapi.requests import Request
from fastapi.responses import StreamingResponse,HTMLResponse,RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from .valuation import CostProfile
from .opportunity_service import analyze_lot
from .history import historical_rows,grouped_history,history_csv
from .settings import get_cost_profile,set_cost_profile
from .dashboard_service import active_opportunities
from .excel_export import export_operational_workbook
from .security import require_admin,dashboard_allowed
from .health import operational_health
from .discovery import add_discovery_source
from .operations import enqueue_lot
from .parsers import lot_id_from_url
from .supabase_sync import get_state
from .provenance import provenance_for_lot
DB_PATH=os.getenv("SUPERBID_DB","superbid.db")
app=FastAPI(title="SUPERBID Deal Intelligence API",version="0.10.0",description="API de lectura del histórico capturado por el collector.")
_BASE_DIR=_Path(__file__).resolve().parent;app.mount("/static",StaticFiles(directory=str(_BASE_DIR/"static")),name="static");templates=Jinja2Templates(directory=str(_BASE_DIR/"templates"))
def conn():
    c=sqlite3.connect(DB_PATH);c.row_factory=sqlite3.Row;return c
@app.get("/",include_in_schema=False)
def root():return RedirectResponse("/dashboard")
@app.get("/dashboard",response_class=HTMLResponse,include_in_schema=False)
def dashboard(request:Request):
    if not dashboard_allowed(request):return HTMLResponse("<h1>Acceso requerido</h1><p>Use ?token=... o X-Superbid-Token.</p>",status_code=401)
    return templates.TemplateResponse("dashboard.html",{"request":request})
@app.get("/health")
def health():return {"ok":True,"db":DB_PATH}
@app.get("/lots")
def lots(brand:str|None=None,model_year:int|None=None,outcome:str|None=None,limit:int=Query(100,ge=1,le=1000)):
    sql="SELECT l.id,l.external_lot_id,l.url,l.title,l.brand,l.model_year,l.city,l.seller,l.initial_bid_cop,l.first_seen_at,l.last_seen_at,o.outcome,o.closing_price_observed_cop,o.sale_price_confirmed_cop,o.confidence FROM lots l LEFT JOIN lot_outcomes o ON o.lot_id=l.id WHERE 1=1";args=[]
    if brand:sql+=" AND upper(l.brand)=upper(?)";args.append(brand)
    if model_year:sql+=" AND l.model_year=?";args.append(model_year)
    if outcome:sql+=" AND o.outcome=?";args.append(outcome)
    sql+=" ORDER BY l.last_seen_at DESC LIMIT ?";args.append(limit)
    with conn() as c:return [dict(r) for r in c.execute(sql,args).fetchall()]
@app.get("/lots/{external_lot_id}")
def lot_detail(external_lot_id:str):
    with conn() as c:
        lot=c.execute("SELECT * FROM lots WHERE external_lot_id=? ORDER BY id DESC LIMIT 1",(external_lot_id,)).fetchone()
        if not lot:return {"found":False}
        snaps=c.execute("SELECT observed_at,displayed_price_cop,displayed_price_label,bid_count,status_text,outcome,closes_at_text FROM lot_snapshots WHERE lot_id=? ORDER BY observed_at ASC",(lot["id"],)).fetchall();outcome=c.execute("SELECT * FROM lot_outcomes WHERE lot_id=?",(lot["id"],)).fetchone()
    return {"found":True,"lot":dict(lot),"outcome":dict(outcome) if outcome else None,"snapshots":[dict(r) for r in snaps]}
@app.get("/analytics/summary")
def summary():
    with conn() as c:
        base=c.execute("SELECT COUNT(*) lots,SUM(CASE WHEN o.outcome='SOLD_CONFIRMED' THEN 1 ELSE 0 END) sold_confirmed,SUM(CASE WHEN o.outcome='CONDITIONAL' THEN 1 ELSE 0 END) conditional,SUM(CASE WHEN o.outcome='ACTIVE' THEN 1 ELSE 0 END) active,AVG(CASE WHEN o.sale_price_confirmed_cop IS NOT NULL AND l.initial_bid_cop IS NOT NULL AND l.initial_bid_cop>0 THEN 1.0*o.sale_price_confirmed_cop/l.initial_bid_cop-1 END) avg_sale_vs_initial_pct FROM lots l LEFT JOIN lot_outcomes o ON o.lot_id=l.id").fetchone();brands=c.execute("SELECT l.brand,COUNT(*) lots,SUM(CASE WHEN o.outcome='SOLD_CONFIRMED' THEN 1 ELSE 0 END) sold FROM lots l LEFT JOIN lot_outcomes o ON o.lot_id=l.id WHERE l.brand IS NOT NULL GROUP BY l.brand ORDER BY lots DESC LIMIT 20").fetchall()
    r=dict(base);r["avg_sale_vs_initial_pct"]=(r["avg_sale_vs_initial_pct"]*100 if r.get("avg_sale_vs_initial_pct") is not None else None);r["brands"]=[dict(x) for x in brands];return r
@app.get("/export/lots.csv")
def export_csv():
    with conn() as c:rows=c.execute("SELECT l.external_lot_id,l.title,l.brand,l.model_year,l.city,l.seller,l.initial_bid_cop,o.outcome,o.closing_price_observed_cop,o.sale_price_confirmed_cop,o.confidence,l.url FROM lots l LEFT JOIN lot_outcomes o ON o.lot_id=l.id ORDER BY l.last_seen_at DESC").fetchall()
    buf=io.StringIO();w=csv.writer(buf);w.writerow(["external_lot_id","title","brand","model_year","city","seller","initial_bid_cop","outcome","closing_price_observed_cop","sale_price_confirmed_cop","confidence","url"])
    for r in rows:w.writerow(list(r))
    return StreamingResponse(io.BytesIO(buf.getvalue().encode("utf-8-sig")),media_type="text/csv",headers={"Content-Disposition":"attachment; filename=superbid_lots.csv"})
class CostProfileInput(BaseModel):
    buyer_commission_pct:float=0.0;vat_on_commission_pct:float=0.0;transfer_cop:int=0;taxes_soat_cop:int=0;transport_cop:int=0;repair_cop:int=0;detailing_cop:int=0;financing_cop:int=0;admin_fee_cop:int=0;contingency_cop:int=0;target_profit_pct_of_resale:float=.12;target_profit_floor_cop:int=3000000;quick_sale_discount_pct:float=.05;fasecolda_cap_pct:float=1.0
@app.post("/lots/{external_lot_id}/valuation")
def lot_valuation(external_lot_id:str,inp:CostProfileInput):
    with conn() as c:
        try:return analyze_lot(c,external_lot_id,CostProfile(**inp.model_dump()))
        except ValueError as exc:return {"found":False,"error":str(exc)}
@app.get("/active-auctions")
def active_auctions(limit:int=Query(200,ge=1,le=1000)):
    with conn() as c:
        rows=c.execute("SELECT l.id,l.external_lot_id,l.title,l.brand,l.model_year,l.city,l.seller,l.url,l.initial_bid_cop,s.displayed_price_cop AS current_bid_cop,s.bid_count,s.closes_at_text,s.status_text,s.observed_at,o.outcome FROM lots l JOIN lot_snapshots s ON s.id=(SELECT s2.id FROM lot_snapshots s2 WHERE s2.lot_id=l.id ORDER BY s2.observed_at DESC LIMIT 1) LEFT JOIN lot_outcomes o ON o.lot_id=l.id WHERE o.outcome IN ('ACTIVE','UNKNOWN') ORDER BY s.closes_at_text ASC,s.observed_at DESC LIMIT ?",(limit,)).fetchall();out=[]
        for r in rows:
            x=dict(r);atts=c.execute("SELECT name,url,kind FROM lot_attachments WHERE lot_id=? ORDER BY id",(r["id"],)).fetchall();per=[dict(a) for a in atts if a["kind"]=="PERITAJE"];x.update({"peritaje_available":bool(per),"peritajes":per,"annex_count":len(atts)});out.append(x)
    return out
@app.get("/lots/{external_lot_id}/attachments")
def lot_attachments(external_lot_id:str):
    with conn() as c:
        lot=c.execute("SELECT id FROM lots WHERE external_lot_id=? ORDER BY id DESC LIMIT 1",(external_lot_id,)).fetchone()
        if not lot:return {"found":False}
        rows=c.execute("SELECT name,url,kind,source,discovered_at FROM lot_attachments WHERE lot_id=? ORDER BY kind,id",(lot["id"],)).fetchall()
    return {"found":True,"attachments":[dict(r) for r in rows],"peritajes":[dict(r) for r in rows if r["kind"]=="PERITAJE"]}
@app.get("/lots/{external_lot_id}/bid-history")
def lot_bid_history(external_lot_id:str):
    with conn() as c:
        lot=c.execute("SELECT id FROM lots WHERE external_lot_id=? ORDER BY id DESC LIMIT 1",(external_lot_id,)).fetchone()
        if not lot:return {"found":False}
        rows=c.execute("SELECT sequence_no,amount_cop,bid_at_text,observed_at FROM lot_bid_history WHERE lot_id=? ORDER BY COALESCE(sequence_no,999999),observed_at",(lot["id"],)).fetchall()
    return {"found":True,"bids":[dict(r) for r in rows]}
@app.get("/history/vehicles")
def vehicle_history(brand:str|None=None,model_year:int|None=None,line:str|None=None,limit:int=Query(1000,ge=1,le=10000)):
    with conn() as c:return historical_rows(c,brand,model_year,line,limit)
@app.get("/history/summary")
def vehicle_history_summary(brand:str|None=None,model_year:int|None=None,line:str|None=None):
    with conn() as c:return grouped_history(c,brand,model_year,line)
@app.get("/export/history.csv")
def export_history_csv(brand:str|None=None,model_year:int|None=None,line:str|None=None):
    with conn() as c:data=history_csv(c,brand,model_year,line)
    return StreamingResponse(io.BytesIO(data),media_type="text/csv",headers={"Content-Disposition":"attachment; filename=superbid_vehicle_history.csv"})
@app.get("/opportunities")
def opportunities(limit:int=Query(500,ge=1,le=2000)):
    with conn() as c:return active_opportunities(c,get_cost_profile(c),limit)
@app.get("/settings/cost-profile")
def get_default_cost_profile():
    with conn() as c:return get_cost_profile(c).__dict__
@app.put("/settings/cost-profile")
def update_default_cost_profile(inp:CostProfileInput):
    p=CostProfile(**inp.model_dump())
    with conn() as c:set_cost_profile(c,p)
    return {"ok":True,"profile":p.__dict__}
@app.get("/export/operacion.xlsx")
def export_operation_xlsx():
    with conn() as c:data=export_operational_workbook(c)
    return StreamingResponse(io.BytesIO(data),media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",headers={"Content-Disposition":"attachment; filename=superbid_operacion.xlsx"})
@app.get("/operations/status")
def operations_status():
    with conn() as c:
        q=c.execute("SELECT SUM(CASE WHEN status='WATCH' THEN 1 ELSE 0 END) watching,SUM(CASE WHEN status='DONE' THEN 1 ELSE 0 END) done,SUM(CASE WHEN status='WATCH' AND next_run_at<=CURRENT_TIMESTAMP THEN 1 ELSE 0 END) due FROM collection_queue").fetchone();runs=[dict(r) for r in c.execute("SELECT * FROM collection_runs ORDER BY started_at DESC LIMIT 20").fetchall()];sources=[dict(r) for r in c.execute("SELECT * FROM discovery_sources ORDER BY id").fetchall()]
    return {"queue":dict(q) if q else {},"runs":runs,"sources":sources}
@app.get("/health/operational")
def health_operational():
    with conn() as c:return operational_health(c)
class DiscoverySourceInput(BaseModel):url:str
class EnqueueInput(BaseModel):url:str
@app.post("/admin/discovery-sources")
def admin_add_discovery_source(inp:DiscoverySourceInput,request:Request):
    require_admin(request);from .storage import Store;s=Store(DB_PATH);s.init();add_discovery_source(s,inp.url);return {"ok":True,"url":inp.url}
@app.post("/admin/enqueue")
def admin_enqueue(inp:EnqueueInput,request:Request):
    require_admin(request);lot_id=lot_id_from_url(inp.url)
    with conn() as c:enqueue_lot(c,lot_id,inp.url)
    return {"ok":True,"external_lot_id":lot_id}
@app.get("/sync/status")
def sync_status():
    with conn() as c:return {"configured":bool(os.getenv("SUPABASE_URL") and os.getenv("SUPABASE_SERVICE_ROLE_KEY")),"last_sync_at":get_state(c,"supabase_last_sync_at"),"last_counts":get_state(c,"supabase_last_sync_counts"),"last_error":get_state(c,"supabase_last_sync_error")}
@app.get("/lots/{external_lot_id}/provenance")
def lot_provenance_api(external_lot_id:str):
    with conn() as c:
        lot=c.execute("SELECT id FROM lots WHERE external_lot_id=? ORDER BY id DESC LIMIT 1",(external_lot_id,)).fetchone()
        return {"found":False} if not lot else {"found":True,"provenance":provenance_for_lot(c,int(lot["id"]))}
