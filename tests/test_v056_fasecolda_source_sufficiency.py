from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MIGRATION = (ROOT / "supabase/migrations/20260826063000_fasecolda_candidate_source_sufficiency_v56.sql").read_text(encoding="utf-8")
SOURCE_DASH = (ROOT / "supabase/functions/superbid-fasecolda-source-dashboard/index.ts").read_text(encoding="utf-8")
WORKBENCH = (ROOT / "supabase/functions/superbid-fasecolda-workbench/index.ts").read_text(encoding="utf-8")
LEGACY = (ROOT / "supabase/functions/superbid-fasecolda-dashboard/index.ts").read_text(encoding="utf-8")
COCKPIT = (ROOT / "supabase/functions/superbid-fasecolda-candidate-cockpit/index.ts").read_text(encoding="utf-8")


def rpc_names(source: str) -> set[str]:
    return set(re.findall(r"/rest/v1/rpc/([a-z0-9_]+)", source.lower()))


def version_tuple(text: str, pattern: str) -> tuple[int, int, int]:
    match = re.search(pattern, text)
    assert match
    return tuple(int(part) for part in match.group(1).split("."))


def test_v056_source_disposition_tables_are_private_and_append_only_history():
    lower = MIGRATION.lower()
    for table in (
        "lot_fasecolda_candidate_source_dispositions",
        "lot_fasecolda_candidate_source_disposition_history",
    ):
        assert f"create table if not exists public.{table}" in lower
        assert f"alter table public.{table} enable row level security" in lower
        assert f"revoke all on public.{table} from public,anon,authenticated" in lower
    assert "grant select,insert,update,delete on public.lot_fasecolda_candidate_source_dispositions to service_role" in lower
    assert "grant select,insert on public.lot_fasecolda_candidate_source_disposition_history to service_role" in lower
    assert "grant select,insert,update,delete on public.lot_fasecolda_candidate_source_disposition_history" not in lower


def test_v056_disposition_actions_are_operational_not_match_states():
    for action in (
        "ROUTE_TO_EVIDENCE_REVIEW",
        "CONFIRM_CURRENT_SOURCES_INSUFFICIENT",
        "REQUEST_SOURCE_RESEARCH",
        "REFER_IDENTITY_REVIEW",
        "REQUEST_MATCHER_RECHECK",
    ):
        assert action in MIGRATION
    assert "CANDIDATE_SOURCE_DISPOSITION_NOT_EVIDENCE_MATCH_OR_VALUATION" in MIGRATION
    assert "CANDIDATE_SOURCE_TRIAGE_NOT_EVIDENCE_MATCH_OR_VALUATION" in MIGRATION
    rpc = MIGRATION[MIGRATION.index("create or replace function public.dashboard_set_fasecolda_candidate_source_disposition_v56"):]
    for forbidden in (
        "insert into public.lot_fasecolda_manual_resolutions",
        "update public.lot_fasecolda_manual_resolutions",
        "insert into public.lot_fasecolda_candidate_resolution_evidence",
        "update public.lot_fasecolda_candidate_resolution_evidence",
        "insert into public.lot_fasecolda_matches",
        "update public.lot_fasecolda_matches",
        "max_bid",
        "final_decision",
        "recommended_bid",
    ):
        assert forbidden not in rpc.lower()
    assert "'buy_signal',false" in rpc.lower()
    assert "'match_fields_modified',false" in rpc.lower()
    assert "'valuation_fields_modified',false" in rpc.lower()
    assert "'evidence_fields_modified',false" in rpc.lower()


def test_v056_fingerprint_covers_identity_match_candidates_and_allowed_sources():
    lower = MIGRATION.lower()
    assert "candidate_fingerprint" in lower
    assert "attachment_fingerprint" in lower
    assert "auction_url" in lower
    assert "automatic_best_code" in lower
    assert "automatic_best_score" in lower
    assert "automatic_second_score" in lower
    assert "search_term" in lower
    assert "external_lot_id" in lower
    assert "upper(coalesce(c.title,''))" in lower
    assert "coalesce(array_to_string(c.structured_discriminators,','),'')" in lower
    assert "when d.evidence_fingerprint=f.evidence_fingerprint then 'current'" in lower
    assert "else 'stale'" in lower


def test_v056_source_classes_preserve_uncertainty_and_single_candidate_gate():
    lower = MIGRATION.lower()
    for cls in (
        "single_candidate_low_confidence",
        "title_discriminator_available",
        "title_proxy_conflict",
        "structured_difference_source_unresolved",
        "trim_or_external_source_required",
    ):
        assert cls in lower
    single_pos = lower.index("when cs.current_candidate_count=1 then 'single_candidate_low_confidence'")
    title_pos = lower.index("when ts.unique_title_discriminator_count>0")
    assert single_pos < title_pos
    assert "single-candidate low-confidence case cannot satisfy the v0.52 discriminating-alternative contract" in lower
    assert "if v_action='route_to_evidence_review' and v_case.current_candidate_count<2" in lower


