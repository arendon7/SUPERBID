from __future__ import annotations
import os
from .storage import Store
from .discovery import add_discovery_source
def bootstrap(db:str):
    s=Store(db); s.init()
    raw=os.getenv("SUPERBID_DISCOVERY_URLS","")
    for item in raw.replace("\n",",").split(","):
        url=item.strip()
        if url:
            add_discovery_source(s,url)
    paginated = os.getenv("SUPERBID_DISCOVERY_PAGINATED_URLS", "")
    for item in paginated.replace("\n", ",").split(","):
        url = item.strip()
        if url:
            add_discovery_source(s, url, source_type="paginated")
    return s
