from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
MIG = (ROOT / "supabase/migrations/20260821165026_economic_readiness_v31.sql").read_text(encoding="utf-8").lower()
API = (ROOT / "supabase/functions/superbid-read-api/index.ts").read_text(encoding="utf-8").lower()


def test_readiness_view_is_private_and_not_buy_signal():
    assert "create or replace view public.dashboard_economic_readiness_current" in MIG
    assert "revoke all on public.dashboard_economic_readiness_current from public, anon, authenticated" in MIG
    assert "grant select on public.dashboard_economic_readiness_current to service_role" in MIG
    assert "economic_readiness_not_buy_signal" in MIG


def test_public_peritaje_requires_human_review_when_available():
    assert "peritaje_not_reviewed" in MIG
    assert "review_peritaje" in MIG
    assert "peritaje_count > 0 and b.peritaje_review_status <> 'reviewed'" in MIG
    assert "no_public_peritaje_available" in MIG


def test_lot_costs_are_explicit_readiness_gates():
    assert "lot_costs_missing" in MIG
    assert "lot_costs_incomplete" in MIG
    assert "lot_costs_not_reviewed" in MIG
    assert "enter_lot_costs" in MIG
    assert "complete_lot_costs" in MIG
    assert "review_lot_costs" in MIG
    assert "completed_cost_fields < 8" in MIG


def test_readiness_explains_all_primary_blockers():
    for blocker in (
        "closed_or_past",
        "fasecolda_not_high",
        "commission_missing",
        "peritaje_not_reviewed",
        "market_not_validated",
        "lot_costs_missing",
        "lot_costs_incomplete",
        "lot_costs_not_reviewed",
        "current_bid_missing",
    ):
        assert blocker in MIG
    assert "ready_for_decision" in MIG
    assert "decision_available" in MIG


def test_readiness_does_not_recompute_or_override_final_decision():
    assert "d.final_decision" in MIG
    assert "as final_decision" not in MIG[MIG.index("), blockers as"):]
    assert "max_bid_market_validated_cop" in MIG
    assert "expected_roi_current_pct" in MIG


def test_read_api_v031_remains_get_only_and_exposes_readiness():
    match = re.search(r'version:"(\d+)\.(\d+)"', API)
    assert match and tuple(map(int, match.groups())) >= (0, 31)
    assert 'req.method!=="get"' in API
    assert 'p==="/economic-readiness"' in API
    assert "/economic-readiness" in API
    assert "dashboard_economic_readiness_current" in API
    assert "next_action" in API
    assert "blockers" in API
