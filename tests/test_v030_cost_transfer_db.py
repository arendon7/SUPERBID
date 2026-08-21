from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MIG = (ROOT / "supabase/migrations/20260821162645_peritaje_cost_transfer_v30.sql").read_text(encoding="utf-8").lower()


def test_transfer_history_private_and_auditable():
    assert "create table if not exists public.peritaje_repair_cost_transfer_history" in MIG
    assert "enable row level security" in MIG
    assert "revoke all on public.peritaje_repair_cost_transfer_history from public,anon,authenticated" in MIG
    assert "manual_peritaje_cost_transfer_not_automatic" in MIG


def test_transfer_requires_reviewed_peritaje_and_scenario():
    fn = MIG[MIG.index("create or replace function public.dashboard_transfer_peritaje_repair_to_costs"):]
    assert "v_review.reviewed_at is null" in fn
    assert "peritaje review must be explicitly reviewed before transfer" in fn
    assert "v_scenario not in ('low','base','high')" in fn
    assert "selected repair scenario has no value" in fn


def test_transfer_invalidates_cost_review_and_audits_draft():
    fn = MIG[MIG.index("create or replace function public.dashboard_transfer_peritaje_repair_to_costs"):MIG.index("revoke all on function public.dashboard_transfer_peritaje_repair_to_costs")]
    assert "set repair_cop=v_selected" in fn
    assert "reviewed_at=null" in fn
    assert "v_cost.source_note,false,null" in fn
    assert "cost_review_invalidated',true" in fn


def test_cost_readiness_states_are_explicit():
    assert "create or replace view public.dashboard_cost_readiness_current" in MIG
    for value in ("'no_costs'", "'draft'", "'reviewed'", "'not_transferred'", "'match_low'", "'match_base'", "'match_high'", "'custom'"):
        assert value in MIG
    assert "completed_cost_fields" in MIG
    assert "peritaje_ready_for_cost_transfer" in MIG
