from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MIGRATION = (ROOT / "supabase/migrations/20260827005000_fasecolda_source_research_fast_path_v571.sql").read_text(encoding="utf-8")
SOURCE_DASH = (ROOT / "supabase/functions/superbid-fasecolda-source-dashboard/index.ts").read_text(encoding="utf-8")


def rpc_names(source: str) -> set[str]:
    return set(re.findall(r"/rest/v1/rpc/([a-z0-9_]+)", source.lower()))


def version_tuple(text: str, pattern: str) -> tuple[int, int, int]:
    match = re.search(pattern, text)
    assert match
    return tuple(int(part) for part in match.group(1).split("."))


def test_v0571_fast_triage_uses_minimal_physical_sources_only():
    lower = MIGRATION.lower()
    section = lower[lower.index("create or replace view public.dashboard_fasecolda_candidate_source_triage_fast_v571"):lower.index("create or replace view public.dashboard_fasecolda_source_research_queue_v571")]
    for required in (
        "public.auction_lots",
        "public.lot_fasecolda_matches",
        "public.lot_fasecolda_manual_resolutions",
        "public.auction_snapshots",
        "public.lot_fasecolda_candidates",
        "public.lot_attachments",
        "public.lot_fasecolda_candidate_source_dispositions",
    ):
        assert required in section
    for forbidden in (
        "dashboard_lot_current",
        "dashboard_fasecolda_resolution_queue",
        "dashboard_economic_readiness_current",
        "lot_opportunity_market_validated",
        "market_comparables",
        "lot_cost_overrides",
    ):
        assert forbidden not in section


def test_v0571_preserves_v056_candidate_and_attachment_fingerprints():
    lower = MIGRATION.lower()
    assert "candidate_fingerprint" in lower
    assert "attachment_fingerprint" in lower
    assert "evidence_fingerprint" in lower
    for token in (
        "automatic_best_code",
        "automatic_best_score",
        "automatic_second_score",
        "current_candidate_count",
        "candidate_fingerprint",
        "auction_url",
        "attachment_fingerprint",
        "source_triage_class",
        "title_unique_target_code",
        "structured_discriminators",
        "unique_title_discriminators",
    ):
        assert token in lower


def test_v0571_preserves_all_v056_source_triage_classes_and_routes():
    lower = MIGRATION.lower()
    for value in (
        "single_candidate_low_confidence",
        "title_discriminator_available",
        "title_proxy_conflict",
        "structured_difference_source_unresolved",
        "trim_or_external_source_required",
        "source_insufficient_acknowledged",
        "source_research_requested",
        "identity_review_requested",
        "matcher_recheck_requested",
        "evidence_review",
        "source_triage",
    ):
        assert value in lower


def test_v0571_actionability_is_live_close_gate_not_economic_readiness_join():
    lower = MIGRATION.lower()
    section = lower[lower.index("create or replace view public.dashboard_fasecolda_source_research_queue_v571"):]
    assert "cst.operational_route<>'evidence_review'" in section
    assert "cst.closes_at is null or cst.closes_at>clock_timestamp()" in section
    assert "true::boolean as source_research_actionable" in section
    assert "dashboard_economic_readiness_current" not in section
    assert "review_valuation" not in section


def test_v0571_reuses_v057_metadata_inventory_without_content_inference():
    lower = MIGRATION.lower()
    section = lower[lower.index("create or replace view public.dashboard_fasecolda_source_research_queue_v571"):]
    assert "dashboard_fasecolda_attachment_research_inventory_v57" in section
    for route in (
        "review_identity_primary_source",
        "review_identity_secondary_source",
        "review_peritaje_for_identity_facts",
        "review_other_registered_source",
        "acquire_external_identity_source",
    ):
        assert route in section
    assert "source_research_fast_path_metadata_only_not_evidence_match_or_valuation" in section


def test_v0571_views_remain_service_role_only():
    lower = MIGRATION.lower()
    for view in (
        "dashboard_fasecolda_candidate_source_triage_fast_v571",
        "dashboard_fasecolda_source_research_queue_v571",
    ):
        assert f"revoke all on public.{view} from public,anon,authenticated" in lower
        assert f"grant select on public.{view} to service_role" in lower


def test_v0571_migration_is_read_only_and_adds_no_rpc_authority():
    lower = MIGRATION.lower()
    assert "create or replace function public.dashboard_" not in lower
    for forbidden in (
        "insert into public.lot_fasecolda_candidate_resolution_evidence",
        "update public.lot_fasecolda_candidate_resolution_evidence",
        "insert into public.lot_fasecolda_manual_resolutions",
        "update public.lot_fasecolda_manual_resolutions",
        "insert into public.lot_fasecolda_matches",
        "update public.lot_fasecolda_matches",
        "max_bid",
        "recommended_bid",
        "final_decision",
        "buy_signal",
    ):
        assert forbidden not in lower


def test_v0571_board_uses_fast_queue_but_detail_stays_completion_safe_v057():
    lower = SOURCE_DASH.lower()
    assert lower.count("dashboard_fasecolda_source_research_queue_v571") >= 2
    detail_marker = "dashboard_fasecolda_source_research_priority_v57?select=*&external_lot_id=eq.${encodeuricomponent(lot)}"
    assert detail_marker in lower
    detail_start = lower.index(detail_marker)
    assert "dashboard_fasecolda_source_research_queue_v571" not in lower[detail_start:detail_start + 350]


def test_v0571_dashboard_keeps_exact_existing_rpc_authority():
    assert rpc_names(SOURCE_DASH) == {
        "dashboard_token_valid",
        "dashboard_set_fasecolda_candidate_source_disposition_v56",
    }
    lower = SOURCE_DASH.lower()
    for forbidden in (
        "dashboard_save_fasecolda_candidate_resolution",
        "dashboard_set_fasecolda_manual_resolution",
        "dashboard_clear_fasecolda_candidate_resolution",
        "p_dimensions",
        "p_mark_reviewed",
        "buy_signal=true",
        "max_bid",
        "final_decision",
    ):
        assert forbidden not in lower


def test_v0571_dashboard_still_forbids_ocr_and_automatic_document_inference():
    lower = SOURCE_DASH.lower()
    assert "sin ocr, extracción ni diagnóstico automático" in lower
    assert "metadata y su apertura no crean evidencia ni preseleccionan candidato" in lower
    for forbidden in ("pdfjs", "tesseract", "extracttext", "diagnosepdf", "vision(", "ocr("):
        assert forbidden not in lower


def test_v0571_package_version_is_consistent():
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    package = (ROOT / "src/superbid_collector/__init__.py").read_text(encoding="utf-8")
    pv = version_tuple(pyproject, r'version\s*=\s*"(\d+\.\d+\.\d+)"')
    iv = version_tuple(package, r'__version__\s*=\s*"(\d+\.\d+\.\d+)"')
    assert pv == iv
    assert pv >= (0, 57, 1)
