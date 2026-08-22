from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MIG = (ROOT / "supabase/migrations/20260822042324_fasecolda_year_case_disposition_v40.sql").read_text(encoding="utf-8").lower()
DASH = (ROOT / "supabase/functions/superbid-fasecolda-year-dashboard/index.ts").read_text(encoding="utf-8").lower()


def test_case_disposition_is_private_auditable_and_not_valuation():
    assert "create table if not exists public.fasecolda_year_reference_case_dispositions" in MIG
    assert "create table if not exists public.fasecolda_year_reference_case_disposition_history" in MIG
    assert "enable row level security" in MIG
    assert "revoke all on public.fasecolda_year_reference_case_dispositions from public,anon,authenticated" in MIG
    assert "fasecolda_year_gap_disposition_not_valuation" in MIG


def test_case_key_fingerprints_evidence_and_groups_repeated_lots():
    assert "md5(concat_ws('|" in MIG
    assert "available_years" in MIG
    assert "nearest_lower_codes" in MIG
    assert "nearest_upper_codes" in MIG
    assert "count(*) as lot_count" in MIG
    assert "array_agg(external_lot_id order by external_lot_id)" in MIG


def test_disposition_actions_are_diagnostic_compatible():
    fn = MIG[MIG.index("create or replace function public.dashboard_set_fasecolda_year_reference_case_disposition"):]
    assert "coverage gap confirmation incompatible with diagnostic" in fn
    assert "identity review referral incompatible with diagnostic" in fn
    assert "matcher recheck incompatible with diagnostic" in fn
    assert "confirm_coverage_gap" in fn
    assert "request_source_refresh" in fn
    assert "refer_identity_review" in fn
    assert "request_matcher_recheck" in fn


def test_disposition_never_writes_match_or_valuation_fields():
    fn = MIG[MIG.index("create or replace function public.dashboard_set_fasecolda_year_reference_case_disposition"):]
    assert "lot_fasecolda_matches" not in fn
    assert "fasecolda_current_cop" not in fn
    assert "max_bid" not in fn
    assert "final_decision" not in fn
    assert "expected_roi" not in fn


def test_dashboard_groups_cases_and_requires_explicit_post_action():
    assert "dashboard_fasecolda_year_reference_case_queue" in DASH
    assert "/cases/${esc(x.case_key)}/disposition" in DASH
    assert 'value="confirm_coverage_gap"' in DASH
    assert 'value="request_source_refresh"' in DASH
    assert 'value="refer_identity_review"' in DASH
    assert 'value="request_matcher_recheck"' in DASH
    assert "fasecolda_year_gap_disposition_not_valuation" in DASH
    assert "casos idénticos se agrupan" in DASH


def test_dashboard_v040_remains_server_rendered_and_versioned():
    assert "<script" not in DASH
    assert "deno.serve" in DASH
    assert "superbid · v0.40" in DASH
    assert 'method="post"' in DASH
