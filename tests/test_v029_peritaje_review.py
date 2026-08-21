from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
MIG = (ROOT / "supabase/migrations/20260821153848_peritaje_review_workflow_v29.sql").read_text(encoding="utf-8").lower()
API = (ROOT / "supabase/functions/superbid-read-api/index.ts").read_text(encoding="utf-8").lower()
DASH = (ROOT / "supabase/functions/superbid-dashboard/index.ts").read_text(encoding="utf-8").lower()


def test_peritaje_tables_are_private_and_auditable():
    assert "create table if not exists public.lot_peritaje_reviews" in MIG
    assert "create table if not exists public.lot_peritaje_review_history" in MIG
    assert "enable row level security" in MIG
    assert "revoke all on public.lot_peritaje_reviews from public,anon,authenticated" in MIG
    assert "revoke all on public.lot_peritaje_review_history from public,anon,authenticated" in MIG


def test_review_requires_public_peritaje_and_valid_source_url():
    fn = MIG[MIG.index("create or replace function public.dashboard_save_peritaje_review"):]
    assert "kind='peritaje'" in fn
    assert "peritaje source url does not belong to lot" in fn
    assert "public peritaje not available for lot" in fn


def test_manual_risk_dimensions_and_repair_scenarios_are_structured():
    for field in (
        "mechanical_risk", "transmission_risk", "body_risk", "safety_risk",
        "electrical_risk", "tires_risk", "documentation_risk", "missing_parts_risk",
        "repair_low_cop", "repair_base_cop", "repair_high_cop",
    ):
        assert field in MIG
    assert "low <= base <= high" in MIG
    assert "all risk dimensions are required" in MIG
    assert "all repair estimates are required" in MIG


def test_peritaje_guardrail_is_explicit_and_not_automated_diagnosis():
    guard = "manual_peritaje_review_not_automated_diagnosis"
    assert guard in MIG
    assert "interpretation" in API and "dashboard_peritaje_review_current" in API
    assert guard in DASH


def test_peritaje_queue_has_three_review_states():
    assert "dashboard_peritaje_review_current" in MIG
    assert "'unreviewed'" in MIG
    assert "'draft'" in MIG
    assert "'reviewed'" in MIG
    assert 'p==="/peritaje-reviews"' in API
    assert "peritaje_review_status=eq." in API


def test_dashboard_exposes_peritaje_queue_and_form():
    assert "/superbid-dashboard/peritajes" in DASH
    assert "revisión de peritajes" in DASH
    assert "revisión estructurada del peritaje" in DASH
    assert 'riskselect("mechanical_risk"' in DASH
    assert 'input("repair_base_cop"' in DASH
    assert "guardar y marcar revisado" in DASH


def test_peritaje_handler_does_not_write_economic_costs_or_decision():
    start = DASH.index("async function saveperitajereview")
    end = DASH.index("async function savecosts", start)
    fn = DASH[start:end]
    assert "dashboard_save_peritaje_review" in fn
    assert "dashboard_save_lot_costs" not in fn
    assert "max_bid_market_validated_cop" not in fn
    assert "final_decision" not in fn


def test_read_api_v029_capability_remains_get_only():
    match = re.search(r'version:"(\d+)\.(\d+)"', API)
    assert match and tuple(map(int, match.groups())) >= (0, 29)
    assert 'req.method!=="get"' in API
    assert 'p==="/peritaje-reviews"' in API
    assert "/peritaje-review" in API


def test_dashboard_remains_server_rendered():
    assert "<script" not in DASH
    assert "deno.serve" in DASH
