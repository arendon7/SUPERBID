from __future__ import annotations

import json
import re
from bs4 import BeautifulSoup
from .models import LotObservation, Outcome

LOT_ID_RE = re.compile(r"-(\d{6,10})(?:[/?#]|$)")
YEAR_RE = re.compile(r"\b(?:19|20)\d{2}\b")
CC_RE = re.compile(r"\b(\d{3,5})\s*CC\b", re.I)
KM_RE = re.compile(r"(\d[\d\.\s]{2,})\s*(?:KM|KMS|KIL[ÓO]METROS)", re.I)
PLATE_RE = re.compile(r"(?:PLACA|PATENTE)\s*[:\-]?\s*([A-Z0-9*]{1,8})", re.I)
CITY_RE = re.compile(r"(?:UBIC(?:ACI[ÓO]N)?\.?|UBICADO EN)\s*[:\-]?\s*([A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑa-záéíóúñ .-]{2,40})", re.I)
MONEY_RE = re.compile(r"(?:COP|\$|R\$)\s*([\d\.\,\s]+)", re.I)

KNOWN_BRANDS = [
    "TOYOTA", "RENAULT", "CHEVROLET", "FORD", "NISSAN", "KIA", "HYUNDAI",
    "VOLKSWAGEN", "MAZDA", "MITSUBISHI", "SUZUKI", "JEEP", "RAM", "JAC",
    "FOTON", "HINO", "ISUZU", "MERCEDES-BENZ", "BMW", "AUDI", "VOLVO",
    "FIAT", "PEUGEOT", "CITROEN", "SUBARU", "SSANGYONG", "BYD"
]


def lot_id_from_url(url: str) -> str:
    m = LOT_ID_RE.search(url)
    if not m:
        raise ValueError(f"No se encontró ID de lote en URL: {url}")
    return m.group(1)


def money_to_int(raw: str | None) -> int | None:
    if not raw:
        return None
    digits = re.sub(r"\D", "", raw)
    return int(digits) if digits else None


def normalize_space(s: str | None) -> str | None:
    if s is None:
        return None
    return re.sub(r"\s+", " ", s).strip()


def first_match(pattern: re.Pattern, text: str) -> str | None:
    m = pattern.search(text)
    return normalize_space(m.group(1)) if m else None


def detect_outcome(text: str) -> Outcome:
    t = text.lower()
    if any(x in t for x in ["vendido", "arrematado", "adjudicado", "venta confirmada"]):
        return Outcome.SOLD_CONFIRMED
    if any(x in t for x in ["lance condicional", "oferta condicional", "sujeto a aprobación", "pendiente de aprobación"]):
        return Outcome.CONDITIONAL
    if any(x in t for x in ["pós-leilão", "pos-leilao", "post-subasta", "after market"]):
        return Outcome.AFTER_MARKET
    if any(x in t for x in ["retirado", "retirada da oferta", "lote retirado"]):
        return Outcome.WITHDRAWN
    if any(x in t for x in ["no vendido", "não vendido", "sin venta"]):
        return Outcome.NOT_SOLD
    if any(x in t for x in ["sin ofertas", "sem lances", "no bids"]):
        return Outcome.NO_BID
    if any(x in t for x in ["encerrado", "cerrado", "finalizado"]):
        return Outcome.CLOSED_OBSERVED
    if any(x in t for x in ["ofertar", "dar lance", "enviar lance", "tempo restante", "tiempo restante"]):
        return Outcome.ACTIVE
    return Outcome.UNKNOWN


def _json_ld_objects(soup: BeautifulSoup) -> list[dict]:
    out = []
    for tag in soup.select('script[type="application/ld+json"]'):
        try:
            data = json.loads(tag.get_text(strip=True))
        except Exception:
            continue
        if isinstance(data, dict):
            out.append(data)
        elif isinstance(data, list):
            out.extend(x for x in data if isinstance(x, dict))
    return out


def _find_labeled_value(text: str, labels: list[str]) -> str | None:
    for label in labels:
        rx = re.compile(rf"{re.escape(label)}\s*[:\-]?\s*([^\n|]{{1,80}})", re.I)
        m = rx.search(text)
        if m:
            return normalize_space(m.group(1))
    return None


def _find_money_after(text: str, labels: list[str]) -> tuple[int | None, str | None]:
    for label in labels:
        rx = re.compile(rf"{re.escape(label)}\s*[:\-]?\s*(?:COP\s*)?\$?\s*([\d\.\,\s]+)", re.I)
        m = rx.search(text)
        if m:
            return money_to_int(m.group(1)), label
    return None, None


def parse_lot_html(url: str, html: str) -> LotObservation:
    soup = BeautifulSoup(html, "html.parser")
    text = normalize_space(soup.get_text("\n", strip=True)) or ""
    title = None

    og = soup.select_one('meta[property="og:title"]')
    if og and og.get("content"):
        title = normalize_space(og["content"])
    if not title and soup.title:
        title = normalize_space(soup.title.get_text(" ", strip=True))
    if not title:
        h1 = soup.find("h1")
        title = normalize_space(h1.get_text(" ", strip=True)) if h1 else None

    for obj in _json_ld_objects(soup):
        if not title and isinstance(obj.get("name"), str):
            title = normalize_space(obj["name"])

    vehicle_text = " ".join(x for x in [title, text[:8000]] if x)
    brand = next((b for b in KNOWN_BRANDS if re.search(rf"\b{re.escape(b)}\b", vehicle_text, re.I)), None)
    years = [int(y) for y in YEAR_RE.findall(vehicle_text)]
    model_year = years[0] if years else None
    plate = first_match(PLATE_RE, vehicle_text)
    partial = bool(plate and ("*" in plate or len(plate) < 6))
    cc = first_match(CC_RE, vehicle_text)
    km = first_match(KM_RE, vehicle_text)
    city = first_match(CITY_RE, vehicle_text)
    initial_bid, initial_label = _find_money_after(text, ["Oferta inicial", "Lance inicial", "Valor inicial", "Precio inicial"])
    displayed_price, display_label = _find_money_after(text, ["Lance actual", "Oferta actual", "Maior lance", "Mayor oferta", "Valor actual", "Precio actual", "Último lance", "Ultimo lance"])
    seller = _find_labeled_value(text, ["Vendedor", "Empresa vendedora", "Seller"])
    closes = _find_labeled_value(text, ["Cierre", "Cierra", "Encerramento", "Fecha de cierre", "Data de encerramento"])
    status = _find_labeled_value(text, ["Estado", "Status"])
    outcome = detect_outcome(" ".join(x for x in [status, text[:12000]] if x))

    return LotObservation(
        external_lot_id=lot_id_from_url(url), url=url, title=title, brand=brand,
        model_year=model_year, plate=plate, plate_is_partial=partial,
        mileage_km=money_to_int(km), engine_cc=int(cc) if cc else None,
        city=city, seller=seller, initial_bid_cop=initial_bid,
        displayed_price_cop=displayed_price, displayed_price_label=display_label,
        status_text=status, outcome=outcome, closes_at_text=closes,
        evidence={"parser":"heuristic_html_v1","initial_price_label":initial_label,"displayed_price_label":display_label},
    )
