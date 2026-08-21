from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MIG = (ROOT / "supabase/migrations/20260821152308_alert_lifecycle_v28.sql").read_text(encoding="utf-8").lower()
API = (ROOT / "supabase/functions/superbid-read-api/index.ts").read_text(encoding="utf-8").lower()
DASH = (ROOT / "supabase/functions/superbid-dashboard/index.ts").read_text(encoding="utf-8").lower()


def test_alert_lifecycle_fields_and_audit_history_are_private():
    assert "manual_disposition" in MIG
    assert "system_resolved_at" in MIG
    assert "system_resolution_reason" in MIG
    assert "create table if not exists public.operational_alert_action_history" in MIG
    assert "enable row level security" in MIG
    assert "revoke all on public.operational_alert_action_history from public,anon,authenticated" in MIG
    assert "grant select,insert on public.operational_alert_action_history to service_role" in MIG


def test_manual_action_rpc_is_service_role_only_and_audited():
    assert "dashboard_set_operational_alert_disposition" in MIG
    assert "acknowledge" in MIG and "dismiss" in MIG and "reopen" in MIG
    assert "length(v_note)>1000" in MIG
    assert "insert into public.operational_alert_action_history" in MIG
    assert "alert_lifecycle_action_not_buy_signal" in MIG
    assert "revoke all on function public.dashboard_set_operational_alert_disposition(bigint,text,text) from public,anon,authenticated" in MIG
    assert "grant execute on function public.dashboard_set_operational_alert_disposition(bigint,text,text) to service_role" in MIG


def test_lifecycle_mutation_never_writes_economic_decision_fields():
    start = MIG.index("create or replace function public.dashboard_set_operational_alert_disposition")
    end = MIG.index("create or replace function public.resolve_operational_alerts", start)
    fn = MIG[start:end]
    assert "review_score=" not in fn
    assert "final_decision=" not in fn
    assert "max_bid" not in fn
    assert "lot_cost" not in fn


def test_system_resolution_is_independent_from_manual_disposition():
    assert "create or replace function public.resolve_operational_alerts" in MIG
    assert "condition_no_longer_active" in MIG
    assert "event_aged_24h" in MIG
    assert "interval '24 hours'" in MIG
    assert "system_resolved_at is null" in MIG
    assert "acknowledged_at is null and e.system_resolved_at is null" in MIG
    assert "is_system_active" in MIG
    assert "is_unattended" in MIG


def test_v28_replaces_v27_cron_with_lifecycle_cron():
    assert "cron.unschedule('superbid-operational-alerts-v27')" in MIG
    assert "superbid-alert-lifecycle-v28" in MIG
    assert "select public.refresh_operational_alert_lifecycle();" in MIG
    assert "'* * * * *'" in MIG


def test_read_api_exposes_lifecycle_fields_but_remains_read_only():
    for field in (
        "manual_disposition", "system_resolved_at", "system_resolution_reason",
        "is_unattended", "is_system_active",
    ):
        assert field in API
    assert "dashboard_set_operational_alert_disposition" not in API
    assert "req.method!==\"get\"" in API


def test_dashboard_has_server_rendered_lifecycle_actions():
    assert 'name="status"' in DASH
    assert "pendientes" in DASH
    assert "atendidas / descartadas" in DASH
    assert "resueltas por sistema" in DASH
    assert "reconocer" in DASH
    assert "descartar" in DASH
    assert "reabrir" in DASH
    assert "dashboard_set_operational_alert_disposition" in DASH
    assert "alert_lifecycle_action_not_buy_signal" not in DASH or "no modifica" in DASH
    assert "/alerts/" in DASH and "/action" in DASH
    assert "<script" not in DASH


def test_dashboard_action_handler_does_not_touch_economic_fields():
    start = DASH.index("async function savealertaction")
    end = DASH.index("const input", start)
    fn = DASH[start:end]
    assert "dashboard_set_operational_alert_disposition" in fn
    assert "dashboard_save_lot_costs" not in fn
    assert "review_score" not in fn
    assert "final_decision" not in fn
    assert "max_bid" not in fn
