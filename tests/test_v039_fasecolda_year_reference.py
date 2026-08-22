from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MIG = (ROOT / "supabase/migrations/20260822035213_fasecolda_year_reference_diagnostics_v39.sql").read_text(encoding="utf-8").lower()
YEAR_UI = (ROOT / "supabase/functions/superbid-fasecolda-year-dashboard/index.ts").read_text(encoding="utf-8").lower()
WORKBENCH = (ROOT / "supabase/functions/superbid-fasecolda-workbench/index.ts").read_text(encoding="utf-8").lower()


def test_year_reference_view_is_private_read_only_evidence():
    assert "create or replace view public.dashboard_fasecolda_year_reference_diagnostics" in MIG
    assert "revoke all on public.dashboard_fasecolda_year_reference_diagnostics from public, anon, authenticated" in MIG
    assert "grant select on public.dashboard_fasecolda_year_reference_diagnostics to service_role" in MIG
    assert "fasecolda_year_reference_diagnostic_not_valuation" in MIG


def test_year_reference_reasons_distinguish_identity_coverage_and_time_gap():
    for reason in (
        "stored_brand_differs_from_search_term",
        "line_not_present_in_imported_values",
        "same_year_reference_exists_diagnostic_stale",
        "year_gap_between_references",
        "only_older_references",
        "only_newer_references",
        "reference_years_unavailable",
    ):
        assert reason in MIG
    assert "review_brand_identity" in MIG
    assert "review_source_coverage" in MIG


def test_neighbor_years_are_direct_evidence_not_interpolated_valuation():
    assert "nearest_lower_year" in MIG
    assert "nearest_upper_year" in MIG
    assert "nearest_lower_min_value_cop" in MIG
    assert "nearest_upper_max_value_cop" in MIG
    assert "never interpolated, carried forward/back" in MIG
    assert "estimated_value_cop" not in MIG
    assert "interpolated_value_cop" not in MIG
    assert "derived_value_cop" not in MIG


def test_year_dashboard_contains_no_business_write_rpc():
    forbidden = (
        "dashboard_set_fasecolda_manual_resolution",
        "dashboard_set_fasecolda_search_term_override",
        "dashboard_probe_fasecolda_search_term",
        "dashboard_save_lot_costs",
        "dashboard_save_peritaje_review",
    )
    for name in forbidden:
        assert name not in YEAR_UI
    assert "dashboard_fasecolda_year_reference_diagnostics" in YEAR_UI
    assert "fasecolda_year_reference_diagnostic_not_valuation" in YEAR_UI


def test_year_dashboard_explicitly_rejects_cross_year_valuation_semantics():
    assert "no se interpolan" in YEAR_UI
    assert "no se trasladan al año del lote" in YEAR_UI
    assert "no crean homologación" in YEAR_UI
    assert "no modifican puja máxima ni decisión" in YEAR_UI
    assert "referencia inferior" in YEAR_UI
    assert "referencia superior" in YEAR_UI


def test_workbench_routes_year_cases_to_specialized_dashboard():
    assert 'x.workflow_target==="year_reference_review"' in WORKBENCH
    assert "/functions/v1/superbid-fasecolda-year-dashboard" in WORKBENCH
    assert "referencias por año" in WORKBENCH
    assert "v0.39" in WORKBENCH


def test_v039_dashboards_remain_private_server_rendered():
    for ui in (YEAR_UI, WORKBENCH):
        assert "dashboard_token_valid" in ui
        assert "httponly; secure; samesite=strict" in ui
        assert "<script" not in ui
        assert "deno.serve" in ui
