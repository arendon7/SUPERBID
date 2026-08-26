from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MIG = (ROOT / "supabase/migrations/20260821191118_fasecolda_manual_resolution_v33.sql").read_text(encoding="utf-8").lower()
ORIGIN = (ROOT / "supabase/migrations/20260821191250_readiness_fasecolda_origin_v33.sql").read_text(encoding="utf-8").lower()
LEGACY = (ROOT / "supabase/functions/superbid-fasecolda-dashboard/index.ts").read_text(encoding="utf-8").lower()
COCKPIT = (ROOT / "supabase/functions/superbid-fasecolda-candidate-cockpit/index.ts").read_text(encoding="utf-8").lower()
READY = (ROOT / "supabase/functions/superbid-readiness-dashboard/index.ts").read_text(encoding="utf-8").lower()


def test_manual_resolution_is_private_auditable_and_reversible():
    assert "create table if not exists public.lot_fasecolda_manual_resolutions" in MIG
    assert "create table if not exists public.lot_fasecolda_manual_resolution_history" in MIG
    assert "enable row level security" in MIG
    assert "revoke all on public.lot_fasecolda_manual_resolutions from public,anon,authenticated" in MIG
    assert "revoke all on public.lot_fasecolda_manual_resolution_history from public,anon,authenticated" in MIG
    assert "'confirm','clear','invalidate_identity_change'" in MIG
    assert "manual_fasecolda_resolution_not_automatic_match" in MIG


def test_confirm_can_only_use_current_candidate_for_same_lot_and_year():
    fn = MIG[MIG.index("create or replace function public.dashboard_set_fasecolda_manual_resolution"):]
    assert "where lot_id=v_lot.id and code=trim(p_code)" in fn
    assert "candidate model year does not match lot" in fn
    assert "candidate has no usable current value" in fn
    assert "candidate reference not found" in fn
    assert "candidate fails fasecolda identity guard" in fn
    assert "manual resolution is allowed only for ambiguous or medium automatic matches" in fn


def test_automatic_match_is_preserved_and_manual_origin_is_explicit():
    assert "create or replace view public.lot_fasecolda_effective_current" in MIG
    assert "then 'manual_confirmed' else 'automatic' end as match_origin" in MIG
    assert "fm.status as automatic_status" in MIG
    assert "fm.best_code as automatic_best_code" in MIG
    assert "case when mr.lot_id is not null then 'high' else fm.status end as status" in MIG
    assert "automatic match preserved separately" in MIG


def test_identity_change_invalidates_manual_resolution():
    assert "invalidate_manual_fasecolda_resolution_on_identity_change" in MIG
    assert "old.title is distinct from new.title" in MIG
    assert "old.brand is distinct from new.brand" in MIG
    assert "old.line is distinct from new.line" in MIG
    assert "old.model_year is distinct from new.model_year" in MIG
    assert "invalidate_identity_change" in MIG
    assert "delete from public.lot_fasecolda_manual_resolutions" in MIG


def test_readiness_appends_match_origin_without_replacing_buy_logic():
    assert "fasecolda_match_origin" in ORIGIN
    assert "fasecolda_automatic_status" in ORIGIN
    assert "fasecolda_match_interpretation" in ORIGIN
    assert "economic_readiness_not_buy_signal" in ORIGIN
    assert "final_decision" in ORIGIN


def test_legacy_resolver_is_retired_without_losing_exact_lot_context():
    assert "legacy_fasecolda_resolver_redirect_no_business_write" in LEGACY
    assert "superbid-fasecolda-candidate-cockpit/lots/" in LEGACY
    assert r"^\d{5,12}$" in LEGACY
    assert "/rest/v1/rpc/dashboard_set_fasecolda_manual_resolution" not in LEGACY
    assert "/rest/v1/rpc/" not in LEGACY


def test_candidate_cockpit_never_uses_automatic_best_as_a_selection():
    assert "ningún candidato se preselecciona automáticamente" in COCKPIT
    assert "ningún código se elige automáticamente" in COCKPIT
    assert "const requested=" in COCKPIT
    assert "persisted=evidence" in COCKPIT
    assert "selected=candidatecodes.has(requested)" in COCKPIT
    assert "confirm_resolution" in COCKPIT


def test_candidate_cockpit_uses_evidence_rpc_not_legacy_confirm_rpc():
    assert "dashboard_save_fasecolda_candidate_resolution" in COCKPIT
    assert "dashboard_clear_fasecolda_candidate_resolution_v52" in COCKPIT
    assert "dashboard_set_fasecolda_manual_resolution" not in COCKPIT
    assert "dashboard_save_lot_costs" not in COCKPIT
    assert "dashboard_save_peritaje_review" not in COCKPIT
    assert "max_bid_market_validated_cop=" not in COCKPIT
    assert "final_decision=" not in COCKPIT


def test_readiness_dashboard_surfaces_origin_and_routes_valuation_review():
    assert "fasecolda_match_origin" in READY
    assert "fasecolda_automatic_status" in READY
    assert "fasecolda_match_interpretation" in READY
    assert "esc(x.fasecolda_match_origin" in READY
    assert "auto ${esc(x.fasecolda_automatic_status" in READY
    assert "/functions/v1/superbid-fasecolda-workbench" in READY
    assert 'a==="review_valuation"' in READY


def test_new_resolver_is_private_server_rendered_and_legacy_shim_has_no_data_authority():
    assert "dashboard_token_valid" in COCKPIT
    assert "httponly; secure; samesite=strict" in COCKPIT
    assert "<script" not in COCKPIT
    assert "deno.serve" in COCKPIT
    assert "supabase_service_role_key" not in LEGACY
