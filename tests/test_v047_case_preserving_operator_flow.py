import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FUNCTIONS = ROOT / "supabase/functions"

READINESS = (FUNCTIONS / "superbid-readiness-dashboard/index.ts").read_text(encoding="utf-8")
WORKBENCH = (FUNCTIONS / "superbid-fasecolda-workbench/index.ts").read_text(encoding="utf-8")
LEGACY_RESOLVER = (FUNCTIONS / "superbid-fasecolda-dashboard/index.ts").read_text(encoding="utf-8")
COCKPIT = (FUNCTIONS / "superbid-fasecolda-candidate-cockpit/index.ts").read_text(encoding="utf-8")
SEARCH = (FUNCTIONS / "superbid-fasecolda-search-dashboard/index.ts").read_text(encoding="utf-8")
YEAR = (FUNCTIONS / "superbid-fasecolda-year-dashboard/index.ts").read_text(encoding="utf-8")
EVIDENCE = (FUNCTIONS / "superbid-fasecolda-evidence-dashboard/index.ts").read_text(encoding="utf-8")
PRIVATE = [READINESS, WORKBENCH, COCKPIT, SEARCH, YEAR, EVIDENCE]
ALL = [READINESS, WORKBENCH, LEGACY_RESOLVER, COCKPIT, SEARCH, YEAR, EVIDENCE]


def rpc_names(source: str) -> set[str]:
    return set(re.findall(r"/rest/v1/rpc/([a-z0-9_]+)", source.lower()))


def test_all_case_aware_surfaces_accept_only_numeric_lot_context():
    for source in ALL:
        assert r"^\d{5,12}$" in source
    for source in PRIVATE:
        assert 'searchparams.get("lot")' in source.lower()


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


def test_legacy_resolver_preserves_exact_lot_but_has_no_write_authority():
    assert 'searchparams.get("lot")' in LEGACY_RESOLVER.lower()
    assert (
        "superbid-fasecolda-candidate-cockpit/lots/" in LEGACY_RESOLVER
        or "superbid-fasecolda-source-dashboard/lots/" in LEGACY_RESOLVER
    )
    assert "legacy_fasecolda_resolver_redirect_no_business_write" in LEGACY_RESOLVER.lower()
    assert rpc_names(LEGACY_RESOLVER) == set()


def test_candidate_cockpit_is_exact_before_and_after_mutation():
    assert "external_lot_id=eq.${encodeURIComponent(lot)}" in COCKPIT
    assert "dashboard_save_fasecolda_candidate_resolution" in COCKPIT
    assert "dashboard_clear_fasecolda_candidate_resolution_v52" in COCKPIT
    assert "candidate=${encodeURIComponent(code)}" in COCKPIT
    assert "&saved=draft" in COCKPIT
    assert "sourceSuffix" in COCKPIT
    assert "superbid-readiness-dashboard?lot=${encodeURIComponent(lot)}" in COCKPIT
    assert 'name="confirm_resolution" value="YES"' in COCKPIT
    lower = COCKPIT.lower()
    selection = lower[lower.index("const requested="):lower.index("const selectedcandidate=")]
    assert "best_code" not in selection
    assert "best_score" not in selection
    assert "source" not in selection


def test_search_workflow_keeps_exact_lot_through_explore_probe_and_override():
    lower = SEARCH.lower()
    assert "external_lot_id=eq.${encodeuricomponent(lot)}" in lower
    assert "dashboard_probe_fasecolda_search_term" in lower
    assert "dashboard_set_fasecolda_search_term_override" in lower
    assert "/lots/${esc(x.external_lot_id)}/explore" in SEARCH
    assert "/lots/${esc(x.external_lot_id)}/probe" in SEARCH
    assert "/lots/${esc(lot)}/override" in SEARCH
    assert "superbid-fasecolda-workbench?lot=${encodeURIComponent(lot)}" in SEARCH
    assert "superbid-fasecolda-workbench?lot=${esc(lot)}" in SEARCH


def test_year_and_evidence_filter_grouped_cases_by_lot_membership():
    assert "external_lot_ids=cs.${encodeURIComponent(`{${lot}}`)}" in YEAR
    assert "external_lot_ids=cs.${encodeURIComponent(`{${lot}}`)}" in EVIDENCE
    assert 'name="return_lot"' in YEAR
    assert "safeReturnLot" in YEAR
    assert "superbid-fasecolda-year-dashboard?lot=${encodeURIComponent(returnLot)}&saved=1" in YEAR
    assert "superbid-fasecolda-year-dashboard?lot=${esc(reviewId)}" in EVIDENCE


def test_cross_function_login_preserves_only_validated_lot_not_arbitrary_url():
    case_login_sources = [READINESS, WORKBENCH, COCKPIT, SEARCH, YEAR, EVIDENCE]
    for source in case_login_sources:
        assert 'name="lot"' in source or "/login?lot=${encodeURIComponent(lot)}" in source
        assert "requestedLot" in source
    for source in ALL:
        lower = source.lower()
        assert "return_to" not in lower
        assert "redirect_uri" not in lower
        assert "redirect_url" not in lower


def test_business_write_authority_is_explicit_and_does_not_expand_elsewhere():
    assert rpc_names(READINESS) == {"dashboard_token_valid"}
    assert rpc_names(WORKBENCH) == {"dashboard_token_valid"}
    assert rpc_names(EVIDENCE) == {"dashboard_token_valid"}
    assert rpc_names(LEGACY_RESOLVER) == set()
    assert rpc_names(COCKPIT) == {
        "dashboard_token_valid",
        "dashboard_save_fasecolda_candidate_resolution",
        "dashboard_clear_fasecolda_candidate_resolution_v52",
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
    for source in PRIVATE:
        lower = source.lower()
        assert "dashboard_token_valid" in lower
        assert "httponly; secure; samesite=strict" in lower


def test_v047_package_version_contract_is_forward_compatible():
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    package = (ROOT / "src/superbid_collector/__init__.py").read_text(encoding="utf-8")
    project_match = re.search(r'version\s*=\s*"(\d+\.\d+\.\d+)"', pyproject)
    package_match = re.search(r'__version__\s*=\s*"(\d+\.\d+\.\d+)"', package)
    assert project_match and package_match
    project_version = tuple(int(part) for part in project_match.group(1).split("."))
    package_version = tuple(int(part) for part in package_match.group(1).split("."))
    assert project_version == package_version
    assert project_version >= (0, 47, 0)
