import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FUNCTIONS = ROOT / "supabase/functions"

READINESS = (FUNCTIONS / "superbid-readiness-dashboard/index.ts").read_text(encoding="utf-8")
WORKBENCH = (FUNCTIONS / "superbid-fasecolda-workbench/index.ts").read_text(encoding="utf-8")
RESOLVER = (FUNCTIONS / "superbid-fasecolda-dashboard/index.ts").read_text(encoding="utf-8")
SEARCH = (FUNCTIONS / "superbid-fasecolda-search-dashboard/index.ts").read_text(encoding="utf-8")
YEAR = (FUNCTIONS / "superbid-fasecolda-year-dashboard/index.ts").read_text(encoding="utf-8")
EVIDENCE = (FUNCTIONS / "superbid-fasecolda-evidence-dashboard/index.ts").read_text(encoding="utf-8")
ALL = [READINESS, WORKBENCH, RESOLVER, SEARCH, YEAR, EVIDENCE]


def rpc_names(source: str) -> set[str]:
    return set(re.findall(r"/rest/v1/rpc/([a-z0-9_]+)", source.lower()))


def test_all_case_aware_surfaces_accept_only_numeric_lot_context():
    for source in ALL:
        assert 'searchparams.get("lot")' in source.lower()
        assert r"^\d{5,12}$" in source


def test_readiness_routes_valuation_and_shortcut_to_exact_workbench_lot():
    assert "dashboard_due_diligence_queue" in READINESS
    assert "superbid-fasecolda-workbench?lot=${id}" in READINESS
    assert "external_lot_id=eq.${encodeURIComponent(lot)}" in READINESS
    assert "CASE_CONTEXT_ROUTING_NOT_BUY_SIGNAL" in READINESS


def test_workbench_keeps_exact_lot_for_every_child_workflow():
    assert "external_lot_id=eq.${encodeURIComponent(lot)}" in WORKBENCH
    assert "superbid-fasecolda-dashboard?lot=${id}" in WORKBENCH
    assert "superbid-fasecolda-search-dashboard?lot=${id}" in WORKBENCH
    assert "superbid-fasecolda-year-dashboard?lot=${id}" in WORKBENCH
    assert "superbid-fasecolda-evidence-dashboard?lot=${id}" in WORKBENCH
    assert "superbid-readiness-dashboard?lot=${id}" in WORKBENCH


def test_resolver_is_exact_before_and_after_manual_mutation():
    assert "external_lot_id=eq.${encodeURIComponent(lot)}" in RESOLVER
    assert "dashboard_set_fasecolda_manual_resolution" in RESOLVER
    assert "?lot=${encodeURIComponent(id)}&manual_status=ALL&saved=1" in RESOLVER
    assert "?lot=${encodeURIComponent(id)}&manual_status=ALL&cleared=1" in RESOLVER
    assert 'type="radio" name="code" checked' not in RESOLVER
    assert 'name="confirm_resolution" value="YES"' in RESOLVER


def test_search_workflow_keeps_exact_lot_through_probe_and_override():
    assert "external_lot_id=eq.${encodeURIComponent(lot)}" in SEARCH
    assert "dashboard_probe_fasecolda_search_term" in SEARCH
    assert "dashboard_set_fasecolda_search_term_override" in SEARCH
    assert "superbid-fasecolda-search-dashboard?lot=${encodeURIComponent(id)}&reason=ALL&saved=1" in SEARCH
    assert "superbid-fasecolda-workbench?lot=${esc(id)}" in SEARCH


def test_year_and_evidence_filter_grouped_cases_by_lot_membership():
    assert "external_lot_ids=cs.${encodeURIComponent(`{${lot}}`)}" in YEAR
    assert "external_lot_ids=cs.${encodeURIComponent(`{${lot}}`)}" in EVIDENCE
    assert 'name="return_lot"' in YEAR
    assert "safeReturnLot" in YEAR
    assert "superbid-fasecolda-year-dashboard?lot=${encodeURIComponent(returnLot)}&saved=1" in YEAR
    assert "superbid-fasecolda-year-dashboard?lot=${esc(reviewId)}" in EVIDENCE


def test_cross_function_login_preserves_only_validated_lot_not_arbitrary_url():
    case_login_sources = [READINESS, WORKBENCH, SEARCH, YEAR, EVIDENCE]
    for source in case_login_sources:
        assert "/login?lot=${encodeURIComponent(lot)}" in source
        assert "requestedLot=exactLot(new URL(req.url))" in source
        assert "login(false,requestedLot)" in source
    assert 'name="lot" value=' in RESOLVER
    assert "lot=safeLot(f.get(\"lot\"))" in RESOLVER
    assert "login(false,requestedLot)" in RESOLVER
    for source in ALL:
        lower = source.lower()
        assert "return_to" not in lower
        assert "redirect_uri" not in lower
        assert "redirect_url" not in lower


def test_business_write_authority_did_not_expand():
    assert rpc_names(READINESS) == {"dashboard_token_valid"}
    assert rpc_names(WORKBENCH) == {"dashboard_token_valid"}
    assert rpc_names(EVIDENCE) == {"dashboard_token_valid"}
    assert rpc_names(RESOLVER) == {
        "dashboard_token_valid",
        "dashboard_set_fasecolda_manual_resolution",
    }
    assert rpc_names(SEARCH) == {
        "dashboard_token_valid",
        "dashboard_probe_fasecolda_search_term",
        "dashboard_set_fasecolda_search_term_override",
    }
    assert rpc_names(YEAR) == {
        "dashboard_token_valid",
        "dashboard_set_fasecolda_year_reference_case_disposition",
    }


def test_private_auth_cookie_contract_is_preserved():
    for source in ALL:
        lower = source.lower()
        assert "dashboard_token_valid" in lower
        assert "httponly; secure; samesite=strict" in lower


def test_v047_package_version():
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert 'version = "0.47.0"' in pyproject
