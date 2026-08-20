from __future__ import annotations
import asyncio,json,time
from pathlib import Path
import typer
from .collector import collect_one,read_urls
from .fetchers import probe_network
from .storage import Store
from .network_capture import capture_public_json
from .fasecolda import import_fasecolda_excel
from .mercadolibre import search_vehicle_comparables
from .market_storage import add_comparable
from .valuation import CostProfile
from .opportunity_service import analyze_lot
from .discovery import add_discovery_source
from .operations import enqueue_lot
app=typer.Typer(no_args_is_help=True,help="SUPERBID Deal Intelligence v0.10")
@app.command("init-db")
def init_db(db:str=typer.Option("superbid.db")):s=Store(db);s.init();typer.echo(f"Base inicializada: {db}")
@app.command("collect-url")
def collect_url(url:str,db:str=typer.Option("superbid.db"),browser:bool=typer.Option(False,"--browser")):
    lot_id,obs=collect_one(url,db,browser);typer.echo(json.dumps({"lot_db_id":lot_id,"external_lot_id":obs.external_lot_id,"title":obs.title,"brand":obs.brand,"model_year":obs.model_year,"initial_bid_cop":obs.initial_bid_cop,"displayed_price_cop":obs.displayed_price_cop,"outcome":obs.outcome.value},ensure_ascii=False,indent=2))
@app.command("watch")
def watch(urls_file:str,db:str=typer.Option("superbid.db"),interval:int=typer.Option(1800,min=60),browser:bool=typer.Option(False,"--browser"),once:bool=typer.Option(False,"--once")):
    urls=read_urls(urls_file)
    if not urls:raise typer.BadParameter("No hay URLs.")
    while True:
        for url in urls:
            try:_,obs=collect_one(url,db,browser);typer.echo(f"{obs.observed_at.isoformat()} {obs.external_lot_id} {obs.outcome.value} {obs.displayed_price_cop}")
            except Exception as exc:typer.echo(f"ERROR {url}: {exc}",err=True)
            time.sleep(1.5)
        if once:return
        time.sleep(interval)
@app.command("probe-network")
def probe_network_cmd(url:str,seconds:int=typer.Option(12,min=3,max=60)):
    rows=asyncio.run(probe_network(url,seconds))
    for row in rows:typer.echo(f'{row["status"]} {row["resource_type"]:<6} {row["content_type"][:40]:<40} {row["url"]}')
    typer.echo(f"\nTotal candidatos JSON/XHR: {len(rows)}")
@app.command("capture-json")
def capture_json_cmd(url:str,db:str=typer.Option("superbid.db"),seconds:int=typer.Option(12,min=3,max=60),dump_dir:str|None=None):
    r=asyncio.run(capture_public_json(url,seconds=seconds,dump_dir=dump_dir,db=db));typer.echo(json.dumps({"page_url":r["page_url"],"candidate_response_count":len(r["candidate_responses"]),"lots_found":len(r["lots_found"]),"saved":r["saved"],"attachments_saved":r.get("attachments_saved",0),"bids_saved":r.get("bids_saved",0),"peritajes_found":[a for a in r.get("attachments_found",[]) if a.get("kind")=="PERITAJE"],"errors":r["errors"][:5],"lot_ids":[x["external_lot_id"] for x in r["lots_found"]]},ensure_ascii=False,indent=2))
@app.command("import-fasecolda")
def import_fasecolda_cmd(excel:str,db:str=typer.Option("superbid.db")):
    s=Store(db);s.init();typer.echo(json.dumps(import_fasecolda_excel(s.conn,excel),ensure_ascii=False,indent=2))
@app.command("meli-comparables")
def meli_comparables_cmd(external_lot_id:str,query:str,db:str=typer.Option("superbid.db"),limit:int=typer.Option(30,min=1,max=50)):
    s=Store(db);s.init();row=s.conn.execute("SELECT id FROM lots WHERE external_lot_id=? ORDER BY id DESC LIMIT 1",(external_lot_id,)).fetchone()
    if not row:raise typer.BadParameter("Lote no encontrado en la base.")
    comps=search_vehicle_comparables(query,limit=limit)
    for c in comps:add_comparable(s.conn,lot_id=int(row["id"]),source=c["source"],external_id=c["external_id"],asking_price_cop=c["asking_price_cop"],url=c["url"],brand=c["brand"],line=c["line"],model_year=c["model_year"],mileage_km=c["mileage_km"],city=c["city"],seller_type=c["seller_type"],raw_json=c["raw_json"])
    typer.echo(json.dumps({"comparables_added":len(comps)},indent=2))
@app.command("analyze")
def analyze_cmd(external_lot_id:str,db:str=typer.Option("superbid.db"),commission_pct:float=0.0,commission_vat_pct:float=0.0,repair:int=0,transport:int=0,transfer:int=0,admin:int=0,contingency:int=0,target_profit_pct:float=.12):
    s=Store(db);s.init();p=CostProfile(buyer_commission_pct=commission_pct,vat_on_commission_pct=commission_vat_pct,repair_cop=repair,transport_cop=transport,transfer_cop=transfer,admin_fee_cop=admin,contingency_cop=contingency,target_profit_pct_of_resale=target_profit_pct)
    try:r=analyze_lot(s.conn,external_lot_id,p)
    except ValueError as exc:raise typer.BadParameter(str(exc))
    typer.echo(json.dumps(r,ensure_ascii=False,indent=2,default=str))
@app.command("add-discovery-source")
def add_discovery_source_cmd(url:str,db:str=typer.Option("superbid.db")):
    s=Store(db);s.init();add_discovery_source(s,url);typer.echo(f"Fuente registrada: {url}")
@app.command("enqueue-url")
def enqueue_url_cmd(url:str,db:str=typer.Option("superbid.db")):
    from .parsers import lot_id_from_url
    s=Store(db);s.init();lot_id=lot_id_from_url(url);enqueue_lot(s.conn,lot_id,url);typer.echo(f"Lote en cola: {lot_id}")
@app.command("enqueue-file")
def enqueue_file_cmd(path:str,db:str=typer.Option("superbid.db")):
    from .parsers import lot_id_from_url
    s=Store(db);s.init();count=0
    for raw in Path(path).read_text(encoding="utf-8").splitlines():
        url=raw.strip()
        if not url or url.startswith("#"):continue
        try:enqueue_lot(s.conn,lot_id_from_url(url),url);count+=1
        except Exception:continue
    typer.echo(json.dumps({"queued":count},indent=2))
