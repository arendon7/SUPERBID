from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MIGRATION = (ROOT / "supabase/migrations/20260827050000_fasecolda_search_evidence_cache_v60.sql").read_text(encoding="utf-8")
EVIDENCE_DASH = (ROOT / "supabase/functions/superbid-fasecolda-search-evidence-dashboard/index.ts").read_text(encoding="utf-8")
WORKBENCH = (ROOT / "supabase/functions/superbid-fasecolda-workbench/index.ts").read_text(encoding="utf-8")


def rpc_names(source: str) -> set[str]:
    return set(re.findall(r"/rest/v1/rpc/([a-z0-9_]+)", source.lower()))


def version_tuple(text: str, pattern: str) -> tuple[int, int, int]:
    match = re.search(pattern, text)
    assert match
    return tuple(int(part) for part in match.group(1).split("."))


def migration_section(start: str, end: str) -> str:
    lower = MIGRATION.lower()
    a = lower.index(start.lower())
    b = lower.index(end.lower(), a)
    return lower[a:b]


def test_v060_cache_tables_are_private_and_history_is_append_only():
    lower = MIGRATION.lower()
    for table in (
        "fasecolda_search_term_evidence_current",
        "fasecolda_search_term_evidence_history",
    ):
        assert f"create table if not exists public.{table}" in lower
        assert f"alter table public.{table} enable row level security" in lower
        assert f"revoke all on public.{table} from public, anon, authenticated" in lower
    assert "grant select,insert,update on public.fasecolda_search_term_evidence_current to service_role" in lower
    assert "grant select,insert on public.fasecolda_search_term_evidence_history to service_role" in lower
    assert "grant select,insert,update" not in lower[lower.index("grant select,insert on public.fasecolda_search_term_evidence_history"):]
    assert "delete from public.fasecolda_search_term_evidence_history" not in lower


def test_v060_sql_input_classifier_matches_v054_fail_closed_semantics():
    lower = MIGRATION.lower()
    section = migration_section(
        "create or replace function public.fasecolda_search_input_disposition_v60",
        "revoke all on function public.fasecolda_search_input_disposition_v60",
    )
    assert "public.vehicle_norm" in section
    assert "p_model_year is null or p_model_year < 1900 or p_model_year > 2100" in section
    for generic in ("COMBO", "AUTOMOVIL", "CAMION", "CAMIONETA", "VEHICULO", "VOLQUETA", "TRACTOCAMION", "TRACTOMULA", "BUS", "MICROBUS"):
        assert f"'{generic.lower()}'" in section
    assert "identity_input_review" in section
    assert "missing_year" in section
    assert "explorable" in section
    assert "v_suggested=v_brand or v_suggested like v_brand||' %'" in section
    assert "left(public.vehicle_norm" in section
    assert "fasecolda_search_input_disposition_v60" in lower


def test_v060_refresh_persists_only_automated_search_evidence():
    section = migration_section(
        "create or replace function public.dashboard_refresh_fasecolda_search_term_evidence_v60",
        "revoke all on function public.dashboard_refresh_fasecolda_search_term_evidence_v60",
    )
    assert "dashboard_probe_fasecolda_search_term" in section
    assert "api/listacodigosid/consultabycodigo/" in section
    assert "insert into public.fasecolda_search_term_evidence_current" in section
    assert "insert into public.fasecolda_search_term_evidence_history" in section
    assert "on conflict(search_term) do update" in section
    for forbidden in (
        "insert into public.lot_fasecolda_matches",
        "update public.lot_fasecolda_matches",
        "delete from public.lot_fasecolda_matches",
        "insert into public.lot_fasecolda_candidates",
        "update public.lot_fasecolda_candidates",
        "delete from public.lot_fasecolda_candidates",
        "lot_fasecolda_search_term_overrides",
        "lot_fasecolda_manual_resolutions",
        "dashboard_economic_readiness",
        "market_comparables",
        "lot_cost",
        "recommended_bid",
        "max_bid",
        "final_decision",
    ):
        assert forbidden not in section
    for flag in (
        "'override_fields_modified',false",
        "'match_fields_modified',false",
        "'candidate_fields_modified',false",
        "'valuation_fields_modified',false",
        "'economic_fields_modified',false",
        "'buy_signal',false",
    ):
        assert flag in section
    assert "fasecolda_search_evidence_not_override_match_or_valuation" in section


