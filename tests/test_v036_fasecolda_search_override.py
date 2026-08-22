from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MIG = (ROOT / "supabase/migrations/20260822023000_fasecolda_search_term_override_v36.sql").read_text(encoding="utf-8").lower()


def test_override_is_private_auditable_and_reversible():
    assert "create table if not exists public.lot_fasecolda_search_term_overrides" in MIG
    assert "create table if not exists public.lot_fasecolda_search_term_override_history" in MIG
    assert "'confirm','clear','invalidate_identity_change'" in MIG
    assert "manual_fasecolda_search_term_not_match" in MIG
    assert "enable row level security" in MIG
    assert "revoke all on public.lot_fasecolda_search_term_overrides from public,anon,authenticated" in MIG


def test_matcher_only_changes_search_term_source():
    assert "pg_get_functiondef('public.fasecolda_match_lot(bigint,boolean)'::regprocedure)" in MIG
    assert "v_old constant text := 'v_term := public.fasecolda_search_term(v_lot.title);'" in MIG
    assert "v_new constant text := 'v_term := public.fasecolda_effective_search_term(p_lot_id,v_lot.title);'" in MIG
    assert "patch anchor not found" in MIG
    assert "patch anchor is not unique" in MIG


def test_confirm_requires_probe_with_codes_and_preserves_brand():
    fn = MIG[MIG.index("create or replace function public.dashboard_set_fasecolda_search_term_override"):]
    assert "dashboard_probe_fasecolda_search_term" in fn
    assert "search term probe returned no public fasecolda codes" in fn
    assert "search term must preserve vehicle brand" in fn
    assert "clear manual fasecolda candidate resolution before changing search term" in fn
    assert "v_match := public.fasecolda_match_lot(v_lot.id,true)" in fn


def test_override_never_forces_high_status():
    fn = MIG[MIG.index("create or replace function public.dashboard_set_fasecolda_search_term_override"):]
    assert "status='high'" not in fn
    assert "status := 'high'" not in fn
    assert "'match_origin','manual_search_term'" in fn
    assert "matcher_result" in fn


def test_identity_change_invalidates_override_and_derived_match():
    assert "invalidate_fasecolda_search_term_override_on_identity_change" in MIG
    assert "old.title is distinct from new.title" in MIG
    assert "old.brand is distinct from new.brand" in MIG
    assert "old.line is distinct from new.line" in MIG
    assert "old.model_year is distinct from new.model_year" in MIG
    assert "delete from public.lot_fasecolda_search_term_overrides" in MIG
    assert "delete from public.lot_fasecolda_candidates" in MIG
    assert "delete from public.lot_fasecolda_matches" in MIG


def test_effective_provenance_distinguishes_manual_search_term():
    assert "then 'manual_search_term'" in MIG
    assert "as search_term_origin" in MIG
    assert "search_term_override" in MIG
    assert "search_term_overridden_at" in MIG
    assert "matcher status and scoring remain unchanged" in MIG
