from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DASHBOARD = ROOT / "supabase/functions/superbid-readiness-dashboard/index.ts"
DOC = ROOT / "docs/V046_UNIFIED_DUE_DILIGENCE_ROUTING.md"
VERSION = ROOT / "src/superbid_collector/__init__.py"
PYPROJECT = ROOT / "pyproject.toml"
V44 = ROOT / "supabase/migrations/20260825030000_auditable_manual_market_evidence_v44.sql"
V45 = ROOT / "supabase/migrations/20260825040000_cost_assumption_governance_v45.sql"
V451 = ROOT / "supabase/migrations/20260825150000_cost_profile_fk_index_v451.sql"


def dashboard() -> str:
    return DASHBOARD.read_text(encoding="utf-8")


def _version_tuple(text: str, pattern: str) -> tuple[int, int, int]:
    match = re.search(pattern, text)
    assert match, f"version not found with {pattern}"
    return tuple(int(part) for part in match.group(1).split("."))


def test_v046_release_lineage_is_exposed_consistently_in_forward_versions():
    package_version = _version_tuple(
        VERSION.read_text(encoding="utf-8"), r'__version__\s*=\s*"(\d+\.\d+\.\d+)"'
    )
    project_version = _version_tuple(
        PYPROJECT.read_text(encoding="utf-8"), r'version\s*=\s*"(\d+\.\d+\.\d+)"'
    )
    assert package_version == project_version
    assert package_version >= (0, 46, 0)
    assert "Due Diligence Command Center" in dashboard()


def test_command_center_uses_canonical_due_diligence_queue_and_priority_order():
    ts = dashboard()
    assert "/rest/v1/dashboard_due_diligence_queue" in ts
    assert "due_diligence_rank" in ts
    assert "due_diligence_stage" in ts
    assert "pressure_level" in ts
    assert "closing_bucket" in ts
    assert "order=due_diligence_rank.asc,blocker_count.asc,review_score.desc,closes_at.asc" in ts
    assert "/rest/v1/dashboard_economic_readiness_current?select=" not in ts


def test_validate_market_routes_to_exact_v044_lot_workflow():
    ts = dashboard()
    assert 'a==="VALIDATE_MARKET"' in ts
    assert "superbid-market-review-dashboard/lots/${id}" in ts
    assert "MARKET_NOT_VALIDATED" in ts


def test_cost_actions_route_to_exact_v045_lot_governance_workflow():
    ts = dashboard()
    for action in ("ENTER_LOT_COSTS", "COMPLETE_LOT_COSTS", "REVIEW_LOT_COSTS"):
        assert action in ts
    assert "superbid-cost-governance-dashboard/lots/${id}" in ts
    for blocker in ("LOT_COSTS_MISSING", "LOT_COSTS_INCOMPLETE", "LOT_COSTS_NOT_REVIEWED"):
        assert blocker in ts


def test_fasecolda_peritaje_commission_and_bid_keep_specialized_or_canonical_routes():
    ts = dashboard()
    assert 'a==="REVIEW_VALUATION"' in ts
    assert "superbid-fasecolda-workbench" in ts
    assert 'a==="REVIEW_PERITAJE"' in ts
    assert "superbid-dashboard/lots/${id}#peritaje" in ts
    assert 'a==="REVIEW_COMMISSION"' in ts
    assert 'a==="WAIT_CURRENT_BID"' in ts
    assert "COMMISSION_MISSING" in ts
    assert "CURRENT_BID_MISSING" in ts


def test_fast_lane_preserves_market_plus_cost_core_and_may_add_only_condition_gate():
    ts = dashboard()
    required = (
        "MARKET_NOT_VALIDATED",
        "LOT_COSTS_MISSING",
        "LOT_COSTS_INCOMPLETE",
        "LOT_COSTS_NOT_REVIEWED",
    )
    assert "function isFastLane" in ts
    assert "required.every(b=>bs.includes(b))" in ts
    assert "bs.length>=4&&bs.length<=5" in ts
    assert 'allowed=new Set([...required,"CONDITION_RISK_UNREVIEWED","CONDITION_REPAIR_RESERVE_MISSING"])' in ts
    for blocker in required:
        assert blocker in ts
    assert "CONDITION_RISK_DECLINED" not in ts.split("function isFastLane", 1)[1].split("function primaryWorkflow", 1)[0]
    assert "FAST LANE" in ts
    assert "DUE_DILIGENCE_ROUTING_NOT_BUY_SIGNAL" in ts
    doc = DOC.read_text(encoding="utf-8")
    assert "Menor fricción documental" in doc
    assert "Interpretaciones prohibidas" in doc


def test_dashboard_is_read_only_for_business_state():
    ts = dashboard()
    forbidden = (
        "dashboard_save_manual_market_evidence",
        "dashboard_save_cost_assumption_profile",
        "dashboard_apply_cost_profile_to_lot",
        "dashboard_save_lot_costs",
        "lot_cost_overrides",
        "market_manual_evidence_sets",
        "lot_fasecolda_matches",
        "final_decision=",
        "max_bid_market_validated_cop=",
    )
    for token in forbidden:
        assert token not in ts
    assert "DUE_DILIGENCE_ROUTING_NOT_BUY_SIGNAL" in ts
    assert "ECONOMIC_READINESS_NOT_BUY_SIGNAL" in ts


def test_private_authentication_contract_is_preserved():
    ts = dashboard()
    assert "dashboard_token_valid" in ts
    assert 'Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")' in ts
    assert "HttpOnly; Secure; SameSite=Strict" in ts
    assert "sb_readiness_session" in ts
    assert 'if(!await valid(cookie(req)))return login(false' in ts


def test_navigation_exposes_all_current_operator_workflows():
    ts = dashboard()
    for route in (
        "/functions/v1/superbid-dashboard",
        "/functions/v1/superbid-readiness-dashboard",
        "/functions/v1/superbid-fasecolda-workbench",
        "/functions/v1/superbid-market-review-dashboard",
        "/functions/v1/superbid-cost-governance-dashboard",
        "/functions/v1/superbid-dashboard/peritajes",
        "/functions/v1/superbid-dashboard/alerts",
    ):
        assert route in ts


def test_filters_expose_operational_stage_pressure_and_next_action_without_recomputing_them():
    ts = dashboard()
    assert 'name="stage"' in ts
    assert 'name="pressure"' in ts
    assert 'name="next_action"' in ts
    for stage in ("UNBLOCK_NOW", "UNBLOCK_SOON", "UNBLOCK_TODAY", "PRIORITY_REVIEW", "PREPARE_REVIEW", "BACKLOG"):
        assert stage in ts
    assert "&due_diligence_stage=eq." in ts
    assert "&pressure_level=eq." in ts


def test_v046_keeps_v044_v045_and_v0451_authority_boundaries_intact():
    v44 = V44.read_text(encoding="utf-8")
    v45 = V45.read_text(encoding="utf-8")
    v451 = V451.read_text(encoding="utf-8")
    assert "MANUAL_MARKET_EVIDENCE_NOT_AUTOMATIC_VALUATION" in v44
    assert "MARKET_REVIEW_NOT_BUY_SIGNAL" in v44
    assert "COST_PROFILE_ASSUMPTION_NOT_LOT_COST" in v45
    assert "COST_PROFILE_APPLICATION_REQUIRES_LOT_CONFIRMATION" in v45
    assert "COST_GOVERNANCE_NOT_BUY_SIGNAL" in v45
    assert "ix_lot_cost_profile_application_profile" in v451
    ts = dashboard()
    assert "superbid-market-review-dashboard" in ts
    assert "superbid-cost-governance-dashboard" in ts
