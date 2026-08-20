from __future__ import annotations
import random,time
from urllib.parse import urlparse
import httpx
ALLOWED_HOST_SUFFIXES=("superbid.com.co","superbid.net")
UA="SUPERBID-Deal-Research/0.1 (+private vehicle-market research)"
def validate_url(url:str)->None:
    p=urlparse(url)
    if p.scheme not in {"http","https"}: raise ValueError("Solo HTTP/HTTPS.")
    host=(p.hostname or "").lower()
    if not any(host==suffix or host.endswith("."+suffix) for suffix in ALLOWED_HOST_SUFFIXES): raise ValueError(f"Dominio no permitido por este adaptador: {host}")
def fetch_http(url:str,timeout:float=25.0)->str:
    validate_url(url); headers={"User-Agent":UA,"Accept-Language":"es-CO,es;q=0.9,en;q=0.5"}
    with httpx.Client(headers=headers,timeout=timeout,follow_redirects=True) as client:
        last_exc=None
        for attempt in range(4):
            try:
                r=client.get(url)
                if r.status_code==429: time.sleep((2**attempt)+random.random()); continue
                r.raise_for_status(); return r.text
            except httpx.HTTPError as exc:
                last_exc=exc; time.sleep((2**attempt)+random.random())
        raise RuntimeError(f"No se pudo obtener {url}: {last_exc}")
async def fetch_browser(url:str,wait_ms:int=1800)->str:
    validate_url(url)
    try: from playwright.async_api import async_playwright
    except ImportError as exc: raise RuntimeError('Instale el extra browser: pip install -e ".[browser]"') from exc
    async with async_playwright() as p:
        browser=await p.chromium.launch(headless=True); context=await browser.new_context(user_agent=UA,locale="es-CO",viewport={"width":1440,"height":1100}); page=await context.new_page(); await page.goto(url,wait_until="domcontentloaded",timeout=45000); await page.wait_for_timeout(wait_ms); html=await page.content(); await browser.close(); return html
async def probe_network(url:str,seconds:int=12)->list[dict]:
    validate_url(url)
    try: from playwright.async_api import async_playwright
    except ImportError as exc: raise RuntimeError('Instale el extra browser: pip install -e ".[browser]"') from exc
    found={}
    async with async_playwright() as p:
        browser=await p.chromium.launch(headless=True); context=await browser.new_context(user_agent=UA,locale="es-CO"); page=await context.new_page()
        async def on_response(resp):
            try:
                ct=(resp.headers.get("content-type") or "").lower(); rt=resp.request.resource_type
                if "json" in ct or rt in {"xhr","fetch"}: found[resp.url]={"status":resp.status,"content_type":ct,"resource_type":rt,"url":resp.url}
            except Exception: return
        page.on("response",on_response); await page.goto(url,wait_until="domcontentloaded",timeout=45000); await page.wait_for_timeout(seconds*1000); await browser.close()
    return list(found.values())
