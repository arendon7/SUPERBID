from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MIG = (ROOT / "supabase/migrations/20260822043345_fasecolda_year_evidence_lifecycle_v41.sql").read_text(encoding="utf-8").lower()


def test_lifecycle_state_and_events_are_private():
    assert "create table if not exists public.fasecolda_year_reference_evidence_state" in MIG
    assert "create table if not exists public.fasecolda_year_reference_evidence_events" in MIG
    assert "enable row level security" in MIG
    assert "revoke all on public.fasecolda_year_reference_evidence_state from public,anon,authenticated" in MIG
    assert "revoke all on public.fasecolda_year_reference_evidence_events from public,anon,authenticated" in MIG


def test_logical_key_is_stable_while_case_key_tracks_evidence():
    fn = MIG[MIG.index("create or replace function public.refresh_fasecolda_year_reference_evidence_v41"):]
    assert "upper(coalesce(current_rec.stored_brand,''))" in fn
    assert "upper(coalesce(current_rec.term_brand,''))" in fn
    assert "upper(coalesce(current_rec.line_term,''))" in fn
    assert "coalesce(current_rec.model_year::text,'')" in fn
    assert "state_rec.current_case_key is distinct from current_rec.case_key" in fn
    assert "previous_case_key=state_rec.current_case_key" in fn


def test_lifecycle_events_cover_meaningful_transitions():
    for event in ("'new'", "'unchanged'", "'changed'", "'resolved'", "'reopened'"):
        assert event in MIG
    assert "state_rec.source_import_marker is distinct from v_source_marker" in MIG
    assert "not exists(" in MIG
    assert "last_event_type='resolved'" in MIG


def test_refresh_is_not_a_valuation_or_match_writer():
    fn = MIG[MIG.index("create or replace function public.refresh_fasecolda_year_reference_evidence_v41"):MIG.index("revoke all on function public.refresh_fasecolda_year_reference_evidence_v41")]
    assert "lot_fasecolda_matches" not in fn
    assert "fasecolda_current_cop" not in fn
    assert "max_bid" not in fn
    assert "final_decision" not in fn
    assert "expected_roi" not in fn
    assert "fasecolda_year_evidence_change_not_valuation" in fn


def test_current_disposition_only_applies_to_current_fingerprint():
    view = MIG[MIG.index("create or replace view public.dashboard_fasecolda_year_reference_evidence_lifecycle"):]
    assert "case_q.disposition_action is not null" in view
    assert "no_review_until_evidence_changes" in view
    assert "review_changed_evidence" in view
    assert "review_required" in view
    assert "disposition_current" in view


def test_cron_runs_without_high_frequency_noise():
    assert "fasecolda-year-evidence-v41" in MIG
    assert "*/30 * * * *" in MIG
    assert "select public.refresh_fasecolda_year_reference_evidence_v41();" in MIG


def test_lifecycle_views_are_backend_only():
    assert "dashboard_fasecolda_year_reference_evidence_lifecycle" in MIG
    assert "dashboard_fasecolda_year_reference_evidence_events" in MIG
    assert "revoke all on public.dashboard_fasecolda_year_reference_evidence_lifecycle from public,anon,authenticated" in MIG
    assert "revoke all on public.dashboard_fasecolda_year_reference_evidence_events from public,anon,authenticated" in MIG
