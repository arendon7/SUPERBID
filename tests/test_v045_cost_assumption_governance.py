from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MIGRATION = ROOT / "supabase/migrations/20260825040000_cost_assumption_governance_v45.sql"
DASHBOARD = ROOT / "supabase/functions/superbid-cost-governance-dashboard/index.ts"
V44 = ROOT / "supabase/migrations/20260825030000_auditable_manual_market_evidence_v44.sql"


def migration() -> str:
    return MIGRATION.read_text(encoding="utf-8")


def dashboard() -> str:
    return DASHBOARD.read_text(encoding="utf-8")


def test_v045_release_artifacts_remain_identifiable_after_patch_releases():
    # Historical release tests protect the v0.45 contract/artifacts, not the
    # repository's mutable global package version.
    assert MIGRATION.exists()
    assert DASHBOARD.exists()
    assert "SUPERBID · v0.45" in dashboard()
    sql = migration()
    assert "COST_PROFILE_ASSUMPTION_NOT_LOT_COST" in sql
    assert "COST_PROFILE_APPLICATION_REQUIRES_LOT_CONFIRMATION" in sql
    assert "COST_GOVERNANCE_NOT_BUY_SIGNAL" in sql


def test_cost_profiles_are_immutable_backend_only_assumptions():
    sql = migration()
    assert "create table if not exists public.cost_assumption_profile_versions" in sql
    assert "generated always as identity primary key" in sql
    assert "COST_PROFILE_ASSUMPTION_NOT_LOT_COST" in sql
    assert "grant select,insert on public.cost_assumption_profile_versions to service_role" in sql
    assert "grant select,update" not in sql
    assert "revoke all on public.cost_assumption_profile_versions,public.lot_cost_profile_application_history from public,anon,authenticated" in sql


def test_reviewed_profile_requires_all_eight_values_and_source_note():
    sql = migration()
    rpc = sql.split("create or replace function public.dashboard_save_cost_assumption_profile", 1)[1]
    rpc = rpc.split("revoke all on function public.dashboard_save_cost_assumption_profile", 1)[0]
    assert "all eight cost assumptions are required before review" in rpc
    assert "reviewed cost profile requires a source note" in rpc
    for field in (
        "p_transfer_cop",
        "p_taxes_soat_cop",
        "p_transport_cop",
        "p_repair_cop",
        "p_detailing_cop",
        "p_financing_cop",
        "p_admin_fee_cop",
        "p_contingency_cop",
    ):
        assert field in rpc
    assert "'lots_modified',0" in rpc
    assert "'buy_signal',false" in rpc


def test_profile_creation_never_mutates_deal_profiles_or_lots():
    sql = migration()
    rpc = sql.split("create or replace function public.dashboard_save_cost_assumption_profile", 1)[1]
    rpc = rpc.split("revoke all on function public.dashboard_save_cost_assumption_profile", 1)[0]
    assert "deal_profiles" not in rpc
    assert "lot_cost_overrides" not in rpc
    assert "lot_cost_review_history" not in rpc
    assert "final_decision=" not in rpc


def test_only_reviewed_profile_can_be_applied_to_one_explicit_lot():
    sql = migration()
    rpc = sql.split("create or replace function public.dashboard_apply_cost_profile_to_lot", 1)[1]
    rpc = rpc.split("revoke all on function public.dashboard_apply_cost_profile_to_lot", 1)[0]
    assert "p_external_lot_id" in rpc
    assert "p_profile_version_id" in rpc
    assert "only REVIEWED cost profiles may be applied" in rpc
    assert "closed lot cannot receive a new cost profile application" in rpc
    assert "lot_cost_overrides" in rpc
    assert "COST_PROFILE_APPLICATION_REQUIRES_LOT_CONFIRMATION" in rpc
    assert "'buy_signal',false" in rpc
    assert "for q in" not in rpc.lower()
    assert "array_agg" not in rpc.lower()


def test_preserve_lot_repair_requires_existing_repair_and_never_silently_overwrites_it():
    sql = migration()
    rpc = sql.split("create or replace function public.dashboard_apply_cost_profile_to_lot", 1)[1]
    rpc = rpc.split("revoke all on function public.dashboard_apply_cost_profile_to_lot", 1)[0]
    assert "v_mode not in ('PROFILE','PRESERVE_LOT')" in rpc
    assert "PRESERVE_LOT requires an existing lot repair cost" in rpc
    assert "case when v_mode='PRESERVE_LOT' then v_existing.repair_cop else v_profile.repair_cop end" in rpc


