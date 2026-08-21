from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MIG = (ROOT / "supabase/migrations/20260821050850_historical_intelligence_v22.sql").read_text(encoding="utf-8").lower()
API = (ROOT / "supabase/functions/superbid-read-api/index.ts").read_text(encoding="utf-8").lower()
DASH = (ROOT / "supabase/functions/superbid-dashboard/index.ts").read_text(encoding="utf-8").lower()


def test_historical_value_keeps_confirmed_and_observed_semantics():
    assert "sale_price_confirmed_cop is not null then 'sale_confirmed'" in MIG
    assert "closing_price_observed_cop is not null then 'closing_observed'" in MIG
    assert "else 'no_final_value'" in MIG


def test_timeline_does_not_expose_raw_snapshot_evidence():
    fn = MIG[MIG.index("create or replace function public.dashboard_lot_timeline"):]
    assert "'displayed_price_cop'" in fn
    assert "'bid_count'" in fn
    assert "'evidence'" not in fn
    assert "reservedprice" not in fn


def test_timeline_preserves_individual_bid_history_separately():
    assert "'public_bid_history'" in MIG
    assert "from public.lot_bid_history" in MIG
    assert "'snapshots'" in MIG
    assert "from public.auction_snapshots" in MIG


def test_historical_objects_are_backend_only():
    assert "revoke all on public.dashboard_history_export from public,anon,authenticated" in MIG
    assert "grant select on public.dashboard_history_export to service_role" in MIG
    assert "revoke all on function public.dashboard_lot_timeline(text) from public,anon,authenticated" in MIG


def test_read_api_exports_csv_and_timeline():
    assert "/timeline" in API
    assert "/export/history.csv" in API
    assert "sale_price_confirmed_cop" in API
    assert "closing_price_observed_cop" in API
    assert "historical_value_type" in API
    assert "content-disposition" in API


def test_dashboard_states_snapshots_are_not_adjudication():
    assert "snapshots públicos; no equivalen a adjudicación" in DASH
    assert "no hay lances individuales públicos almacenados para este lote. no se infieren desde snapshots" in DASH
    assert "sale_confirmed" in DASH
    assert "closing_observed" in DASH
    assert "no_final_value" in DASH


def test_dashboard_has_history_and_csv_navigation():
    assert "/history" in DASH
    assert "/export/history.csv" in DASH
    assert "histórico de vehículos" in DASH
