from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MIG = ROOT / "supabase/migrations/20260826020000_fasecolda_candidate_resolution_evidence_v52.sql"
HARDEN = ROOT / "supabase/migrations/20260826020500_fasecolda_candidate_resolution_gate_hardening_v52.sql"
COCKPIT = ROOT / "supabase/functions/superbid-fasecolda-candidate-cockpit/index.ts"
LEGACY = ROOT / "supabase/functions/superbid-fasecolda-dashboard/index.ts"


def sql() -> str:
    return MIG.read_text(encoding="utf-8")


def hardening_sql() -> str:
    return HARDEN.read_text(encoding="utf-8")


def cockpit() -> str:
    return COCKPIT.read_text(encoding="utf-8")


def rpc_names(source: str) -> set[str]:
    return set(re.findall(r"/rest/v1/rpc/([a-z0-9_]+)", source.lower()))


def version_tuple(text: str, pattern: str) -> tuple[int, int, int]:
    m = re.search(pattern, text)
    assert m
    return tuple(int(x) for x in m.group(1).split("."))


def test_candidate_evidence_state_is_private_append_only_auditable():
    s = sql().lower()
    assert "create table if not exists public.lot_fasecolda_candidate_resolution_evidence" in s
    assert "create table if not exists public.lot_fasecolda_candidate_resolution_evidence_history" in s
    assert "enable row level security" in s
    assert "revoke all on public.lot_fasecolda_candidate_resolution_evidence from public,anon,authenticated" in s
    assert "revoke all on public.lot_fasecolda_candidate_resolution_evidence_history from public,anon,authenticated" in s
    assert "manual_fasecolda_candidate_evidence_not_automatic_match_or_buy_signal" in s
    assert "'draft','confirm','manual_removal_invalidated','identity_change_invalidated'" in s


def test_legacy_manual_resolution_is_backend_gated_by_reviewed_v052_snapshot():
    s = sql().lower()
    assert "create or replace function public.enforce_fasecolda_candidate_evidence_gate_v52" in s
    assert "v0.52 reviewed candidate evidence is required before manual fasecolda confirmation" in s
    assert "manual fasecolda resolution must match current v0.52 reviewed evidence snapshot" in s
    assert "before insert or update on public.lot_fasecolda_manual_resolutions" in s
    assert "new.chosen_code is distinct from e.chosen_code" in s
    assert "new.chosen_value_cop is distinct from e.chosen_value_cop" in s
    assert "new.source_evaluated_at is distinct from e.source_evaluated_at" in s


def test_defense_in_depth_revalidates_direct_service_role_evidence_before_high():
    s = hardening_sql().lower()
    assert "malformed direct service-role evidence write" in s
    assert "reviewed evidence dimensions must be an object" in s
    assert "reviewed evidence missing or invalid dimension" in s
    assert "reviewed evidence contains unresolved status" in s
    assert "reviewed evidence source is not registered for lot dimension" in s
    assert "reviewed evidence requires an explicit non-line discriminating match" in s
    assert "reviewed evidence counters do not match dimensions" in s
    assert "reviewed evidence candidate is no longer current" in s
    assert "reviewed evidence candidate is not uniquely distinguishable" in s
    assert "new manual resolution requires ambiguous or medium automatic status" in s
    assert "manual fasecolda resolution must match current v0.52 reviewed evidence and candidate snapshot" in s
    assert "new.model_year is distinct from c.model_year" in s


def test_reviewed_contract_requires_all_six_dimensions_no_conflict_and_explicit_discriminator():
    s = sql()
    for dim in ("line_identity", "engine_cc", "transmission", "fuel", "drivetrain", "trim_body_use"):
        assert f"'{dim}'" in s
    assert "reviewed candidate evidence requires all six dimensions complete" in s
    assert "reviewed candidate evidence requires line identity MATCH" in s
    assert "reviewed candidate evidence cannot contain CONFLICT" in s
    assert "reviewed candidate evidence requires at least one explicitly discriminating MATCH beyond line identity" in s
    assert "reviewed candidate evidence requires summary note of at least 20 characters" in s
    assert "NOT_STATED" in s


def test_discriminator_flag_is_human_explicit_and_semantically_restricted():
    s = sql()
    assert "invalid discriminating flag for dimension" in s
    assert "discriminating flag is allowed only for non-line MATCH dimensions" in s
    assert "discriminating MATCH requires evidence note of at least 20 characters" in s
    assert "if v_discriminates then v_discriminating:=v_discriminating+1" in s
    t = cockpit()
    assert "__discriminating" in t
    assert "Este MATCH distingue al candidato frente a por lo menos una alternativa actual" in t
    assert "discriminating:String(f.get" in t


def test_source_binding_and_observed_values_are_backend_validated():
    s = sql().lower()
    assert "v_source is distinct from v_lot.url" in s
    assert "from public.lot_attachments a where a.lot_id=v_lot.id and a.url=v_source" in s
    assert "evidence source does not belong to lot for dimension" in s
    assert "evidence source must be http or https for dimension" in s
    assert "reviewed candidate evidence requires observed value for assessed dimension" in s
    assert "evidence note too long for dimension" in s
    assert "observed value too long for dimension" in s


