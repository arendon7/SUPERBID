from __future__ import annotations
import json,os,re
import httpx
API="https://api.mercadolibre.com";SITE="MCO"
def _attr(item:dict,names:set[str])->str|None:
    for a in item.get("attributes") or []:
        if str(a.get("id","")).upper() in names:return a.get("value_name")
    return None
def _year(item:dict)->int|None:
    raw=_attr(item,{"VEHICLE_YEAR","YEAR","MODEL_YEAR"})
    if raw:
        m=re.search(r"(?:19|20)\d{2}",str(raw))
        if m:return int(m.group(0))
    m=re.search(r"(?:19|20)\d{2}",item.get("title") or "");return int(m.group(0)) if m else None
def _mileage(item:dict)->int|None:
    raw=_attr(item,{"KILOMETERS","MILEAGE"})
    if not raw:return None
    digits=re.sub(r"\D","",str(raw));return int(digits) if digits else None
def search_vehicle_comparables(query:str,*,access_token:str|None=None,limit:int=50)->list[dict]:
    token=access_token or os.getenv("MELI_ACCESS_TOKEN")
    if not token:raise RuntimeError("Defina MELI_ACCESS_TOKEN para usar la API oficial de Mercado Libre.")
    with httpx.Client(timeout=25,headers={"Authorization":f"Bearer {token}"}) as client:
        r=client.get(f"{API}/sites/{SITE}/search",params={"q":query,"limit":max(1,min(50,limit))});r.raise_for_status();data=r.json()
    out=[]
    for item in data.get("results") or []:
        price=item.get("price")
        if not isinstance(price,(int,float)) or price<=0:continue
        seller=item.get("seller") or {};location=item.get("location") or item.get("seller_address") or {};city=None
        if isinstance(location,dict):
            city_obj=location.get("city");city=city_obj.get("name") if isinstance(city_obj,dict) else None
        out.append({"source":"mercadolibre_mco","external_id":item.get("id"),"url":item.get("permalink"),"title":item.get("title"),"asking_price_cop":int(price),"model_year":_year(item),"mileage_km":_mileage(item),"brand":_attr(item,{"BRAND"}),"line":_attr(item,{"MODEL","LINE"}),"city":city,"seller_type":"dealer" if seller.get("car_dealer") else "private_or_unknown","raw_json":json.dumps(item,ensure_ascii=False)})
    return out
