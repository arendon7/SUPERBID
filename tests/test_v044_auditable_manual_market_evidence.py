from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MIGRATION = ROOT / "supabase/migrations/20260825030000_auditable_manual_market_evidence_v44.sql"
DASHBOARD = ROOT / "supabase/functions/superbid-market-review-dashboard/index.ts"
VERSION = ROOT / "src/superbid_collector/__init__.py"
PYPROJECT = ROOT / "pyproject.toml"
V43 = ROOT / "supabase/migrations/20260822044324_fasecolda_workbench_lifecycle_triage_v43.sql"


def migration() -> str:
    return MIGRATION.read_text(encoding="utf-8")


def dashboard() -> str:
    return DASHBOARD.read_text(encoding="utf-8")


def test_v044_version_is_exposed_consistently():
    assert '__version__ = "0.44.0"' in VERSION.read_text(encoding="utf-8")
    assert 'version = "0.44.0"' in PYPROJECT.read_text(encoding="utf-8")
    assert "SUPERBID · v0.44" in dashboard()


def test_manual_market_evidence_is_immutable_auditable_and_backend_only():
    sql = migration()
    assert "market_manual_evidence_sets" in sql
    assert "market_manual_evidence_items" in sql
    assert "generated always as identity primary key" in sql
    assert "unique(evidence_set_id,source_url)" in sql
    assert "evidence_fingerprint" in sql
    assert "MANUAL_MARKET_EVIDENCE_NOT_AUTOMATIC_VALUATION" in sql
    assert "revoke all on public.market_manual_evidence_sets,public.market_manual_evidence_items from public,anon,authenticated" in sql
    assert "grant select,insert,update on public.market_manual_evidence_sets to service_role" in sql
    assert "grant select,insert on public.market_manual_evidence_items to service_role" in sql


def test_reviewed_manual_market_evidence_requires_three_real_same_year_https_comparables():
    sql = migration()
    assert "if p_mark_reviewed and v_count<3" in sql
    assert "at least three comparables are required before review" in sql
    assert "reviewed market evidence requires a source note" in sql
    assert "v_url !~ '^https://[^[:space:]]+$'" in sql
    assert "unique(evidence_set_id,source_url)" in sql
    assert "v_year<>v_model_year" in sql
    assert "model year does not match lot year" in sql
    assert "asking_price_cop between 100000 and 5000000000" in sql


def test_draft_cannot_become_effective_market_validation():
    sql = migration()
    manual_view = sql.split("create or replace view public.market_manual_valuation_current as", 1)[1]
    manual_view = manual_view.split("create or replace view public.market_valuation_effective_current as", 1)[0]
    assert "where s.status='REVIEWED'" in manual_view
    assert "s.comparable_count>=3" in manual_view
    assert "'READY'::text as status" in manual_view
    assert "'MANUAL_REVIEWED'::text as evidence_origin" in manual_view


def test_effective_market_evidence_preserves_origin_and_ready_precedence():
    sql = migration()
    assert "create or replace view public.market_valuation_effective_current" in sql
    assert "'MERCADOLIBRE_PIPELINE'::text as evidence_origin" in sql
    assert "'MANUAL_REVIEWED'::text as evidence_origin" in sql
    assert "case status when 'READY' then 0" in sql
    assert "observed_at desc nulls last" in sql
    assert "market_evidence_origin" in sql
    assert "market_evidence_fingerprint" in sql
    assert "case when mv.status='READY' and mv.comparable_count>=3 then true else false end market_validation_available" in sql


def test_existing_market_intelligence_column_order_is_preserved_and_provenance_appended():
    sql = migration()
    view = sql.split("create or replace view public.lot_market_intelligence_current as", 1)[1]
    view = view.split("revoke all on public.lot_market_intelligence_current", 1)[0]
    assert "mv.status market_status" in view
    assert "mv.comparable_count market_comparable_count_live" in view
    assert "market_validation_available," in view
    assert view.index("mv.status market_status") < view.index("market_validation_available")
    assert view.index("market_validation_available") < view.index("mv.source as market_validation_source")
    assert view.index("mv.source as market_validation_source") < view.index("mv.evidence_origin as market_evidence_origin")


