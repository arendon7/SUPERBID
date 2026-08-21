import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MIG = (ROOT / "supabase/migrations/20260821142412_bid_pressure_metrics_v24.sql").read_text(encoding="utf-8").lower()
API = (ROOT / "supabase/functions/superbid-read-api/index.ts").read_text(encoding="utf-8").lower()
DASH = (ROOT / "supabase/functions/superbid-dashboard/index.ts").read_text(encoding="utf-8").lower()


def test_pressure_view_is_backend_only():
    assert "create or replace view public.lot_bid_pressure_current" in MIG
    assert "revoke all on public.lot_bid_pressure_current from public,anon,authenticated" in MIG
    assert "grant select on public.lot_bid_pressure_current to service_role" in MIG


def test_pressure_is_explicitly_observational_not_buy_signal():
    assert "observational_only_not_buy_signal" in MIG
    assert "pressure_level" in MIG
    assert "close_extension_count" in MIG
    assert "changes_2h" in MIG
    assert "bid_up_2h" in MIG


def test_pressure_rpc_is_private():
    assert "dashboard_bid_pressure" in MIG
    assert "revoke all on function public.dashboard_bid_pressure(text) from public,anon,authenticated" in MIG
    assert "grant execute on function public.dashboard_bid_pressure(text) to service_role" in MIG


def test_private_api_exposes_pressure_endpoint():
    assert "/bid-pressure" in API
    assert "dashboard_bid_pressure" in API
    match = re.search(r'version:"(\d+)\.(\d+)"', API)
    assert match is not None
    assert tuple(map(int, match.groups())) >= (0, 24)


def test_dashboard_keeps_pressure_separate_from_final_decision():
    assert "presión competitiva observada" in DASH
    assert "no modifica por sí sola el score ni la decisión final" in DASH
    assert "dashboard_bid_pressure" in DASH
    assert "extensiones de cierre" in DASH
