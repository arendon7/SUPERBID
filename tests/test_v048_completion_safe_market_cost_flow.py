import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FUNCTIONS = ROOT / "supabase/functions"

MARKET = (FUNCTIONS / "superbid-market-review-dashboard/index.ts").read_text(encoding="utf-8")
COST = (FUNCTIONS / "superbid-cost-governance-dashboard/index.ts").read_text(encoding="utf-8")


def rpc_names(source: str) -> set[str]:
    return set(re.findall(r"/rest/v1/rpc/([a-z0-9_]+)", source.lower()))


def test_market_and_cost_accept_only_numeric_lot_context():
    for source in (MARKET, COST):
        assert r"^\d{5,12}$" in source
        assert "function safeLot" in source
        assert "function lotFromPath" in source


def test_market_login_preserves_exact_lot_without_open_redirect():
    assert 'name="lot" value=' in MARKET
    assert 'lot=safeLot(f.get("lot"))' in MARKET
    assert "superbid-market-review-dashboard/lots/${encodeURIComponent(lot)}" in MARKET
    for token in ("return_to", "redirect_uri", "redirect_url"):
        assert token not in MARKET.lower()


def test_market_reviewed_completion_routes_to_canonical_readiness_but_draft_stays_in_workflow():
    save = MARKET.split("async function saveReview", 1)[1].split("Deno.serve", 1)[0]
    assert "dashboard_save_manual_market_evidence" in save
    assert "reviewed?`/functions/v1/superbid-readiness-dashboard?lot=${encodeURIComponent(external)}`" in save
    assert "superbid-market-review-dashboard/lots/${encodeURIComponent(external)}?saved=1" in save
    assert "COMPLETION_ROUTING_NOT_BUY_SIGNAL" in MARKET


def test_market_completed_case_never_falls_into_pending_queue_404():
    detail = MARKET.split("async function lot", 1)[1].split("function parseComparableLines", 1)[0]
    assert "ya no está en la cola de mercado pendiente" in detail
    assert "superbid-readiness-dashboard?lot=${esc(external)}" in detail
    assert 'return html("No encontrado"' not in detail


def test_market_write_authority_did_not_expand():
    assert rpc_names(MARKET) == {
        "dashboard_token_valid",
        "dashboard_save_manual_market_evidence",
    }
    assert "MANUAL_MARKET_EVIDENCE_NOT_AUTOMATIC_VALUATION" in MARKET
    assert "MARKET_REVIEW_NOT_BUY_SIGNAL" in MARKET
    assert '"buy_signal"' not in MARKET.lower()
    assert "lot_fasecolda_matches" not in MARKET
    assert "dashboard_save_lot_costs" not in MARKET


def test_cost_login_preserves_exact_lot_without_open_redirect():
    assert 'name="lot" value=' in COST
    assert 'lot=safeLot(f.get("lot"))' in COST
    assert "superbid-cost-governance-dashboard/lots/${encodeURIComponent(lot)}" in COST
    for token in ("return_to", "redirect_uri", "redirect_url"):
        assert token not in COST.lower()


def test_cost_reviewed_completion_routes_to_readiness_but_draft_stays_in_cost_workflow():
    apply = COST.split("async function applyProfile", 1)[1].split("Deno.serve", 1)[0]
    assert "dashboard_apply_cost_profile_to_lot" in apply
    assert "reviewed?`/functions/v1/superbid-readiness-dashboard?lot=${encodeURIComponent(external)}`" in apply
    assert "superbid-cost-governance-dashboard/lots/${encodeURIComponent(external)}?saved=1" in apply
    assert "COMPLETION_ROUTING_NOT_BUY_SIGNAL" in COST


def test_cost_profile_creation_can_return_to_case_but_never_applies_it_implicitly():
    assert 'name="return_lot"' in COST
    assert 'returnLot=safeLot(f.get("return_lot"))' in COST
    assert "superbid-cost-governance-dashboard/lots/${encodeURIComponent(returnLot)}" in COST
    save = COST.split("async function saveProfile", 1)[1].split("async function applyProfile", 1)[0]
    assert "dashboard_save_cost_assumption_profile" in save
    assert "dashboard_apply_cost_profile_to_lot" not in save


def test_cost_completed_case_never_falls_into_pending_queue_404():
    detail = COST.split("async function lot", 1)[1].split("async function saveProfile", 1)[0]
    assert "ya no está en la cola de costos pendiente" in detail
    assert "superbid-readiness-dashboard?lot=${esc(external)}" in detail
    assert 'return html("No encontrado"' not in detail


def test_cost_write_authority_did_not_expand_and_bulk_apply_remains_absent():
    assert rpc_names(COST) == {
        "dashboard_token_valid",
        "dashboard_save_cost_assumption_profile",
        "dashboard_apply_cost_profile_to_lot",
    }
    assert "COST_PROFILE_ASSUMPTION_NOT_LOT_COST" in COST
    assert "COST_PROFILE_APPLICATION_REQUIRES_LOT_CONFIRMATION" in COST
    assert "COST_GOVERNANCE_NOT_BUY_SIGNAL" in COST
    assert "Aplicación siempre individual" in COST
    assert "bulk" not in COST.lower()
    assert '"buy_signal"' not in COST.lower()


def test_private_auth_cookie_contract_is_preserved():
    for source in (MARKET, COST):
        lower = source.lower()
        assert "dashboard_token_valid" in lower
        assert "httponly; secure; samesite=strict" in lower
        assert 'deno.env.get("supabase_service_role_key")' in lower


def test_v048_package_version_is_consistent():
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    package = (ROOT / "src/superbid_collector/__init__.py").read_text(encoding="utf-8")
    assert 'version = "0.48.0"' in pyproject
    assert '__version__ = "0.48.0"' in package
