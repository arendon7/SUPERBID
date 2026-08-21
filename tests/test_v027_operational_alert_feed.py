from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MIG = (ROOT / "supabase/migrations/20260821150109_operational_alert_feed_v27.sql").read_text(encoding="utf-8").lower()
API = (ROOT / "supabase/functions/superbid-read-api/index.ts").read_text(encoding="utf-8").lower()
DASH = (ROOT / "supabase/functions/superbid-dashboard/index.ts").read_text(encoding="utf-8").lower()


def test_alert_events_are_private_and_deduplicated():
    assert "create table if not exists public.operational_alert_events" in MIG
    assert "dedupe_key text not null unique" in MIG
    assert "enable row level security" in MIG
    assert "revoke all on public.operational_alert_events from public,anon,authenticated" in MIG
    assert "grant select,insert,update on public.operational_alert_events to service_role" in MIG


def test_alert_types_and_interpretation_are_operational_only():
    for value in ("closing_2h", "high_pressure", "close_extension"):
        assert value in MIG
    assert "operational_alert_not_buy_signal" in MIG
    assert "interpretation='operational_alert_not_buy_signal'" in MIG


def test_close_extensions_are_derived_from_real_close_changes():
    assert "create or replace view public.lot_close_extension_events" in MIG
    assert "lag(s.closes_at)" in MIG
    assert "o.closes_at>o.prev_closes_at" in MIG
    assert "extension_minutes" in MIG


def test_refresh_function_deduplicates_and_does_not_write_decisions():
    fn = MIG[MIG.index("create or replace function public.refresh_operational_alerts"):]
    assert "on conflict(dedupe_key) do nothing" in fn
    assert "review_now" in fn
    assert "pressure_level='high'" in fn
    assert "max_bid_market_validated_cop" not in fn
    assert "final_decision" not in fn
    assert "update public.dashboard" not in fn


def test_alert_cron_runs_each_minute():
    assert "superbid-operational-alerts-v27" in MIG
    assert "'* * * * *'" in MIG
    assert "select public.refresh_operational_alerts();" in MIG


def test_alert_feed_view_is_backend_only():
    assert "create or replace view public.dashboard_operational_alert_feed" in MIG
    assert "revoke all on public.dashboard_operational_alert_feed from public,anon,authenticated" in MIG
    assert "grant select on public.dashboard_operational_alert_feed to service_role" in MIG


def test_private_api_exposes_alerts_with_auth_guard():
    assert 'p==="/alerts"' in API
    assert "dashboard_operational_alert_feed" in API
    assert "alert_type=eq." in API
    assert "severity=eq." in API
    assert "is_open=eq." in API
    assert "unauthorized" in API and "401" in API
    assert 'version:"0.27"' in API


def test_dashboard_has_alert_feed_without_buy_action():
    assert "/superbid-dashboard/alerts" in DASH
    assert "alertas operativas" in DASH
    assert "operational_alert_not_buy_signal" in DASH
    assert "ninguna alerta modifica score, puja máxima ni decisión final" in DASH
    start = DASH.index("async function alertspage")
    end = DASH.index("const input", start)
    page = DASH[start:end]
    assert "dashboard_operational_alert_feed" in page
    assert "dashboard_save_lot_costs" not in page
    assert "final_decision" not in page
    assert "max_bid_market_validated_cop" not in page


def test_alert_ui_remains_server_rendered():
    assert "<script" not in DASH
    assert 'method="get"' in DASH
    assert "deno.serve" in DASH
