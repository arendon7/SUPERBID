from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MIGRATION = (ROOT / "supabase/migrations/20260826143000_fasecolda_source_research_priority_v57.sql").read_text(encoding="utf-8")
SOURCE_DASH = (ROOT / "supabase/functions/superbid-fasecolda-source-dashboard/index.ts").read_text(encoding="utf-8")
COCKPIT = (ROOT / "supabase/functions/superbid-fasecolda-candidate-cockpit/index.ts").read_text(encoding="utf-8")


def rpc_names(source: str) -> set[str]:
    return set(re.findall(r"/rest/v1/rpc/([a-z0-9_]+)", source.lower()))


def version_tuple(text: str, pattern: str) -> tuple[int, int, int]:
    match = re.search(pattern, text)
    assert match
    return tuple(int(part) for part in match.group(1).split("."))


def test_v057_metadata_role_taxonomy_and_rank_are_explicit_and_deterministic():
    lower = MIGRATION.lower()
    assert "create or replace function public.fasecolda_source_metadata_role_v57" in lower
    assert "create or replace function public.fasecolda_source_metadata_rank_v57" in lower
    assert "immutable" in lower
    for role in (
        "identity_primary",
        "identity_secondary",
        "condition_identity_potential",
        "administrative_generic",
        "other_registered",
    ):
        assert role in lower
    assert "when 'identity_primary' then 10" in lower
    assert "when 'identity_secondary' then 20" in lower
    assert "when 'condition_identity_potential' then 30" in lower
    assert "when 'other_registered' then 40" in lower
    assert "when 'administrative_generic' then 90" in lower


def test_v057_metadata_helpers_and_views_are_service_role_only():
    lower = MIGRATION.lower()
    for fn in (
        "fasecolda_source_metadata_role_v57(text,text)",
        "fasecolda_source_metadata_rank_v57(text,text)",
    ):
        assert f"revoke all on function public.{fn} from public,anon,authenticated" in lower
        assert f"grant execute on function public.{fn} to service_role" in lower
    for view in (
        "dashboard_fasecolda_attachment_research_inventory_v57",
        "dashboard_fasecolda_source_research_priority_v57",
    ):
        assert f"create or replace view public.{view}" in lower
        assert f"revoke all on public.{view} from public,anon,authenticated" in lower
        assert f"grant select on public.{view} to service_role" in lower


def test_v057_research_route_precedence_prefers_identity_before_condition_or_acquisition():
    lower = MIGRATION.lower()
    section = lower[lower.index("create or replace view public.dashboard_fasecolda_source_research_priority_v57"):]
    primary = section.index("review_identity_primary_source")
    secondary = section.index("review_identity_secondary_source")
    peritaje = section.index("review_peritaje_for_identity_facts")
    other = section.index("review_other_registered_source")
    acquire = section.index("acquire_external_identity_source")
    assert primary < secondary < peritaje < other < acquire
    for route in (
        "review_identity_primary_source",
        "review_identity_secondary_source",
        "review_peritaje_for_identity_facts",
        "review_other_registered_source",
        "acquire_external_identity_source",
    ):
        assert route in section


def test_v057_actionable_queue_is_readiness_aware_but_detail_view_remains_complete():
    lower = MIGRATION.lower()
    assert "left join public.dashboard_economic_readiness_current er using(lot_id)" in lower
    assert "(er.next_action='review_valuation' and cst.operational_route<>'evidence_review') as source_research_actionable" in lower
    source = SOURCE_DASH.lower()
    assert "dashboard_fasecolda_source_research_priority_v57" in source
    assert "source_research_actionable=eq.true" in source
    detail_marker = "dashboard_fasecolda_source_research_priority_v57?select=*&external_lot_id=eq.${encodeuricomponent(lot)}"
    assert detail_marker in source
    detail_start = source.index(detail_marker)
    detail_window = source[detail_start : detail_start + 300]
    assert "source_research_actionable=eq.true" not in detail_window


