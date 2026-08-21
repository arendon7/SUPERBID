from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MIG = (ROOT / "supabase/migrations/20260821051812_observed_bid_events_v23.sql").read_text(encoding="utf-8").lower()
LIM = (ROOT / "supabase/migrations/20260821141852_observed_bid_events_limit_v23.sql").read_text(encoding="utf-8").lower()
API = (ROOT / "supabase/functions/superbid-read-api/index.ts").read_text(encoding="utf-8").lower()
DASH = (ROOT / "supabase/functions/superbid-dashboard/index.ts").read_text(encoding="utf-8").lower()


def test_observed_event_view_is_backend_only_and_never_claims_individual_bid():
    assert "create or replace view public.lot_observed_bid_events" in MIG
    assert "false as is_individual_bid" in MIG
    assert "revoke all on public.lot_observed_bid_events from public,anon,authenticated" in MIG
    assert "grant select on public.lot_observed_bid_events to service_role" in MIG


def test_observed_event_rpc_is_backend_only():
    assert "dashboard_observed_bid_events" in MIG
    assert "'is_individual_bid',false" in MIG
    assert "revoke all on function public.dashboard_observed_bid_events(text) from public,anon,authenticated" in MIG
    assert "grant execute on function public.dashboard_observed_bid_events(text) to service_role" in MIG


def test_bounded_rpc_overload_limits_server_side_and_stays_private():
    assert "p_limit integer" in LIM
    assert "limit greatest(1,least(coalesce(p_limit,100),500))" in LIM
    assert "revoke all on function public.dashboard_observed_bid_events(text,integer) from public,anon,authenticated" in LIM
    assert "grant execute on function public.dashboard_observed_bid_events(text,integer) to service_role" in LIM


def test_private_api_exposes_observed_events_without_changing_auth_guard():
    assert "/observed-bid-events" in API
    assert "dashboard_observed_bid_events" in API
    assert "unauthorized" in API and "401" in API


def test_dashboard_labels_observed_changes_as_non_individual():
    assert "cambios observados de puja/precio — no son lances individuales" in DASH
    assert "un intervalo puede contener varias pujas" in DASH
    assert "lance individual" in DASH
    assert "is_individual_bid" in DASH
    assert "no hay lances individuales públicos almacenados" in DASH
