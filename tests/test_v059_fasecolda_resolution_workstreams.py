from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MIGRATION = (ROOT / "supabase/migrations/20260827030000_fasecolda_resolution_workstreams_v59.sql").read_text(encoding="utf-8")
WORKBENCH = (ROOT / "supabase/functions/superbid-fasecolda-workbench/index.ts").read_text(encoding="utf-8")


def rpc_names(source: str) -> set[str]:
    return set(re.findall(r"/rest/v1/rpc/([a-z0-9_]+)", source.lower()))


def version_tuple(text: str, pattern: str) -> tuple[int, int, int]:
    match = re.search(pattern, text)
    assert match
    return tuple(int(part) for part in match.group(1).split("."))


def test_v059_creates_private_read_only_resolution_workstreams_view():
    lower = MIGRATION.lower()
    assert "create or replace view public.dashboard_fasecolda_resolution_workstreams_v59" in lower
    assert "revoke all on public.dashboard_fasecolda_resolution_workstreams_v59 from public, anon, authenticated" in lower
    assert "grant select on public.dashboard_fasecolda_resolution_workstreams_v59 to service_role" in lower
    for forbidden in (
        "insert into public.",
        "update public.",
        "delete from public.",
        "max_bid",
        "final_decision",
        "recommended_bid",
    ):
        assert forbidden not in lower
    assert "fasecolda_resolution_workstream_routing_not_match_valuation_or_buy_signal" in lower


def test_v059_candidate_source_routing_uses_fast_structural_path_not_economics():
    lower = MIGRATION.lower()
    assert "dashboard_fasecolda_candidate_source_triage_fast_v571" in lower
    assert "left join lateral" in lower
    assert "from public.lot_attachments a" in lower
    assert "fasecolda_source_metadata_role_v57" in lower
    assert "fasecolda_source_metadata_rank_v57" in lower
    for forbidden in (
        "dashboard_economic_readiness_current",
        "dashboard_due_diligence_readiness_current",
        "dashboard_lot_current",
        "dashboard_fasecolda_valuation_workbench",
    ):
        assert forbidden not in lower


def test_v059_search_year_routing_uses_physical_latest_snapshot_path():
    lower = MIGRATION.lower()
    assert "from public.auction_lots l" in lower
    assert "lot_fasecolda_effective_current" in lower
    assert "from public.auction_snapshots s" in lower
    assert "order by s.observed_at desc" in lower
    assert "limit 1" in lower
    assert "fasecolda_suggest_search_term(l.title)" in lower
    assert "search_term_can_be_expanded" in lower
    assert "no_year_compatible_reference" in lower
    # Search-term expansion intentionally wins before year review, matching the canonical diagnostic priority.
    assert lower.index("search_term_can_be_expanded") < lower.index("no_year_compatible_reference")


def test_v059_six_workstreams_are_explicit_and_dead_end_is_not_document_review():
    lower = MIGRATION.lower()
    for workstream in (
        "candidate_evidence",
        "source_registered_review",
        "catalog_indistinguishable",
        "source_acquisition",
        "search_review",
        "year_review",
    ):
        assert workstream in lower
    assert "when f.duplicate_description_group_count > 0 then 'catalog_indistinguishable'" in lower
    assert "revisar catálogo/matcher antes de tratar un documento como discriminador" in lower
    assert "when 'candidate_evidence' then 10" in lower
    assert "when 'source_registered_review' then 20" in lower
    assert "when 'search_review' then 30" in lower
    assert "when 'year_review' then 40" in lower
    assert "when 'source_acquisition' then 60" in lower
    assert "when 'catalog_indistinguishable' then 90" in lower


def test_v059_preserves_source_lifecycle_as_context_not_authority():
    lower = MIGRATION.lower()
    assert "f.operational_route as source_operational_route" in lower
    assert "f.current_disposition_action as source_disposition_action" in lower
    assert "f.disposition_status as source_disposition_status" in lower
    assert "when f.operational_route = 'evidence_review' then 'candidate_evidence'" in lower


def test_v059_workbench_reads_only_fast_workstream_board_and_auth_rpc():
    lower = WORKBENCH.lower()
    assert "/rest/v1/dashboard_fasecolda_resolution_workstreams_v59" in lower
    assert "/rest/v1/dashboard_fasecolda_valuation_workbench" not in lower
    assert rpc_names(WORKBENCH) == {"dashboard_token_valid"}
    for forbidden in (
        "dashboard_set_fasecolda",
        "dashboard_save_fasecolda",
        "dashboard_probe_fasecolda_search_term",
        "dashboard_save_lot_costs",
        "dashboard_save_peritaje_review",
    ):
        assert forbidden not in lower


def test_v059_workbench_routes_each_workstream_to_existing_human_authority():
    lower = WORKBENCH.lower()
    assert "superbid-fasecolda-candidate-cockpit/lots/${id}" in lower
    assert "superbid-fasecolda-source-dashboard/lots/${id}" in lower
    assert "superbid-fasecolda-search-dashboard?lot=${id}&reason=" in lower
    assert "superbid-fasecolda-year-dashboard?lot=${id}" in lower
    assert "revisar catálogo/matcher" in lower
    assert "completar evidencia" in lower
    assert "adquirir fuente" in lower


def test_v059_workbench_preserves_private_exact_lot_completion_safe_shell():
    lower = WORKBENCH.lower()
    assert "dashboard_token_valid" in lower
    assert "httponly; secure; samesite=strict" in lower
    assert "^\\d{5,12}$" in WORKBENCH
    assert "requestedlot" in lower
    assert "<script" not in lower
    assert "req.method!==\"get\"" in lower
    for forbidden in ("return_to", "redirect_uri", "redirect_url"):
        assert forbidden not in lower


def test_v059_guardrails_make_routing_non_economic_and_non_match():
    lower = WORKBENCH.lower()
    assert "fasecolda_resolution_workstream_routing_not_match_valuation_or_buy_signal" in lower
    assert "fasecolda_valuation_triage_not_match" in lower
    assert "fasecolda_year_evidence_change_not_valuation" in lower
    assert "nunca se convierte en homologación o valoración" in lower
    assert "no modifica puja máxima ni decisión de compra" in lower


def test_v059_package_version_is_consistent():
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    package = (ROOT / "src/superbid_collector/__init__.py").read_text(encoding="utf-8")
    pv = version_tuple(pyproject, r'version\s*=\s*"(\d+\.\d+\.\d+)"')
    iv = version_tuple(package, r'__version__\s*=\s*"(\d+\.\d+\.\d+)"')
    assert pv == iv == (0, 59, 0)
