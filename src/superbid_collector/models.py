from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from pydantic import BaseModel, Field


class Outcome(StrEnum):
    UNKNOWN = "UNKNOWN"
    ACTIVE = "ACTIVE"
    CONDITIONAL = "CONDITIONAL"
    AFTER_MARKET = "AFTER_MARKET"
    CLOSED_OBSERVED = "CLOSED_OBSERVED"
    SOLD_CONFIRMED = "SOLD_CONFIRMED"
    NOT_SOLD = "NOT_SOLD"
    WITHDRAWN = "WITHDRAWN"
    NO_BID = "NO_BID"


class LotObservation(BaseModel):
    source: str = "superbid_co"
    external_lot_id: str
    url: str
    title: str | None = None
    brand: str | None = None
    line: str | None = None
    version: str | None = None
    model_year: int | None = None
    plate: str | None = None
    plate_is_partial: bool = False
    mileage_km: int | None = None
    engine_cc: int | None = None
    fuel: str | None = None
    transmission: str | None = None
    drivetrain: str | None = None
    city: str | None = None
    seller: str | None = None
    initial_bid_cop: int | None = None
    displayed_price_cop: int | None = None
    displayed_price_label: str | None = None
    bid_count: int | None = None
    status_text: str | None = None
    outcome: Outcome = Outcome.UNKNOWN
    closes_at_text: str | None = None
    observed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    evidence: dict = Field(default_factory=dict)
