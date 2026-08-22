from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MIG = (ROOT / "supabase/migrations/20260822044324_fasecolda_workbench_lifecycle_triage_v43.sql").read_text(encoding="utf-8").lower()
UI = (ROOT / "supabase/functions/superbid-fasecolda-workbench/index.ts").read_text(encoding="utf-8").lower()


def test_v043_uses_year_evidence_lifecycle_without_creating_valuation():
    assert "dashboard_fasecolda_year_reference_evidence_lifecycle" in MIG
    assert "year_evidence_review_status" in MIG
    assert "year_lifecycle_next_action" in MIG
    assert "fasecolda_valuation_triage_not_match" in MIG
    assert "insert into public.lot_fasecolda_matches" not in MIG
    assert "update public.lot_fasecolda_matches" not in MIG


def test_changed_or_new_year_evidence_is_prioritized():
    assert "evidence_review_status='review_required'" in MIG
    assert "then 'year_evidence_review'" in MIG
    assert "then 25" in MIG
    assert "nueva, cambió o reapareció" in MIG


def test_current_confirmed_gap_is_deprioritized_but_stays_blocked():
    assert "disposition_action='confirm_coverage_gap'" in MIG
    assert "evidence_review_status='disposition_current'" in MIG
    assert "then 'known_year_coverage_gap'" in MIG
    assert "then 85" in MIG
    assert "sigue bloqueado económicamente" in MIG
    assert "superbid-fasecolda-evidence-dashboard" in MIG


def test_v043_keeps_private_backend_access():
    assert "revoke all on public.dashboard_fasecolda_valuation_workbench from public,anon,authenticated" in MIG
    assert "grant select on public.dashboard_fasecolda_valuation_workbench to service_role" in MIG


def test_workbench_exposes_lifecycle_and_routes_known_gaps():
    assert "superbid · v0.43" in UI
    assert "year_evidence_review_status" in UI
    assert "year_evidence_event_type" in UI
    assert "year_lifecycle_next_action" in UI
    assert "known_year_coverage_gap" in UI
    assert "superbid-fasecolda-evidence-dashboard" in UI
    assert "lifecycle evidencia" in UI


def test_workbench_remains_server_rendered_and_read_only_after_login():
    assert "<script" not in UI
    assert "dashboard_token_valid" in UI
    assert "httponly; secure; samesite=strict" in UI
    assert "dashboard_set_fasecolda" not in UI
    assert "dashboard_save" not in UI
    assert "dashboard_probe_fasecolda_search_term" not in UI
    assert "req.method!==\"get\"" in UI


def test_v043_guardrails_are_visible():
    assert "fasecolda_valuation_triage_not_match" in UI
    assert "fasecolda_year_evidence_change_not_valuation" in UI
    assert "nunca se convierte en homologación o valoración" in UI
