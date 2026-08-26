from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DASH = (ROOT / "supabase/functions/superbid-readiness-dashboard/index.ts").read_text(encoding="utf-8").lower()
V46 = (ROOT / "supabase/migrations/20260825200000_due_diligence_fasecolda_provenance_v46.sql").read_text(encoding="utf-8").lower()


def test_readiness_dashboard_preserves_v031_contract_through_canonical_due_diligence_view():
    # Later waves do not recompute economic readiness in the UI. The canonical
    # due-diligence view remains derived from the readiness contract.
    assert "dashboard_due_diligence_queue" in DASH
    assert "dashboard_economic_readiness_current r" in V46
    assert "blocker_count.asc" in DASH
    assert "review_score.desc" in DASH
    assert "closes_at.asc" in DASH


def test_ready_is_never_presented_as_buy_signal():
    assert "economic_readiness_not_buy_signal" in DASH
    assert "due_diligence_routing_not_buy_signal" in DASH
    assert "ready_for_decision" in DASH
    assert "nunca significa comprar" in DASH
    assert "final_decision=" not in DASH
    assert "max_bid_market_validated_cop=" not in DASH
    assert "expected_roi_current_pct=" not in DASH


def test_dashboard_exposes_blockers_and_next_action_filters():
    assert 'name="status"' in DASH
    assert 'name="next_action"' in DASH
    assert 'name="review_state"' in DASH
    for action in (
        "review_valuation", "review_commission", "review_peritaje",
        "validate_market", "enter_lot_costs", "complete_lot_costs",
        "review_lot_costs", "wait_current_bid", "decision_available",
    ):
        assert action in DASH


def test_next_actions_link_to_current_human_workflows():
    assert "/functions/v1/superbid-dashboard/lots/" in DASH
    assert "#peritaje" in DASH
    assert "/functions/v1/superbid-market-review-dashboard/lots/" in DASH
    assert "/functions/v1/superbid-cost-governance-dashboard/lots/" in DASH
    assert "/functions/v1/superbid-dashboard/peritajes" in DASH


def test_visual_board_is_read_only_for_business_data():
    assert "dashboard_save_lot_costs" not in DASH
    assert "dashboard_save_peritaje_review" not in DASH
    assert "dashboard_transfer_peritaje_repair_to_costs" not in DASH
    assert "final_decision=" not in DASH
    assert "max_bid_market_validated_cop=" not in DASH
    assert "expected_roi_current_pct=" not in DASH


def test_dashboard_uses_custom_private_auth_and_server_rendering():
    assert "dashboard_token_valid" in DASH
    assert "httponly; secure; samesite=strict" in DASH
    assert "<script" not in DASH
    assert "deno.serve" in DASH
