from __future__ import annotations
import sqlite3
from statistics import median
from .valuation import CostProfile
from .opportunity_service import analyze_lot

def _history_median(conn:sqlite3.Connection,brand:str|None,model_year:int|None,title:str|None):
    if not brand or not model_year:return None
    rows=conn.execute("SELECT COALESCE(o.sale_price_confirmed_cop,o.closing_price_observed_cop) AS v FROM lots l JOIN lot_outcomes o ON o.lot_id=l.id WHERE upper(l.brand)=upper(?) AND l.model_year=? AND COALESCE(o.sale_price_confirmed_cop,o.closing_price_observed_cop) IS NOT NULL",(brand,model_year)).fetchall()
    vals=[int(r["v"]) for r in rows if r["v"]]; return int(median(vals)) if vals else None

def active_opportunities(conn:sqlite3.Connection,profile:CostProfile,limit:int=500)->list[dict]:
    rows=conn.execute("""SELECT l.id,l.external_lot_id,l.title,l.brand,l.line,l.model_year,l.city,l.seller,l.url,l.initial_bid_cop,s.displayed_price_cop AS current_bid_cop,s.bid_count,s.closes_at_text,s.status_text,s.observed_at,o.outcome FROM lots l JOIN lot_snapshots s ON s.id=(SELECT s2.id FROM lot_snapshots s2 WHERE s2.lot_id=l.id ORDER BY s2.observed_at DESC LIMIT 1) LEFT JOIN lot_outcomes o ON o.lot_id=l.id WHERE COALESCE(o.outcome,'UNKNOWN') IN ('ACTIVE','UNKNOWN') ORDER BY s.observed_at DESC LIMIT ?""",(limit,)).fetchall()
    out=[]
    for r in rows:
        x=dict(r); atts=conn.execute("SELECT name,url,kind FROM lot_attachments WHERE lot_id=? ORDER BY id",(r["id"],)).fetchall(); peritajes=[dict(a) for a in atts if a["kind"]=="PERITAJE"]
        x.update({"historical_reference_cop":_history_median(conn,r["brand"],r["model_year"],r["title"]),"peritaje_available":bool(peritajes),"peritajes":peritajes,"annex_count":len(atts)})
        try:
            analysis=analyze_lot(conn,r["external_lot_id"],profile); opp=analysis["opportunity"]; market=analysis["market"]
            x.update({"market_reference_cop":market.get("conservative_resale_cop"),"market_confidence":market.get("confidence"),"max_bid_cop":opp.get("max_bid_cop"),"expected_profit_cop":opp.get("expected_profit_cop"),"expected_roi_pct":opp.get("expected_roi_pct"),"score":opp.get("score"),"decision":opp.get("decision"),"headroom_cop":opp.get("headroom_cop"),"needs_fasecolda_version_selection":analysis.get("needs_fasecolda_version_selection",False)})
        except Exception:
            x.update({"market_reference_cop":None,"market_confidence":0,"max_bid_cop":None,"expected_profit_cop":None,"expected_roi_pct":None,"score":0,"decision":"SIN_DATOS","headroom_cop":None,"needs_fasecolda_version_selection":False})
        out.append(x)
    rank={"COMPRAR":0,"VIGILAR":1,"RIESGO":2,"ANALIZAR":3,"SIN_DATOS":4,"NO_PUJAR":5}
    return sorted(out,key=lambda x:(rank.get(x.get("decision"),9),-(x.get("score") or 0),-(x.get("expected_roi_pct") or -999)))
