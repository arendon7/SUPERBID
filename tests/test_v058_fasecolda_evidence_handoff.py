from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MIGRATION = (ROOT / "supabase/migrations/20260827013000_fasecolda_evidence_handoff_v58.sql").read_text(encoding="utf-8")
COCKPIT = (ROOT / "supabase/functions/superbid-fasecolda-candidate-cockpit/index.ts").read_text(encoding="utf-8")
SOURCE_DASH = (ROOT / "supabase/functions/superbid-fasecolda-source-dashboard/index.ts").read_text(encoding="utf-8")


def rpc_names(source: str) -> set[str]:
    return set(re.findall(r"/rest/v1/rpc/([a-z0-9_]+)", source.lower()))


def version_tuple(text: str, pattern: str) -> tuple[int, int, int]:
    match = re.search(pattern, text)
    assert match
    return tuple(int(part) for part in match.group(1).split("."))


def test_v058_fast_candidate_queue_reuses_certified_source_triage_not_readiness_graph():
    lower = MIGRATION.lower()
    assert "dashboard_fasecolda_candidate_source_triage_fast_v571" in lower
    assert "lot_fasecolda_candidate_resolution_evidence" in lower
    for forbidden in (
        "dashboard_economic_readiness_current",
        "dashboard_fasecolda_candidate_resolution_cockpit_v52",
        "dashboard_fasecolda_resolution_queue",
        "dashboard_fasecolda_valuation_workbench",
        "lot_opportunity_market_validated",
        "market_comparables",
        "lot_cost_overrides",
    ):
        assert forbidden not in lower


def test_v058_fast_candidate_queue_is_live_evidence_route_only():
    lower = MIGRATION.lower()
    assert "f.operational_route='evidence_review'" in lower
    assert "f.closes_at is null or f.closes_at>clock_timestamp()" in lower
    assert "'candidate_resolution'::text as workflow_target" in lower
    assert "'blocked'::text as readiness_status" in lower
    assert "'review_valuation'::text as readiness_next_action" in lower


def test_v058_queue_preserves_evidence_state_but_does_not_create_it():
    lower = MIGRATION.lower()
    for token in (
        "'unreviewed'",
        "'draft'",
        "'reviewed'",
        "e.evidence_complete_count",
        "e.discriminating_match_count",
        "e.updated_at",
    ):
        assert token in lower
    for forbidden in (
        "insert into public.lot_fasecolda_candidate_resolution_evidence",
        "update public.lot_fasecolda_candidate_resolution_evidence",
        "delete from public.lot_fasecolda_candidate_resolution_evidence",
        "insert into public.lot_fasecolda_manual_resolutions",
        "update public.lot_fasecolda_manual_resolutions",
    ):
        assert forbidden not in lower


def test_v058_queue_exposes_routing_provenance_without_promoting_it_to_evidence():
    lower = MIGRATION.lower()
    assert "human_source_disposition" in lower
    assert "title_discriminator" in lower
    assert "current_disposition_action='route_to_evidence_review'" in lower
    assert "candidate_evidence_fast_queue_routing_not_evidence_match_or_buy_signal" in lower


def test_v058_queue_remains_service_role_only():
    lower = MIGRATION.lower()
    view = "dashboard_fasecolda_candidate_resolution_queue_v58"
    assert f"revoke all on public.{view} from public,anon,authenticated" in lower
    assert f"grant select on public.{view} to service_role" in lower


def test_v058_candidate_board_uses_fast_queue_only_but_exact_lot_keeps_v052_authority():
    lower = COCKPIT.lower()
    assert "dashboard_fasecolda_candidate_resolution_queue_v58" in lower
    assert "dashboard_fasecolda_candidate_resolution_cockpit_v52?select=" not in lower
    for required in (
        "/rest/v1/auction_lots?select=",
        "/rest/v1/lot_fasecolda_matches?select=",
        "/rest/v1/lot_fasecolda_candidates?select=",
        "/rest/v1/lot_fasecolda_candidate_resolution_evidence?select=*",
        "dashboard_save_fasecolda_candidate_resolution",
    ):
        assert required in lower


def test_v058_source_handoff_carries_only_validated_registered_context():
    lower = SOURCE_DASH.lower()
    assert "name=\"source\"" in lower
    assert "allowedsourceforlot" in lower
    assert "allowed.has(requested)" in lower
    assert "route_to_evidence_review" in lower
    assert "superbid-fasecolda-candidate-cockpit/lots/${encodeuricomponent(lot)}" in lower
    assert "source=${encodeuricomponent(source)}" in lower


def test_v058_candidate_cockpit_validates_source_context_against_same_lot_sources():
    lower = COCKPIT.lower()
    assert "requestedsource=safehttpurl(u.searchparams.get(\"source\"))" in lower
    assert "requestedsource&&seen.has(requestedsource)" in lower
    assert "fuente en contexto" in lower
    assert "iframe class=\"viewer\"" in lower


def test_v058_source_context_never_prefills_candidate_or_dimension_evidence():
    lower = COCKPIT.lower()
    selected_expr = re.search(r"const requested=.*?const selectedcandidate", lower, re.S)
    assert selected_expr
    assert "source" not in selected_expr.group(0)
    assert re.search(r"sourceoptions\(sources,\s*src\)", lower)
    assert not re.search(r"sourceoptions\(sources,\s*selectedsource\)", lower)
    assert "statusoptions(st)" in lower
    status_source_helpers = re.search(r"function statusoptions.*?function sourceoptions", lower, re.S)
    assert status_source_helpers
    assert "selectedsource" not in status_source_helpers.group(0)
    assert "ningún candidato, match, valor observado ni fuente de dimensión se prellena" in lower


def test_v058_context_survives_candidate_navigation_and_draft_redirect_only_as_query_context():
    lower = COCKPIT.lower()
    assert "sourcecontextquery" in lower
    assert "name=\"source_context\"" in lower
    assert "safehttpurl(f.get(\"source_context\"))" in lower
    assert "candidate=${encodeuricomponent(string(c.code))}${sourcecontextquery}" in lower


def test_v058_edge_rpc_authority_is_unchanged():
    assert rpc_names(SOURCE_DASH) == {
        "dashboard_token_valid",
        "dashboard_set_fasecolda_candidate_source_disposition_v56",
    }
    assert rpc_names(COCKPIT) == {
        "dashboard_token_valid",
        "dashboard_save_fasecolda_candidate_resolution",
        "dashboard_clear_fasecolda_candidate_resolution_v52",
    }


def test_v058_still_forbids_automatic_document_inference_and_economic_authority():
    combined = (MIGRATION + "\n" + COCKPIT + "\n" + SOURCE_DASH).lower()
    for forbidden in (
        "pdfjs",
        "tesseract",
        "extracttext",
        "diagnosepdf",
        "vision(",
        "ocr(",
        "recommended_bid",
        "max_bid",
        "final_decision",
        "buy_signal=true",
    ):
        assert forbidden not in combined


def test_v058_package_version_is_consistent():
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    package = (ROOT / "src/superbid_collector/__init__.py").read_text(encoding="utf-8")
    pv = version_tuple(pyproject, r'version\s*=\s*"(\d+\.\d+\.\d+)"')
    iv = version_tuple(package, r'__version__\s*=\s*"(\d+\.\d+\.\d+)"')
    assert pv == iv == (0, 58, 0)
