from __future__ import annotations
import re
AMOUNT_KEYS=("amount","value","price","bid_value","bid_amount","lance","valor")
DATE_KEYS=("date","created_at","create_at","timestamp","time","bid_date","date_time")
def _to_int(v):
    if isinstance(v,(int,float)) and not isinstance(v,bool): return int(v)
    if isinstance(v,str):
        digits=re.sub(r"\D","",v); return int(digits) if digits else None
    return None
def extract_bid_history(payload)->list[dict]:
    out,seen=[],set()
    def parse_list(items):
        local=[]
        for i,x in enumerate(items):
            if not isinstance(x,dict): continue
            amount=next((_to_int(x.get(k)) for k in AMOUNT_KEYS if _to_int(x.get(k))),None)
            if not amount: continue
            date=next((str(x.get(k)) for k in DATE_KEYS if x.get(k) is not None),None)
            key=(amount,date,i)
            if key in seen: continue
            seen.add(key); local.append({"sequence_no":i+1,"amount_cop":amount,"bid_at_text":date})
        return local
    def walk(obj):
        if isinstance(obj,dict):
            for k,v in obj.items():
                lk=str(k).lower()
                if ("bid" in lk or "lance" in lk) and any(term in lk for term in ("history","histor","list","bids","lances")) and isinstance(v,list): out.extend(parse_list(v))
                walk(v)
        elif isinstance(obj,list):
            for v in obj: walk(v)
    walk(payload); return out
