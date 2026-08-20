from __future__ import annotations
import sqlite3,re
from dataclasses import asdict
from .market_storage import init_market_schema
from .valuation import CostProfile,estimate_market,calculate_opportunity

def _line_from_title(title:str|None,brand:str|None)->str|None:
    if not title:return None
    t=title.upper()
    if brand:t=t.replace(brand.upper()," ",1)
    t=re.split(r"\b(?:19|20)\d{2}\b",t)[0]; t=re.sub(r"\b(?:MOD|MODELO|CC|PLACA|UBIC)\b.*$","",t); t=re.sub(r"\s+"," ",t).strip(" ,-")
    return t or None

def fasecolda_candidates(conn:sqlite3.Connection,brand:str,model_year:int,line_hint:str|None,limit=20):
    init_market_schema(conn); sql="SELECT * FROM fasecolda_values WHERE upper(brand)=upper(?) AND model_year=?"; args=[brand,model_year]
    if line_hint:sql+=" AND upper(reference1) LIKE upper(?)"; args.append(f"%{line_hint.split()[0]}%")
    sql+=" ORDER BY value_cop ASC LIMIT ?"; args.append(limit)
    return [dict(r) for r in conn.execute(sql,args).fetchall()]

def analyze_lot(conn:sqlite3.Connection,external_lot_id:str,profile:CostProfile)->dict:
    init_market_schema(conn)
    lot=conn.execute("SELECT * FROM lots WHERE external_lot_id=? ORDER BY id DESC LIMIT 1",(external_lot_id,)).fetchone()
    if not lot:raise ValueError("Lote no encontrado.")
    snap=conn.execute("SELECT * FROM lot_snapshots WHERE lot_id=? ORDER BY observed_at DESC LIMIT 1",(lot["id"],)).fetchone()
    comps=conn.execute("SELECT asking_price_cop FROM market_comparables WHERE lot_id=? ORDER BY observed_at DESC",(lot["id"],)).fetchall(); prices=[int(x["asking_price_cop"]) for x in comps]
    fval=None; fcands=[]
    if lot["brand"] and lot["model_year"]:
        hint=lot["line"] or _line_from_title(lot["title"],lot["brand"]); fcands=fasecolda_candidates(conn,lot["brand"],lot["model_year"],hint)
        if len(fcands)==1:fval=int(fcands[0]["value_cop"])
    market=estimate_market(prices,fasecolda_cop=fval,quick_sale_discount_pct=profile.quick_sale_discount_pct,fasecolda_cap_pct=profile.fasecolda_cap_pct)
    current=snap["displayed_price_cop"] if snap else None; opp=calculate_opportunity(market,current,profile)
    return {"lot":dict(lot),"latest_snapshot":dict(snap) if snap else None,"market":asdict(market),"opportunity":asdict(opp),"cost_profile":asdict(profile),"fasecolda_candidates":fcands,"needs_fasecolda_version_selection":len(fcands)>1}