def test_profile_application_snapshots_values_and_writes_both_histories():
    sql = migration()
    rpc = sql.split("create or replace function public.dashboard_apply_cost_profile_to_lot", 1)[1]
    rpc = rpc.split("revoke all on function public.dashboard_apply_cost_profile_to_lot", 1)[0]
    assert "insert into public.lot_cost_overrides" in rpc
    assert "insert into public.lot_cost_review_history" in rpc
    assert "insert into public.lot_cost_profile_application_history" in rpc
    assert "previous_costs" in rpc
    assert "applied_costs" in rpc
    assert "profile_fingerprint" in rpc


def test_cost_readiness_coverage_no_longer_depends_on_peritaje_view():
    sql = migration()
    view = sql.split("create or replace view public.dashboard_cost_readiness_current as", 1)[1]
    view = view.split("revoke all on public.dashboard_cost_readiness_current", 1)[0]
    assert "from public.dashboard_lot_current d" in view
    assert "left join public.lot_peritaje_reviews p" in view
    assert "left join public.lot_cost_overrides c" in view
    assert "dashboard_peritaje_review_current" not in view
    assert "when coalesce(d.peritaje_count,0)=0 then 'NOT_AVAILABLE'" in view


def test_cost_readiness_preserves_existing_column_contract_and_peritaje_guardrail():
    sql = migration()
    view = sql.split("create or replace view public.dashboard_cost_readiness_current as", 1)[1]
    view = view.split("revoke all on public.dashboard_cost_readiness_current", 1)[0]
    for column in (
        "d.external_lot_id",
        "d.lot_id",
        "d.title",
        "p.repair_low_cop",
        "p.repair_base_cop",
        "p.repair_high_cop",
        "c.transfer_cop",
        "c.contingency_cop",
        "cost_review_status",
        "completed_cost_fields",
        "repair_cost_source_status",
        "peritaje_ready_for_cost_transfer",
    ):
        assert column in view
    assert "MANUAL_PERITAJE_COST_TRANSFER_NOT_AUTOMATIC" in view


def test_v045_governance_queue_is_all_cost_blockers_not_only_peritaje_cases():
    sql = migration()
    q = sql.split("create or replace view public.dashboard_cost_governance_queue_v45 as", 1)[1]
    q = q.split("revoke all on public.dashboard_cost_governance_queue_v45", 1)[0]
    assert "dashboard_economic_readiness_current" in q
    assert "dashboard_cost_readiness_current" in q
    assert "LOT_COSTS_MISSING" in q
    assert "LOT_COSTS_INCOMPLETE" in q
    assert "LOT_COSTS_NOT_REVIEWED" in q
    assert "CONFIGURE_REVIEWED_PROFILE" in q
    assert "APPLY_PROFILE_PRESERVE_REPAIR" in q
    assert "COST_GOVERNANCE_NOT_BUY_SIGNAL" in q


def test_private_dashboard_has_server_side_auth_no_bulk_apply_and_custom_escape_hatch():
    ts = dashboard()
    assert "dashboard_token_valid" in ts
    assert "HttpOnly; Secure; SameSite=Strict" in ts
    assert 'Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")' in ts
    assert "dashboard_save_cost_assumption_profile" in ts
    assert "dashboard_apply_cost_profile_to_lot" in ts
    assert "COST_PROFILE_ASSUMPTION_NOT_LOT_COST" in ts
    assert "COST_GOVERNANCE_NOT_BUY_SIGNAL" in ts
    assert "Aplicación siempre individual" in ts
    assert "#costs" in ts
    assert "bulk" not in ts.lower()
    assert '"buy_signal"' not in ts.lower()
    assert "deal_profiles" not in ts


def test_profile_application_post_must_not_redirect_to_queue_only_lot_page_after_review():
    ts = dashboard()
    apply = ts.split("async function applyProfile", 1)[1]
    apply = apply.split("Deno.serve", 1)[0]
    assert "dashboard_apply_cost_profile_to_lot" in apply
    assert "superbid-cost-governance-dashboard?saved=applied" in apply or "superbid-dashboard/lots/${external}" in apply
    assert "superbid-cost-governance-dashboard/lots/${external}?saved=1" not in apply


def test_v045_preserves_v044_market_evidence_guardrails():
    v44 = V44.read_text(encoding="utf-8")
    assert "MANUAL_MARKET_EVIDENCE_NOT_AUTOMATIC_VALUATION" in v44
    assert "MARKET_REVIEW_NOT_BUY_SIGNAL" in v44
    sql = migration()
    apply_rpc = sql.split("create or replace function public.dashboard_apply_cost_profile_to_lot", 1)[1]
    apply_rpc = apply_rpc.split("revoke all on function public.dashboard_apply_cost_profile_to_lot", 1)[0]
    assert "market_manual_evidence" not in apply_rpc
    assert "lot_fasecolda_matches" not in apply_rpc
