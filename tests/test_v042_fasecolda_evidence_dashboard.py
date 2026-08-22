from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UI = (ROOT / "supabase/functions/superbid-fasecolda-evidence-dashboard/index.ts").read_text(encoding="utf-8").lower()


def test_dashboard_reads_only_lifecycle_views():
    assert "dashboard_fasecolda_year_reference_evidence_lifecycle" in UI
    assert "dashboard_fasecolda_year_reference_evidence_events" in UI
    forbidden = (
        "dashboard_set_fasecolda_year_reference_case_disposition",
        "dashboard_set_fasecolda_manual_resolution",
        "dashboard_set_fasecolda_search_term_override",
        "dashboard_save_lot_costs",
        "dashboard_save_peritaje_review",
    )
    for name in forbidden:
        assert name not in UI


def test_dashboard_exposes_lifecycle_states_and_events():
    for value in ("review_required", "disposition_current", "open_review"):
        assert value in UI
    for event in ("new", "unchanged", "changed", "resolved", "reopened"):
        assert event in UI
    assert "/events" in UI
    assert "evidence_changed_at" in UI
    assert "source_import_marker" in UI


def test_dashboard_preserves_not_valuation_semantics():
    assert "fasecolda_year_evidence_change_not_valuation" in UI
    assert "no crean homologación" in UI
    assert "no interpolan años" in UI
    assert "puja máxima" in UI
    assert "roi" in UI
    assert "decisión final" in UI
    assert "resolved significa" in UI
    assert "no implica por sí solo match high" in UI


def test_dashboard_is_private_and_server_rendered():
    assert "dashboard_token_valid" in UI
    assert "httponly; secure; samesite=strict" in UI
    assert "sb_fasecolda_evidence_session" in UI
    assert "<script" not in UI
    assert "deno.serve" in UI
    assert 'req.method!=="get"' in UI


def test_dashboard_v042_routes_and_filters_are_explicit():
    assert "superbid · v0.42" in UI
    assert 'name="review"' in UI
    assert 'name="event"' in UI
    assert 'name="reason"' in UI
    assert "una disposición v0.40 solo aparece vigente si pertenece al fingerprint actual" in UI
    assert "/functions/v1/superbid-fasecolda-year-dashboard" in UI
