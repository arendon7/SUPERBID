import pytest
from superbid_collector.storage import Store
from superbid_collector.discovery import discover_from_source

@pytest.mark.asyncio
async def test_paginated_discovery_stops_on_empty_second_page(tmp_path, monkeypatch):
    s=Store(tmp_path/"d.db"); s.init()
    calls=[]
    async def fake_capture(store, url, seconds):
        calls.append(url)
        if "pageNumber=1" in url:
            return {"lots_found":[{
                "external_lot_id":"1234567",
                "url":"https://www.superbid.com.co/oferta/a-1234567",
                "closes_at_text":"2026-08-21 12:00"
            }],"saved":1,"attachments_saved":0,"bids_saved":0,"errors":[]}
        return {"lots_found":[],"saved":0,"attachments_saved":0,"bids_saved":0,"errors":[]}
    monkeypatch.setattr("superbid_collector.discovery._capture_source_page", fake_capture)
    monkeypatch.setenv("SUPERBID_DISCOVERY_MAX_PAGES","5")
    result=await discover_from_source(
        s,"https://www.superbid.com.co/categoria/vehiculos?searchType=opened",
        seconds=1,source_type="paginated"
    )
    assert result["pages_scanned"]==2
    assert len(result["lots_found"])==1
    assert len(calls)==2
    q=s.conn.execute("select count(*) c from collection_queue").fetchone()
    assert q["c"]==1
