from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MIG = (ROOT / "supabase/migrations/20260822034245_fasecolda_valuation_workbench_v38.sql").read_text(encoding="utf-8").lower()
UI = (ROOT / "supabase/functions/superbid-fasecolda-workbench/index.ts").read_text(encoding="utf-8").lower()


def test_workbench_view_is_private_and_read_only_triage():
    assert "create or replace view public.dashboard_fasecolda_valuation_workbench" in MIG
    assert "revoke all on public.dashboard_fasecolda_valuation_workbench from public, anon, authenticated" in MIG
    assert "grant select on public.dashboard_fasecolda_valuation_workbench to service_role" in MIG
    assert "fasecolda_valuation_triage_not_match" in MIG


def test_workbench_routes_existing_valuation_workflows_without_matching():
    assert "candidate_resolution" in MIG
    assert "search_term_workflow" in MIG
    assert "year_reference_review" in MIG
    assert "superbid-fasecolda-dashboard" in MIG
    assert "superbid-fasecolda-search-dashboard" in MIG
    assert "where er.next_action = 'review_valuation'" in MIG


def test_triage_prioritizes_small_candidate_sets_but_not_as_buy_signal():
    assert "between 1 and 3 then 10" in MIG
    assert "pocos candidatos públicos: revisión humana acotada" in MIG
    assert "el matcher produjo candidatos pero no evidencia suficiente para high" in MIG
    assert "fasecolda_valuation_triage_not_match" in UI
    assert "no modifica puja máxima ni decisión de compra" in UI


def test_workbench_ui_contains_no_business_write_rpcs():
    forbidden = (
        "dashboard_set_fasecolda_manual_resolution",
        "dashboard_set_fasecolda_search_term_override",
        "dashboard_probe_fasecolda_search_term",
        "dashboard_save_lot_costs",
        "dashboard_save_peritaje_review",
    )
    for name in forbidden:
        assert name not in UI
    assert "dashboard_fasecolda_valuation_workbench" in UI


def test_workbench_links_to_existing_human_workflows():
    assert "/functions/v1/superbid-fasecolda-dashboard" in UI
    assert "/functions/v1/superbid-fasecolda-search-dashboard" in UI
    assert "/functions/v1/superbid-readiness-dashboard" in UI
    assert "abrir workflow" in UI


def test_workbench_is_private_server_rendered_without_client_js():
    assert "dashboard_token_valid" in UI
    assert "httponly; secure; samesite=strict" in UI
    assert "<script" not in UI
    assert "deno.serve" in UI
    assert "v0.38" in UI