def test_v057_migration_is_metadata_only_and_has_no_business_write_surface():
    lower = MIGRATION.lower()
    assert "source_research_priority_metadata_only_not_evidence_match_or_valuation" in lower
    for forbidden in (
        "insert into public.lot_fasecolda_candidate_resolution_evidence",
        "update public.lot_fasecolda_candidate_resolution_evidence",
        "delete from public.lot_fasecolda_candidate_resolution_evidence",
        "insert into public.lot_fasecolda_manual_resolutions",
        "update public.lot_fasecolda_manual_resolutions",
        "insert into public.lot_fasecolda_matches",
        "update public.lot_fasecolda_matches",
        "update public.dashboard_economic_readiness_current",
        "insert into public.dashboard_economic_readiness_current",
        "max_bid",
        "recommended_bid",
        "final_decision",
        "buy_signal",
    ):
        assert forbidden not in lower
    assert "create or replace function public.dashboard_" not in lower


def test_v057_dashboard_preserves_exact_v056_rpc_authority_only():
    assert rpc_names(SOURCE_DASH) == {
        "dashboard_token_valid",
        "dashboard_set_fasecolda_candidate_source_disposition_v56",
    }
    assert "HttpOnly; Secure; SameSite=Strict" in SOURCE_DASH
    lower = SOURCE_DASH.lower()
    for forbidden in (
        "dashboard_save_fasecolda_candidate_resolution",
        "dashboard_set_fasecolda_manual_resolution",
        "dashboard_clear_fasecolda_candidate_resolution",
        "p_dimensions",
        "p_mark_reviewed",
        "recommended_candidate",
        "recommendedcandidate",
        "buy_signal=true",
        "max_bid",
        "final_decision",
    ):
        assert forbidden not in lower


def test_v057_dashboard_metadata_priority_is_navigation_not_evidence():
    lower = SOURCE_DASH.lower()
    assert "source_research_priority_metadata_only_not_evidence_match_or_valuation" in lower
    assert "primera por metadata" in lower
    assert "la selección inicial es navegación, no conclusión" in lower
    assert "source_context_handoff_not_evidence_or_candidate_selection" in lower
    assert "la fuente seleccionada puede acompañar la navegación al cockpit" in lower
    assert "metadata y su apertura no crean evidencia ni preseleccionan candidato" in lower
    assert "target literal del título · solo proxy read-only" in lower
    assert "public_lot_context" in lower


def test_v057_dashboard_has_safe_registered_source_viewer_without_ocr_or_content_parsing():
    lower = SOURCE_DASH.lower()
    assert "safehttpurl" in lower
    assert "seen.has(requested)" in lower
    assert "<iframe" in lower
    assert "sin ocr, extracción ni diagnóstico automático" in lower
    assert "source_inventory" in lower
    for forbidden in (
        "pdfjs",
        "tesseract",
        "extracttext",
        "diagnosepdf",
        "vision(",
        "ocr(",
    ):
        assert forbidden not in lower


def test_v057_dashboard_renders_all_research_routes_and_metadata_roles():
    lower = SOURCE_DASH.lower()
    for route in (
        "review_identity_primary_source",
        "review_identity_secondary_source",
        "review_peritaje_for_identity_facts",
        "review_other_registered_source",
        "acquire_external_identity_source",
    ):
        assert route in lower
    for role in (
        "identity_primary",
        "identity_secondary",
        "condition_identity_potential",
        "administrative_generic",
        "other_registered",
    ):
        assert role in lower


def test_v057_does_not_modify_v052_candidate_cockpit_authority():
    assert rpc_names(COCKPIT) == {
        "dashboard_token_valid",
        "dashboard_save_fasecolda_candidate_resolution",
        "dashboard_clear_fasecolda_candidate_resolution_v52",
    }
    assert "source_research_priority_v57" not in "\n".join(
        line for line in COCKPIT.lower().splitlines() if "/rest/v1/rpc/" in line
    )


def test_v057_package_version_is_consistent_and_not_below_baseline():
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    package = (ROOT / "src/superbid_collector/__init__.py").read_text(encoding="utf-8")
    pv = version_tuple(pyproject, r'version\s*=\s*"(\d+\.\d+\.\d+)"')
    iv = version_tuple(package, r'__version__\s*=\s*"(\d+\.\d+\.\d+)"')
    assert pv == iv
    assert pv >= (0, 57, 0)
