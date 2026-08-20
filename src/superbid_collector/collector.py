from __future__ import annotations
import asyncio
from pathlib import Path
from .fetchers import fetch_http,fetch_browser
from .parsers import parse_lot_html
from .storage import Store
from .attachments import extract_html_attachments
from .storage_extensions import save_attachments
from .provenance import save_provenance

def collect_one(url:str,db:str,browser:bool=False):
    html=asyncio.run(fetch_browser(url)) if browser else fetch_http(url); obs=parse_lot_html(url,html); store=Store(db);store.init();lot_id=store.save(obs);save_attachments(store.conn,lot_id,extract_html_attachments(url,html))
    fields={"title":obs.title is not None,"brand":obs.brand is not None,"model_year":obs.model_year is not None,"initial_bid_cop":obs.initial_bid_cop is not None,"displayed_price_cop":obs.displayed_price_cop is not None,"closes_at_text":obs.closes_at_text is not None}
    save_provenance(store.conn,lot_id,source_type="superbid_rendered_html",source_url=url,fields=fields,confidence=.75,note="Captured from a public rendered Superbid page.");return lot_id,obs

def read_urls(path:str|Path)->list[str]:
    return [x.strip() for x in Path(path).read_text(encoding="utf-8").splitlines() if x.strip() and not x.strip().startswith("#")]