def test_v060_refresh_revalidates_exact_lot_brand_and_input_before_http():
    section = migration_section(
        "create or replace function public.dashboard_refresh_fasecolda_search_term_evidence_v60",
        "revoke all on function public.dashboard_refresh_fasecolda_search_term_evidence_v60",
    )
    exact_at = section.index("invalid external lot id")
    input_at = section.index("fasecolda_search_input_disposition_v60")
    brand_at = section.index("search term must preserve vehicle brand")
    probe_at = section.index("dashboard_probe_fasecolda_search_term")
    assert exact_at < input_at < brand_at < probe_at
    assert "^\\d{5,12}$" in MIGRATION


def test_v060_queue_reuses_term_evidence_and_checks_year_without_valuation():
    section = MIGRATION.lower()[MIGRATION.lower().index("create or replace view public.dashboard_fasecolda_search_evidence_queue_v60"):]
    assert "from public.dashboard_fasecolda_resolution_workstreams_v59" in section
    assert "where w.workstream='search_review'" in section
    assert "c.search_term=b.normalized_suggested_term" in section
    assert "interval '24 hours'" in section
    assert "jsonb_array_elements" in section
    assert "item->'valormodelo'" in section
    assert "(m->>'modelo')::integer=j.model_year" in section
    assert "year_compatible_code_count" in section
    for state in (
        "identity_input_review",
        "missing_year",
        "suggested_evidence_missing",
        "suggested_evidence_stale",
        "suggested_no_codes",
        "suggested_detail_unavailable",
        "suggested_no_year_compatible_codes",
        "suggested_year_compatible_codes",
    ):
        assert state in section
    assert "value_cop" not in section
    assert "candidate_min_cop" not in section
    assert "candidate_median_cop" not in section
    assert "candidate_max_cop" not in section
    assert "fasecolda_search_evidence_not_override_match_or_valuation" in section


def test_v060_evidence_dashboard_has_auth_plus_cache_refresh_authority_only():
    assert rpc_names(EVIDENCE_DASH) == {
        "dashboard_token_valid",
        "dashboard_refresh_fasecolda_search_term_evidence_v60",
    }
    lower = EVIDENCE_DASH.lower()
    for forbidden in (
        "dashboard_set_fasecolda_search_term_override",
        "dashboard_probe_fasecolda_search_term",
        "fasecolda_match_lot",
        "dashboard_save_fasecolda_candidate_resolution",
        "recommended_bid",
        "max_bid",
        "final_decision",
        "buy_signal=true",
    ):
        assert forbidden not in lower
    assert "httponly; secure; samesite=strict" in lower
    assert "<script" not in lower


def test_v060_batch_refresh_is_explicit_bounded_deduplicated_and_sequential():
    lower = EVIDENCE_DASH.lower()
    assert "const batch_refresh_limit=6" in lower
    assert 'p==="/refresh-next"&&req.method==="post"' in lower
    assert "new map<string,any>()" in lower
    assert "unique.has(key)" in lower
    assert "unique.size>=batch_refresh_limit" in lower
    assert "for(const x of targets)" in lower
    assert "await refreshrpc" in lower
    assert "promise.all" not in lower
    assert "máximo ${batch_refresh_limit}" in lower
    assert "no se confirmó ningún término ni se ejecutó matcher" in lower


def test_v060_exact_lot_and_human_authority_handoff_are_preserved():
    lower = EVIDENCE_DASH.lower()
    assert "^\\d{5,12}$" in EVIDENCE_DASH
    assert "requestedlot" in lower
    assert "external_lot_id=eq.${encodeuricomponent(lot)}" in lower
    assert "superbid-fasecolda-search-dashboard" in lower
    assert "search humano" in lower
    assert "suggested_term_reviewable" in lower
    for forbidden in ("return_to", "redirect_uri", "redirect_url"):
        assert forbidden not in lower


def test_v060_workbench_routes_search_primary_to_evidence_and_keeps_human_shortcut():
    lower = WORKBENCH.lower()
    assert "superbid-fasecolda-search-evidence-dashboard?lot=${id}" in lower
    assert "superbid-fasecolda-search-dashboard?lot=${id}&reason=" in lower
    assert "preparar evidencia búsqueda" in lower
    assert "search humano" in lower
    assert "fasecolda_search_evidence_not_override_match_or_valuation" in lower
    assert rpc_names(WORKBENCH) == {"dashboard_token_valid"}


def test_v060_package_version_is_consistent():
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    package = (ROOT / "src/superbid_collector/__init__.py").read_text(encoding="utf-8")
    pv = version_tuple(pyproject, r'version\s*=\s*"(\d+\.\d+\.\d+)"')
    iv = version_tuple(package, r'__version__\s*=\s*"(\d+\.\d+\.\d+)"')
    assert pv == iv
    assert pv >= (0, 60, 0)
