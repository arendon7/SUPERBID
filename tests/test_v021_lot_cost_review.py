from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MIG = (ROOT / "supabase/migrations/20260821050145_lot_cost_review_workflow_v21.sql").read_text(encoding="utf-8").lower()
DASH = (ROOT / "supabase/functions/superbid-dashboard/index.ts").read_text(encoding="utf-8").lower()


def test_cost_history_is_backend_only():
    assert "alter table public.lot_cost_review_history enable row level security" in MIG
    assert "revoke all on public.lot_cost_review_history from public, anon, authenticated" in MIG
    assert "grant select, insert on public.lot_cost_review_history to service_role" in MIG


def test_review_requires_all_eight_costs():
    assert "p_mark_reviewed and not v_complete" in MIG
    for field in [
        "p_transfer_cop", "p_taxes_soat_cop", "p_transport_cop", "p_repair_cop",
        "p_detailing_cop", "p_financing_cop", "p_admin_fee_cop", "p_contingency_cop",
    ]:
        assert field in MIG


def test_any_draft_save_invalidates_old_review():
    assert "v_reviewed_at := case when p_mark_reviewed and v_complete then clock_timestamp() else null end" in MIG
    assert "reviewed_at=excluded.reviewed_at" in MIG


def test_every_save_is_audited():
    assert "insert into public.lot_cost_review_history" in MIG
    assert "marked_reviewed" in MIG
    assert "source_note" in MIG


def test_write_rpc_is_service_role_only():
    assert "revoke all on function public.dashboard_save_lot_costs" in MIG
    assert "from public,anon,authenticated" in MIG
    assert "to service_role" in MIG


def test_dashboard_exposes_all_cost_fields_and_server_side_rpc():
    for field in [
        "transfer_cop", "taxes_soat_cop", "transport_cop", "repair_cop",
        "detailing_cop", "financing_cop", "admin_fee_cop", "contingency_cop",
    ]:
        assert field in DASH
    assert "dashboard_save_lot_costs" in DASH
    assert "guardar borrador" in DASH
    assert "guardar y marcar revisado" in DASH


def test_dashboard_rejects_negative_cost_text_before_rpc():
    assert "if(!/^\\d+$/.test(s))" in DASH
    assert "v<0||v>50000000000" in DASH
