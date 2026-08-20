from __future__ import annotations

import re
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup


PERITAJE_TERMS = (
    "peritaje", "peritazgo", "inspeccion", "inspección",
    "informe tecnico", "informe técnico", "avaluo", "avalúo",
    "diagnostico", "diagnóstico", "revision vehicular", "revisión vehicular",
    "ficha de inspeccion", "ficha de inspección",
)

CONDITIONS_TERMS = (
    "condiciones", "terminos", "términos", "reglamento",
    "condiciones de venta", "condiciones particulares",
)

CONTRACT_TERMS = ("contrato", "minuta", "compraventa")


def classify_attachment(name: str | None, url: str) -> str:
    hay = f"{name or ''} {url}".lower()
    if any(t in hay for t in PERITAJE_TERMS): return "PERITAJE"
    if any(t in hay for t in CONDITIONS_TERMS): return "CONDICIONES"
    if any(t in hay for t in CONTRACT_TERMS): return "CONTRATO"
    if re.search(r"\.(?:jpg|jpeg|png|webp)(?:\?|$)", url, re.I): return "IMAGEN"
    if re.search(r"\.pdf(?:\?|$)", url, re.I): return "PDF_OTRO"
    return "OTRO"


def _looks_like_file_url(url: str) -> bool:
    return bool(re.search(r"\.(?:pdf|docx?|xlsx?|jpe?g|png|webp|zip)(?:[?#]|$)", url, re.I) or any(x in url.lower() for x in ("/attachment", "/document", "/anexo", "/arquivo", "/file/")))


def extract_html_attachments(page_url: str, html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    out, seen = [], set()
    for a in soup.find_all("a", href=True):
        raw = a.get("href")
        if not raw: continue
        url = urljoin(page_url, raw)
        if url in seen: continue
        name = " ".join(a.stripped_strings).strip() or None
        combined = f"{name or ''} {url}".lower()
        is_relevant = (_looks_like_file_url(url) or any(t in combined for t in PERITAJE_TERMS + CONDITIONS_TERMS + CONTRACT_TERMS) or "anexo" in combined)
        if not is_relevant: continue
        seen.add(url)
        out.append({"name":name,"url":url,"kind":classify_attachment(name,url),"source":"html_anchor"})
    return out


def extract_json_attachments(payload) -> list[dict]:
    out, seen = [], set()
    file_key_terms={"url","uri","href","link","file","file_url","file_uri","document_url","attachment_url","download_url","path"}
    name_key_terms={"name","filename","file_name","title","description","desc","label"}
    def walk(obj):
        if isinstance(obj, dict):
            string_items={str(k).lower():v for k,v in obj.items() if isinstance(v,str)}
            urls=[]
            for k,v in string_items.items():
                if k in file_key_terms or any(x in k for x in ("file","document","attachment","anexo","annex")):
                    if v.startswith(("http://","https://")) and _looks_like_file_url(v): urls.append(v)
            if not urls:
                for k,v in string_items.items():
                    if k in file_key_terms and v.startswith(("http://","https://")):
                        context=" ".join(string_items.values()).lower()
                        if any(t in context for t in PERITAJE_TERMS+CONDITIONS_TERMS+CONTRACT_TERMS) or "anexo" in context: urls.append(v)
            name=None
            for k in name_key_terms:
                if isinstance(string_items.get(k),str): name=string_items[k]; break
            for url in urls:
                if url in seen: continue
                seen.add(url)
                out.append({"name":name,"url":url,"kind":classify_attachment(name,url),"source":"json"})
            for v in obj.values(): walk(v)
        elif isinstance(obj,list):
            for v in obj: walk(v)
    walk(payload)
    return out