def test_ambiguous_identical_candidate_descriptions_cannot_be_arbitrarily_confirmed():
    s = sql().lower()
    assert "candidate is not uniquely distinguishable from another current candidate" in s
    assert "c.code<>v_candidate.code" in s
    assert "c.model_year is not distinct from v_candidate.model_year" in s
    assert "regexp_replace(upper(trim(c.description))" in s
    assert "[[:space:]]+" in s


def test_draft_never_calls_manual_resolution_and_reviewed_does_so_transactionally():
    s = sql().lower()
    fn = s.split("create or replace function public.dashboard_save_fasecolda_candidate_resolution", 1)[1]
    fn = fn.split("revoke all on function public.dashboard_save_fasecolda_candidate_resolution", 1)[0]
    marker = "if p_mark_reviewed then\n    select public.dashboard_set_fasecolda_manual_resolution"
    assert marker in fn
    draft_return = fn.split("return jsonb_build_object(", 2)[-1]
    assert "'action','draft'" in draft_return
    assert "'match_origin','automatic'" in draft_return
    assert "'automatic_match_overwritten',false" in fn
    assert "'buy_signal',false" in fn
    assert "'economic_fields_modified',false" in fn


def test_clear_and_identity_change_invalidate_current_evidence_but_keep_history():
    s = sql().lower()
    assert "dashboard_clear_fasecolda_candidate_resolution_v52" in s
    assert "clear requires note of at least 10 characters" in s
    assert "'manual_removal_invalidated'" in s
    assert "'identity_change_invalidated'" in s
    assert "after delete on public.lot_fasecolda_manual_resolutions" in s
    assert "after update of title,brand,line,model_year on public.auction_lots" in s
    assert "delete from public.lot_fasecolda_candidate_resolution_evidence" in s


def test_cockpit_view_uses_real_auction_lot_primary_key_join():
    s = sql().lower()
    assert "create or replace view public.dashboard_fasecolda_candidate_resolution_cockpit_v52" in s
    assert "join public.auction_lots a on a.id=r.lot_id" in s
    assert "join public.auction_lots a using(lot_id)" not in s
    assert "left join public.dashboard_fasecolda_valuation_workbench w on w.lot_id=r.lot_id" in s
    assert "evidence_discriminating_match_count" in s


def test_cockpit_is_private_case_preserving_and_completion_safe():
    t = cockpit()
    assert r"^\d{5,12}$" in t
    assert "function lotFromPath" in t
    assert "dashboard_token_valid" in t
    assert "HttpOnly; Secure; SameSite=Strict" in t
    assert "auction_lots?select=" in t
    assert "lot_fasecolda_matches?select=" in t
    assert "lot_fasecolda_candidates?select=" in t
    assert "lot_fasecolda_manual_resolutions?select=" in t
    assert "lot_fasecolda_candidate_resolution_evidence?select=*" in t
    assert "dashboard_fasecolda_candidate_resolution_cockpit_v52" in t
    for token in ("return_to", "redirect_uri", "redirect_url"):
        assert token not in t.lower()


def test_cockpit_has_two_step_candidate_selection_and_never_auto_picks_best_score():
    t = cockpit().lower()
    assert "ningún candidato se preselecciona automáticamente" in t
    assert "ningún código se elige automáticamente" in t
    assert "evaluar este código" in t
    assert "const requested=" in t
    assert "persisted=evidence" in t
    assert "selected=candidatecodes.has(requested)" in t
    assert "best_code||" in t
    selection = t[t.index("const requested="):t.index("const selectedcandidate=")]
    assert "best_code" not in selection
    assert "best_score" not in selection


def test_cockpit_business_write_authority_is_narrow_and_non_economic():
    t = cockpit()
    assert rpc_names(t) == {
        "dashboard_token_valid",
        "dashboard_save_fasecolda_candidate_resolution",
        "dashboard_clear_fasecolda_candidate_resolution_v52",
    }
    lower = t.lower()
    for forbidden in (
        "dashboard_set_fasecolda_manual_resolution",
        "dashboard_save_lot_costs",
        "dashboard_transfer_peritaje_repair_to_costs",
        "dashboard_save_market",
        "final_decision=",
        "max_bid_market_validated_cop=",
        "expected_roi_current_pct=",
    ):
        assert forbidden not in lower
    assert "no buy signal" in lower


def test_legacy_edge_is_only_a_numeric_context_redirect_shim():
    t = LEGACY.read_text(encoding="utf-8")
    assert r"^\d{5,12}$" in t
    assert "LEGACY_FASECOLDA_RESOLVER_REDIRECT_NO_BUSINESS_WRITE" in t
    assert "superbid-fasecolda-candidate-cockpit/lots/" in t
    assert "/rest/v1/rpc/" not in t
    assert "SUPABASE_SERVICE_ROLE_KEY" not in t
    assert "return_to" not in t.lower()


def test_v052_package_version_is_exact_and_consistent():
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    package = (ROOT / "src/superbid_collector/__init__.py").read_text(encoding="utf-8")
    pv = version_tuple(pyproject, r'version\s*=\s*"(\d+\.\d+\.\d+)"')
    iv = version_tuple(package, r'__version__\s*=\s*"(\d+\.\d+\.\d+)"')
    assert pv == iv == (0, 52, 0)