def test_conservative_resale_still_caps_market_evidence_by_fasecolda():
    sql = migration()
    assert "least(mv.quick_sale_cop,round(o.fasecolda_current_cop*0.95)::bigint)" in sql
    assert "conservative_resale_market_validated_cop" in sql
    assert "v_quick:=round(v_p25*0.95)::bigint" in sql


def test_manual_evidence_rpc_never_grants_a_buy_signal_or_writes_other_decision_layers():
    sql = migration()
    rpc = sql.split("create or replace function public.dashboard_save_manual_market_evidence", 1)[1]
    rpc = rpc.split("revoke all on function public.dashboard_save_manual_market_evidence", 1)[0]
    assert "'buy_signal',false" in rpc
    assert "MANUAL_MARKET_EVIDENCE_NOT_AUTOMATIC_VALUATION" in rpc
    assert "lot_fasecolda_matches" not in rpc
    assert "lot_cost_overrides" not in rpc
    assert "final_decision=" not in rpc
    assert "max_bid_market_validated_cop=" not in rpc
    assert "expected_roi_current_pct=" not in rpc


def test_market_review_queue_is_readiness_scoped_and_exposes_lot_year():
    sql = migration()
    assert "create or replace view public.dashboard_market_review_queue_v44" in sql
    assert "l.model_year" in sql
    assert "join public.auction_lots l on l.id=r.lot_id" in sql
    assert "r.readiness_status='BLOCKED'" in sql
    assert "r.blockers @> array['MARKET_NOT_VALIDATED']::text[]" in sql
    assert "'MARKET_REVIEW_NOT_BUY_SIGNAL'::text as interpretation" in sql
    assert "revoke all on public.dashboard_market_review_queue_v44 from public,anon,authenticated" in sql


def test_private_dashboard_uses_custom_auth_live_connection_and_only_review_post_mutates_business_data():
    ts = dashboard()
    assert "dashboard_token_valid" in ts
    assert "HttpOnly; Secure; SameSite=Strict" in ts
    assert 'Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")' in ts
    assert "MANUAL_MARKET_EVIDENCE_NOT_AUTOMATIC_VALUATION" in ts
    assert "MARKET_REVIEW_NOT_BUY_SIGNAL" in ts
    assert "dashboard_save_manual_market_evidence" in ts
    assert "REVIEWED requiere al menos 3 comparables" in ts
    assert "URL | PRECIO_COP | AÑO | TÍTULO | CIUDAD" in ts
    assert "async function marketConnection()" in ts
    assert "market_connections?select=source,status,access_expires_at,updated_at,last_error" in ts
    assert '"OAuth Mercado Libre","APP_REQUIRED"' not in ts
    assert "model_year" in ts
    assert "Año obligatorio del lote" in ts
    # The visible guardrail intentionally contains NOT_BUY_SIGNAL. What must not
    # exist in the dashboard is a mutable/business payload field named buy_signal.
    assert '"buy_signal"' not in ts.lower()
    assert "'buy_signal'" not in ts.lower()
    assert "lot_fasecolda_matches" not in ts
    assert "dashboard_save_lot_costs" not in ts


def test_v044_preserves_v043_economic_blocking_contract():
    v43 = V43.read_text(encoding="utf-8")
    assert "sigue bloqueado económicamente" in v43
    assert "FASECOLDA_VALUATION_TRIAGE_NOT_MATCH" in v43
    sql = migration()
    assert "MARKET_REVIEW_NOT_BUY_SIGNAL" in sql
    assert "Never writes Fasecolda, costs, bid, ROI or final decision directly" in sql
