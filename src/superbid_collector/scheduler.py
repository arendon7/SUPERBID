from __future__ import annotations
from datetime import datetime,timezone
def recommended_interval_seconds(closes_at:datetime|None)->int:
    if closes_at is None:return 4*60*60
    now=datetime.now(timezone.utc)
    if closes_at.tzinfo is None:closes_at=closes_at.replace(tzinfo=timezone.utc)
    remaining=(closes_at-now).total_seconds()
    if remaining>24*3600:return 4*3600
    if remaining>2*3600:return 30*60
    if remaining>15*60:return 5*60
    return 60
