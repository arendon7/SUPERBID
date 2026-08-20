from __future__ import annotations
import csv,io,re,sqlite3
from statistics import median
from .provenance import provenance_for_lot,quality_label

def normalize_vehicle_key(title:str|None,brand:str|None,model_year:int|None)->str:
    if not title:return f"{(brand or 'UNKNOWN').upper()}|UNKNOWN|{model_year or 0}"
    t=title.upper()
    if brand:t=re.sub(rf"\b{re.escape(brand.upper())}\b"," ",t,count=1)
    t=re.sub(r"\b(?:19|20)\d{2}\b.*$","",t); t=re.sub(r"\b(?:MOD\.?|MODELO|PLACA|UBIC\.?|CC)\b.*$","",t); t=re.sub(r"[^A-Z0-9ÁÉÍÓÚÑ ]+"," ",t); t=re.sub(r"\s+"," ",t).strip()
    return f"{(brand or 'UNKNOWN').upper()}|{t or 'UNKNOWN'}|{model_year or 0}"

def historical_rows(conn:sqlite3.Connection,brand=None,model_year=None,line_query=None,limit=1000):
    sql="""SELECT l.id,l.external_lot_id,l.title,l.brand,l.line,l.model_year,l.city,l.seller,l.initial_bid_cop,l.url,l.first_seen_at,l.last_seen_at,o.outcome,o.closing_price_observed_cop,o.sale_price_confirmed_cop,o.confidence FROM lots l LEFT JOIN lot_outcomes o ON o.lot_id=l.id WHERE o.outcome IN ('SOLD_CONFIRMED','CLOSED_OBSERVED','CONDITIONAL','NOT_SOLD')"""; args=[]
    if brand:sql+=" AND upper(l.brand)=upper(?)"; args.append(brand)
    if model_year:sql+=" AND l.model_year=?"; args.append(model_year)
    if line_query:sql+=" AND upper(COALESCE(l.line,l.title,'')) LIKE upper(?)"; args.append(f"%{line_query}%")
    sql+=" ORDER BY l.last_seen_at DESC LIMIT ?"; args.append(limit)
    rows=[dict(r) for r in conn.execute(sql,args).fetchall()]
    for r in rows:
        r["vehicle_key"]=normalize_vehicle_key(r["title"],r["brand"],r["model_year"]); r["historical_value_cop"]=r["sale_price_confirmed_cop"] or r["closing_price_observed_cop"]
        atts=conn.execute("SELECT name,url,kind FROM lot_attachments WHERE lot_id=? ORDER BY id",(r["id"],)).fetchall(); r["peritajes"]=[dict(a) for a in atts if a["kind"]=="PERITAJE"]
        prov=provenance_for_lot(conn,r["id"]); r["provenance"]=prov
        if prov:
            best=prov[0]; r["data_quality"]=quality_label(best["source_type"],float(best["confidence"])); r["data_confidence"]=float(best["confidence"]); r["data_source_type"]=best["source_type"]
        else:r["data_quality"]="REFERENCIAL"; r["data_confidence"]=0.0; r["data_source_type"]=None
    return rows

def grouped_history(conn:sqlite3.Connection,brand=None,model_year=None,line_query=None):
    rows=historical_rows(conn,brand,model_year,line_query,limit=10000); groups={}
    for r in rows:
        v=r.get("historical_value_cop")
        if not v:continue
        g=groups.setdefault(r["vehicle_key"],{"vehicle_key":r["vehicle_key"],"brand":r["brand"],"model_year":r["model_year"],"sample_titles":[],"values":[],"sold_confirmed":0,"closed_observed":0})
        if r["title"] and r["title"] not in g["sample_titles"] and len(g["sample_titles"])<3:g["sample_titles"].append(r["title"])
        g["values"].append(int(v))
        if r["outcome"]=="SOLD_CONFIRMED":g["sold_confirmed"]+=1
        elif r["outcome"]=="CLOSED_OBSERVED":g["closed_observed"]+=1
    out=[]
    for g in groups.values():
        vals=sorted(g.pop("values")); g.update({"observations":len(vals),"min_cop":min(vals),"median_cop":int(median(vals)),"max_cop":max(vals),"avg_cop":int(round(sum(vals)/len(vals)))}); out.append(g)
    return sorted(out,key=lambda x:(x["brand"] or "",x["model_year"] or 0,x["vehicle_key"]))

def history_csv(conn:sqlite3.Connection,brand=None,model_year=None,line_query=None)->bytes:
    rows=historical_rows(conn,brand,model_year,line_query,limit=100000); buf=io.StringIO(); cols=["external_lot_id","brand","title","model_year","city","seller","initial_bid_cop","outcome","closing_price_observed_cop","sale_price_confirmed_cop","historical_value_cop","confidence","last_seen_at","data_quality","data_confidence","data_source_type","peritaje_urls","url"]
    w=csv.DictWriter(buf,fieldnames=cols,extrasaction="ignore"); w.writeheader()
    for r in rows:
        x=dict(r); x["peritaje_urls"]=" | ".join(a["url"] for a in r["peritajes"]); w.writerow(x)
    return buf.getvalue().encode("utf-8-sig")
