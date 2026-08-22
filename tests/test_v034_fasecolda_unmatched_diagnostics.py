from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MIG = (ROOT / "supabase/migrations/20260822021500_fasecolda_unmatched_diagnostics_v34.sql").read_text(encoding="utf-8").lower()


def test_v034_is_read_only_diagnostic_layer():
    assert "create or replace view public.dashboard_fasecolda_unmatched_diagnostics" in MIG
    assert "fasecolda_unmatched_diagnostic_not_match" in MIG
    assert "insert into public.lot_fasecolda_matches" not in MIG
    assert "update public.lot_fasecolda_matches" not in MIG
    assert "delete from public.lot_fasecolda_matches" not in MIG


def test_compound_search_term_suggestion_is_conservative():
    assert "fasecolda_suggest_search_term" in MIG
    assert "regexp_replace(coalesce(p_title,''),'\\[[^\\]]+\\]'" in MIG
    assert "max_model_words := 2" in MIG
    assert "w='new'" in MIG
    assert "max_model_words := 3" in MIG
    for stop in ("'cc'", "'mt'", "'at'", "'tp'", "'td'", "'4x2'", "'4x4'"):
        assert stop in MIG


def test_diagnostics_separate_parser_gap_from_source_gap():
    for reason in (
        "search_term_can_be_expanded",
        "no_year_compatible_reference",
        "public_search_returned_no_codes",
        "no_match_row",
        "unmatched_other",
    ):
        assert reason in MIG
    assert "suggestion_differs" in MIG
    assert "diagnostic_rank" in MIG


def test_diagnostics_only_cover_valuation_unmatched_cases():
    assert "r.next_action='review_valuation'" in MIG
    assert "coalesce(e.status,'no_match_row') in ('unmatched','no_match_row')" in MIG


def test_v034_objects_are_backend_only():
    assert "revoke all on function public.fasecolda_suggest_search_term(text) from public,anon,authenticated" in MIG
    assert "grant execute on function public.fasecolda_suggest_search_term(text) to service_role" in MIG
    assert "revoke all on public.dashboard_fasecolda_unmatched_diagnostics from public,anon,authenticated" in MIG
    assert "grant select on public.dashboard_fasecolda_unmatched_diagnostics to service_role" in MIG