def test_v056_title_proxy_is_bounded_read_only_and_never_auto_confirms():
    lower = MIGRATION.lower()
    assert "abs(r.candidate_engine_cc-b.title_engine_cc)<=50" in lower
    assert "ms.engine_match_count=1" in lower
    assert "ms.transmission_match_count=1" in lower
    assert "ms.drivetrain_match_count=1" in lower
    assert "ms.fuel_match_count=1" in lower
    assert "distinct_title_target_codes" in lower
    assert "title_unique_target_code" in lower
    assert "title_discriminator_available" in lower
    assert "todavía requiere evidencia humana v0.52" in lower


def test_v056_duplicate_description_normalization_matches_v052_gate():
    lower = MIGRATION.lower()
    exact = "regexp_replace(upper(trim(coalesce(c.description,''))),'[[:space:]]+',' ','g')"
    assert exact in lower
    assert "replace(/[^a-z0-9]+/" not in lower


def test_v056_workbench_routes_candidate_work_by_source_sufficiency_without_readiness_write():
    lower = MIGRATION.lower()
    for workflow in (
        "candidate_resolution",
        "candidate_source_triage",
        "candidate_source_insufficient",
        "candidate_source_research",
        "candidate_identity_review",
        "candidate_matcher_recheck",
    ):
        assert workflow in lower
    assert "superbid-fasecolda-candidate-cockpit" in lower
    assert "superbid-fasecolda-source-dashboard" in lower
    assert "where er.next_action='review_valuation'" in lower
    routing = lower[lower.index("create or replace view public.dashboard_fasecolda_valuation_workbench"):]
    assert "update public.dashboard_economic_readiness_current" not in routing
    assert "insert into public.dashboard_economic_readiness_current" not in routing


def test_v056_source_dashboard_has_only_auth_and_disposition_rpc_authority():
    assert rpc_names(SOURCE_DASH) == {
        "dashboard_token_valid",
        "dashboard_set_fasecolda_candidate_source_disposition_v56",
    }
    assert "HttpOnly; Secure; SameSite=Strict" in SOURCE_DASH
    assert "CANDIDATE_SOURCE_TRIAGE_NOT_EVIDENCE_MATCH_OR_VALUATION" in SOURCE_DASH
    lower = SOURCE_DASH.lower()
    for forbidden in (
        "dashboard_save_fasecolda_candidate_resolution",
        "dashboard_set_fasecolda_manual_resolution",
        "dashboard_clear_fasecolda_candidate_resolution",
        "p_dimensions",
        "p_mark_reviewed",
        "winner",
        "recommendedcandidate",
        "recommended_candidate",
        "buy_signal=true",
        "max_bid",
        "final_decision",
    ):
        assert forbidden not in lower


def test_v056_source_dashboard_does_not_extract_or_diagnose_pdf_content():
    lower = SOURCE_DASH.lower()
    assert "sin ocr, extracción ni diagnóstico automático" in lower
    assert "<iframe" in lower
    assert "safehttpurl" in lower
    assert "seen.has(requested)" in lower
    assert "target literal del título · solo proxy read-only" in lower
    for forbidden in ("pdfjs", "ocr", "tesseract", "extracttext", "diagnosepdf", "vision"):
        if forbidden == "ocr":
            assert "ocr(" not in lower
        else:
            assert forbidden not in lower


def test_v056_workbench_and_legacy_shim_use_source_triage_route():
    lower = WORKBENCH.lower()
    for workflow in (
        "candidate_source_triage",
        "candidate_source_insufficient",
        "candidate_source_research",
        "candidate_identity_review",
        "candidate_matcher_recheck",
    ):
        assert workflow in lower
    assert "superbid-fasecolda-source-dashboard/lots/${id}" in lower
    assert "superbid-fasecolda-candidate-cockpit/lots/${id}" in lower
    legacy = LEGACY.lower()
    assert "superbid-fasecolda-source-dashboard/lots/" in legacy
    assert "superbid-fasecolda-candidate-cockpit/lots/" not in legacy
    assert "legacy_fasecolda_resolver_redirect_no_business_write" in legacy


def test_v056_does_not_expand_v052_candidate_cockpit_write_surface():
    assert rpc_names(COCKPIT) == {
        "dashboard_token_valid",
        "dashboard_save_fasecolda_candidate_resolution",
        "dashboard_clear_fasecolda_candidate_resolution_v52",
    }
    assert "candidate_source" not in "\n".join(
        line for line in COCKPIT.lower().splitlines() if "/rest/v1/rpc/" in line
    )


def test_v056_package_version_baseline_is_consistent_and_forward_compatible():
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    package = (ROOT / "src/superbid_collector/__init__.py").read_text(encoding="utf-8")
    pv = version_tuple(pyproject, r'version\s*=\s*"(\d+\.\d+\.\d+)"')
    iv = version_tuple(package, r'__version__\s*=\s*"(\d+\.\d+\.\d+)"')
    assert pv == iv
    assert pv >= (0, 56, 0)
