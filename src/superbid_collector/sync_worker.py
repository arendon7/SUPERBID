from __future__ import annotations

import json
import os
import time

from .storage import Store
from .supabase_sync import sync_once, SupabaseREST
from .fasecolda_sync import sync_fasecolda

DB=os.getenv("SUPERBID_DB","superbid.db")
INTERVAL=int(os.getenv("SUPERBID_SYNC_INTERVAL","300"))


def main():
    s=Store(DB); s.init()
    if not os.getenv("SUPABASE_URL") or not os.getenv("SUPABASE_SERVICE_ROLE_KEY"):
        print(json.dumps({"sync_worker":"disabled","reason":"Supabase credentials missing"}))
        while True:
            time.sleep(3600)

    print(json.dumps({"sync_worker":"started","interval":INTERVAL}))
    while True:
        try:
            counts=sync_once(s.conn)
            remote=SupabaseREST()
            try:
                counts["fasecolda_values"] = sync_fasecolda(s.conn, remote)
            finally:
                remote.close()
            print(json.dumps({"supabase_sync":"ok","counts":counts},ensure_ascii=False))
        except Exception as exc:
            print(json.dumps({"supabase_sync":"error","error":str(exc)},ensure_ascii=False))
        time.sleep(INTERVAL)


if __name__=="__main__":
    main()
