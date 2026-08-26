import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MIGRATION = ROOT / "supabase/migrations/20260826003500_condition_evidence_gate_v49.sql"
CONDITION = ROOT / "supabase/functions/superbid-condition-review-dashboard/index.ts"
READINESS = ROOT / "supabase/functions/superbid-readiness-dashboard/index.ts"
V46 = ROOT / "supabase/migrations/20260825200000_due_diligence_fasecolda_provenance_v46.sql"


def migration() -> str:
    return MIGRATION.read_text(encoding="utf-8")


def condition_ui() -> str:
    return CONDITION.read_text(encoding="utf-8")


def readiness_ui() -> str:
    return READINESS.read_text(encoding="utf-8")


def rpc_names(source: str) -> set[str]:
    return set(re.findall(r"/rest/v1/rpc/([a-z0-9_]+)", source.lower()))


def test_condition_disposition_is_backend_only_auditable_state():
    sql = migration()
    assert "create table if not exists public.lot_condition_dispositions" in sql
    assert "create table if not exists public.lot_condition_disposition_history" in sql
    assert "generated always as identity primary key" in sql
    assert "alter table public.lot_condition_dispositions enable row level security" in sql
    assert "alter table public.lot_condition_disposition_history enable row level security" in sql
    assert "revoke all on public.lot_condition_dispositions,public.lot_condition_disposition_history from public,anon,authenticated" in sql
    assert "grant select,insert,update on public.lot_condition_dispositions to service_role" in sql
    assert "grant select,insert on public.lot_condition_disposition_history to service_role" in sql
    assert "MANUAL_CONDITION_RISK_DISPOSITION_NOT_DIAGNOSIS_OR_BUY_SIGNAL" in sql


def test_no_public_peritaje_is_now_a_real_readiness_blocker():
    sql = migration()
    assert "when b.peritaje_count=0 and b.condition_disposition_status in ('UNREVIEWED','DRAFT') then 'CONDITION_RISK_UNREVIEWED'" in sql
    assert "when x.peritaje_count=0 and x.condition_disposition_status in ('UNREVIEWED','DRAFT') then 'REVIEW_CONDITION_RISK'" in sql
    assert "NO_PUBLIC_PERITAJE_REQUIRES_EXPLICIT_DISPOSITION" in sql
    assert "when b.peritaje_count > 0 and b.peritaje_review_status <> 'REVIEWED' then 'PERITAJE_NOT_REVIEWED'" in sql
    assert "when x.peritaje_count > 0 and x.peritaje_review_status <> 'REVIEWED' then 'REVIEW_PERITAJE'" in sql


def test_accept_unknown_condition_still_requires_positive_repair_reserve():
    sql = migration()
    assert "when b.peritaje_count=0 and b.condition_disposition_status='REVIEWED_ACCEPT' and coalesce(b.condition_repair_reserve_cop,0)<=0 then 'CONDITION_REPAIR_RESERVE_MISSING'" in sql
    assert "when x.peritaje_count=0 and x.condition_disposition_status='REVIEWED_ACCEPT' and coalesce(x.condition_repair_reserve_cop,0)<=0 then 'REVIEW_CONDITION_RESERVE'" in sql
    assert "c.repair_cop as condition_repair_reserve_cop" in sql
    assert "NO_PUBLIC_PERITAJE_ACCEPTED_UNKNOWN_RISK" in sql


def test_decline_unknown_condition_never_becomes_ready_or_urgent_work():
    sql = migration()
    assert "when b.peritaje_count=0 and b.condition_disposition_status='REVIEWED_DECLINE' then 'CONDITION_RISK_DECLINED'" in sql
    assert "when x.peritaje_count=0 and x.condition_disposition_status='REVIEWED_DECLINE' then 'NO_ACTION_CONDITION_DECLINED'" in sql
    assert "when r.next_action='NO_ACTION_CONDITION_DECLINED' then 990" in sql
    assert "when r.next_action='NO_ACTION_CONDITION_DECLINED' then 'CONDITION_DECLINED_NO_ACTION'" in sql


def test_condition_rpc_rejects_public_peritaje_requires_evidence_and_has_no_buy_authority():
    sql = migration()
    rpc = sql.split("create or replace function public.dashboard_save_condition_disposition", 1)[1]
    rpc = rpc.split("revoke all on function public.dashboard_save_condition_disposition", 1)[0]
    assert "public peritaje exists; use peritaje review workflow" in rpc
    assert "reviewed condition disposition requires an evidence note of at least 20 characters" in rpc
    assert "ACCEPT_UNKNOWN_WITH_RESERVE" in rpc
    assert "DECLINE_UNKNOWN_CONDITION" in rpc
    assert "'buy_signal',false" in rpc
    assert "'economic_fields_modified',false" in rpc
    for forbidden in (
        "final_decision=",
        "lot_fasecolda_matches",
        "market_manual_evidence",
        "lot_cost_overrides",
        "max_bid_market_validated_cop=",
        "expected_roi_current_pct=",
    ):
        assert forbidden not in rpc


