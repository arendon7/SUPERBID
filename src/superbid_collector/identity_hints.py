from __future__ import annotations

import re
from dataclasses import dataclass

IDENTITY_HINT_GUARDRAIL = "AUTOMATED_IDENTITY_HINT_NOT_HUMAN_EVIDENCE_OR_MATCH"

ENGINE_CC_RE = re.compile(r"\b(\d{3,5})\s*CC\b", re.I)

_MANUAL_TRANSMISSION_RE = re.compile(r"\b(?:MT|MANUAL|MEC[ÁA]NIC[AO])\b", re.I)
_AUTOMATIC_TRANSMISSION_RE = re.compile(
    r"\b(?:AT|TP|CVT|DCT|DSG|AUT|AUTOM[ÁA]TIC[AO])\b", re.I
)
_4X4_RE = re.compile(r"\b(?:4\s*[Xx]\s*4|4WD|AWD)\b", re.I)
_4X2_RE = re.compile(r"\b(?:4\s*[Xx]\s*2|2WD)\b", re.I)
_HYBRID_RE = re.compile(r"\b(?:H[IÍ]BRID[AO]|HYBRID|HEV|PHEV)\b", re.I)
_ELECTRIC_RE = re.compile(r"\b(?:EL[EÉ]CTRIC[AO]|ELECTRIC|EV|BEV)\b", re.I)
_DIESEL_RE = re.compile(r"\b(?:DI[EÉ]SEL|DIESEL)\b", re.I)
_CNG_RE = re.compile(r"\b(?:GNV|GNC|CNG|GAS\s+NATURAL)\b", re.I)
_GASOLINE_RE = re.compile(r"\b(?:GASOLINA|GASOLINE|PETROL)\b", re.I)


@dataclass(frozen=True)
class VehicleIdentityHints:
    engine_cc: int | None = None
    transmission: str | None = None
    drivetrain: str | None = None
    fuel: str | None = None

    def as_dict(self) -> dict[str, int | str | None]:
        return {
            "engine_cc": self.engine_cc,
            "transmission": self.transmission,
            "drivetrain": self.drivetrain,
            "fuel": self.fuel,
        }


def _unique_engine_cc(text: str) -> int | None:
    values = {int(match.group(1)) for match in ENGINE_CC_RE.finditer(text)}
    return next(iter(values)) if len(values) == 1 else None


def _exclusive_flag(text: str, rules: tuple[tuple[str, re.Pattern[str]], ...]) -> str | None:
    values = {label for label, pattern in rules if pattern.search(text)}
    return next(iter(values)) if len(values) == 1 else None


def _fuel_hint(text: str) -> str | None:
    # Hybrid/electric labels are treated as higher-order propulsion declarations.
    if _HYBRID_RE.search(text):
        return "HYBRID"
    if _ELECTRIC_RE.search(text):
        return "ELECTRIC"
    return _exclusive_flag(
        text,
        (
            ("DIESEL", _DIESEL_RE),
            ("CNG", _CNG_RE),
            ("GASOLINE", _GASOLINE_RE),
        ),
    )


def extract_vehicle_identity_hints(text: str | None) -> VehicleIdentityHints:
    raw = str(text or "")
    return VehicleIdentityHints(
        engine_cc=_unique_engine_cc(raw),
        transmission=_exclusive_flag(
            raw,
            (
                ("MANUAL", _MANUAL_TRANSMISSION_RE),
                ("AUTOMATIC", _AUTOMATIC_TRANSMISSION_RE),
            ),
        ),
        drivetrain=_exclusive_flag(raw, (("4X4_AWD", _4X4_RE), ("4X2_2WD", _4X2_RE))),
        fuel=_fuel_hint(raw),
    )


def compare_vehicle_identity_hints(
    lot_text: str | None, candidate_text: str | None
) -> dict[str, dict[str, object]]:
    lot = extract_vehicle_identity_hints(lot_text).as_dict()
    candidate = extract_vehicle_identity_hints(candidate_text).as_dict()
    out: dict[str, dict[str, object]] = {}
    for key in ("engine_cc", "transmission", "drivetrain", "fuel"):
        lot_value = lot[key]
        candidate_value = candidate[key]
        if lot_value is None:
            status = "LOT_UNKNOWN"
        elif candidate_value is None:
            status = "CANDIDATE_UNKNOWN"
        elif lot_value == candidate_value:
            status = "CONSISTENT"
        else:
            status = "DIFFERS"
        out[key] = {
            "lot": lot_value,
            "candidate": candidate_value,
            "status": status,
        }
    return out
