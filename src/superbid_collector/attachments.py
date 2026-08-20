from __future__ import annotations

import json
import re
from urllib.parse import urljoin
from bs4 import BeautifulSoup

PERITAJE_TERMS = (
    "peritaje", "peritazgo", "inspeccion", "inspección", "informe tecnico",
    "informe técnico", "avaluo", "avalúo", "diagnostico", "diagnóstico",
    "revision vehicular", "revisión vehicular", "ficha de inspeccion",
    "ficha de inspección",
)
CONDITIONS_TERMS = (
    "condiciones", "terminos", "términos", "reglamento",
    "condiciones de venta", "condiciones particulares",
)
CONTRACT_TERMS = ("contrato", "minuta", "compraventa")
EMBEDDED_JSON_KEYS = {"productcustomjson", "customjson", "custom_json", "metadatajson", "metadata_json"}


def classify_attachment(name: str | None, url: str) -> str:
    hay = f"{name or ''} {url}".lower()
    if any(t in hay for t in PERITAJE_TERMS): return "PERITAJE"
    if any(t in hay for t in CONDITIONS_TERMS): return "CONDICIONES"
    if any(t in hay for t in CONTRACT_TERMS): return "CONTRATO"
    if re.search(r"\.(?:jpg|jpeg|png|webp)(?:\?|$)", url, re.I): return "IMAGEN"
    if re.search(r"\.pdf(?:\?|$)", url, re.I): return "PDF_OTRO"
    return "OTRO"


def _looks_like_file_url(url: str) -> bool:
    return bool(
        re.search(r"\.(?:pdf|docx?|xlsx?|jpe?g|png|webp|zip)(?:[?#]|$)", url, re.I)
        or any(x in url.lower() for x in ("/attachment", "/document", "/anexo", "/arquivo", "/file/"))
    )


def _lot_context(text: str) -> bool:
    t = text.lower()
    return any(x in t for x in PERITAJE_TERMS + CONDITIONS_TERMS + CONTRACT_TERMS) or "anexo" in t


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
        if not (_looks_like_file_url(url) or _lot_context(combined)):
            continue
        seen.add(url)
        out.append({"name": name, "url": url, "kind": classify_attachment(name, url), "source": "html_anchor"})
    return out


def extract_json_attachments(payload) -> list[dict]:
    """Extract public file links, including JSON embedded in productCustomJson strings."""
    out, seen = [], set()
    file_keys = {
        "url", "uri", "href", "link", "file", "file_url", "file_uri",
        "document_url", "attachment_url", "download_url", "path", "value",
    }
    name_keys = {"name", "filename", "file_name", "title", "description", "desc", "label", "key"}

    def add(name, url, source="json"):
        if not isinstance(url, str) or not url.startswith(("http://", "https://")) or url in seen:
            return
        context = f"{name or ''} {url}"
        if not (_looks_like_file_url(url) or _lot_context(context)):
            return
        seen.add(url)
        out.append({"name": name, "url": url, "kind": classify_attachment(name, url), "source": source})

    def walk(obj, source="json"):
        if isinstance(obj, dict):
            string_items = {str(k).lower(): v for k, v in obj.items() if isinstance(v, str)}
            name = next((string_items[k] for k in name_keys if isinstance(string_items.get(k), str)), None)
            context = " ".join(string_items.values()).lower()
            for k, v in string_items.items():
                if v.startswith(("http://", "https://")):
                    if k in file_keys or any(x in k for x in ("file", "document", "attachment", "anexo", "annex")) or _lot_context(context):
                        add(name, v, source)
                if k in EMBEDDED_JSON_KEYS and v.lstrip().startswith(("{", "[")):
                    try:
                        walk(json.loads(v), source="embedded_json")
                    except Exception:
                        pass
            for k, v in obj.items():
                if isinstance(v, str) and str(k).lower() in EMBEDDED_JSON_KEYS:
                    continue
                walk(v, source)
        elif isinstance(obj, list):
            for v in obj:
                walk(v, source)

    walk(payload)
    return out