def test_readiness_and_due_diligence_column_contracts_are_append_only():
    sql = migration()
    readiness = sql.split("create or replace view public.dashboard_economic_readiness_current as", 1)[1]
    readiness = readiness.split("revoke all on public.dashboard_economic_readiness_current", 1)[0]
    projection = readiness.split("select\n  x.external_lot_id", 1)[1].split("from blockers x", 1)[0]
    assert projection.index("d.fasecolda_match_interpretation") < projection.index("x.condition_disposition_status")

    old = V46.read_text(encoding="utf-8")
    old_prefix = old.split("'DUE_DILIGENCE_PRIORITY_NOT_BUY_SIGNAL'::text as due_diligence_interpretation", 1)[0]
    current = sql.split("create or replace view public.dashboard_due_diligence_queue as", 1)[1]
    for token in (
        "r.external_lot_id",
        "r.blockers",
        "r.readiness_status",
        "o.pressure_level",
        "as due_diligence_rank",
        "as due_diligence_stage",
        "r.fasecolda_match_origin",
        "r.fasecolda_automatic_status",
        "r.fasecolda_match_interpretation",
    ):
        assert token in current
    assert current.index("r.fasecolda_match_interpretation") < current.index("r.condition_disposition_status")
    assert "dashboard_due_diligence_queue" in old_prefix


def test_condition_queue_is_scoped_to_active_missing_peritaje_cases():
    sql = migration()
    q = sql.split("create or replace view public.dashboard_condition_review_queue_v49 as", 1)[1]
    q = q.split("revoke all on public.dashboard_condition_review_queue_v49", 1)[0]
    assert "where r.peritaje_count=0" in q
    assert "r.readiness_status<>'CLOSED'" in q
    assert "condition_disposition_status in ('UNREVIEWED','DRAFT','REVIEWED_DECLINE')" in q
    assert "condition_disposition_status='REVIEWED_ACCEPT'" in q
    assert "condition_repair_reserve_cop" in q
    assert "CONDITION_EVIDENCE_GATE_NOT_BUY_SIGNAL" in q


def test_condition_dashboard_preserves_exact_lot_and_is_completion_safe():
    ts = condition_ui()
    assert r"^\d{5,12}$" in ts
    assert "function safeLot" in ts
    assert "function lotFromPath" in ts
    assert 'name="lot" value=' in ts
    assert 'lot=safeLot(f.get("lot"))' in ts
    assert "superbid-condition-review-dashboard/lots/${encodeURIComponent(lot)}" in ts
    assert "dashboard_economic_readiness_current" in ts
    assert "superbid-readiness-dashboard?lot=${encodeURIComponent(external)}" in ts
    for token in ("return_to", "redirect_uri", "redirect_url"):
        assert token not in ts.lower()


def test_condition_dashboard_has_narrow_write_authority_and_explicit_guardrails():
    ts = condition_ui()
    assert rpc_names(ts) == {"dashboard_token_valid", "dashboard_save_condition_disposition"}
    assert "CONDITION_EVIDENCE_GATE_NOT_BUY_SIGNAL" in ts
    assert "MANUAL_CONDITION_RISK_DISPOSITION_NOT_DIAGNOSIS_OR_BUY_SIGNAL" in ts
    assert "NO PUBLIC PERITAJE ≠ CONDITION CLEARED" in ts
    assert '"buy_signal"' not in ts.lower()
    assert "dashboard_save_manual_market_evidence" not in ts
    assert "dashboard_apply_cost_profile_to_lot" not in ts
    assert "dashboard_set_fasecolda_manual_resolution" not in ts


def test_condition_dashboard_preserves_private_auth_contract():
    lower = condition_ui().lower()
    assert "dashboard_token_valid" in lower
    assert "httponly; secure; samesite=strict" in lower
    assert 'deno.env.get("supabase_service_role_key")' in lower


def test_readiness_routes_new_condition_actions_without_write_authority():
    ts = readiness_ui()
    assert "REVIEW_CONDITION_RISK" in ts
    assert "superbid-condition-review-dashboard/lots/${id}" in ts
    assert "REVIEW_CONDITION_RESERVE" in ts
    assert "NO_ACTION_CONDITION_DECLINED" in ts
    assert "CONDITION_RISK_UNREVIEWED" in ts
    assert "CONDITION_RISK_DECLINED" in ts
    assert "CONDITION_REPAIR_RESERVE_MISSING" in ts
    assert "CONDITION_EVIDENCE_GATE_NOT_BUY_SIGNAL" in ts
    assert rpc_names(ts) == {"dashboard_token_valid"}


def test_v049_package_version_is_consistent():
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    package = (ROOT / "src/superbid_collector/__init__.py").read_text(encoding="utf-8")
    assert 'version = "0.49.0"' in pyproject
    assert '__version__ = "0.49.0"' in package
