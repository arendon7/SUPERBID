from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MIGRATION = (ROOT / "supabase/migrations/20260827161000_fasecolda_detail_403_backoff_v601.sql").read_text(encoding="utf-8")
DASH = (ROOT / "supabase/functions/superbid-fasecolda-search-evidence-dashboard/index.ts").read_text(encoding="utf-8")


def rpc_names(source: str) -> set[str]:
    return set(re.findall(r"/rest/v1/rpc/([a-z0-9_]+)", source.lower()))


def version_tuple(text: str, pattern: str) -> tuple[int, int, int]:
    match = re.search(pattern, text)
    assert match
    return tuple(int(part) for part in match.group(1).split("."))


def test_v0601_creates_private_retry_classifier_and_queue_wrapper():
    lower = MIGRATION.lower()
    assert "create or replace function public.fasecolda_detail_retry_class_v601" in lower
    assert "create or replace view public.dashboard_fasecolda_search_evidence_queue_v601" in lower
    assert "from public.dashboard_fasecolda_search_evidence_queue_v60 q" in lower
    assert "revoke all on function public.fasecolda_detail_retry_class_v601(integer,boolean)" in lower
    assert "grant execute on function public.fasecolda_detail_retry_class_v601(integer,boolean)" in lower
    assert "revoke all on public.dashboard_fasecolda_search_evidence_queue_v601" in lower
    assert "grant select on public.dashboard_fasecolda_search_evidence_queue_v601 to service_role" in lower


def test_v0601_retry_classifier_is_fail_closed_for_fresh_4xx():
    lower = MIGRATION.lower()
    assert "p_http_status = 403 then 'forbidden_nonretryable'" in lower
    assert "p_http_status = 200 then 'invalid_nonretryable'" in lower
    assert "p_http_status between 400 and 499 and p_http_status not in (408,425,429)" in lower
    assert "'rejected_nonretryable'" in lower
    assert "p_http_status in (408,425,429)" in lower
    assert "p_http_status between 500 and 599" in lower
    assert "'unavailable_retryable'" in lower
    assert "p_http_status = 200 and p_payload_valid is true then 'valid'" in lower


def test_v0601_fresh_403_routes_human_but_stale_evidence_refreshes_first():
    lower = MIGRATION.lower()
    stale_at = lower.index("when not q.evidence_fresh then 'suggested_evidence_stale'")
    forbidden_at = lower.index("then 'suggested_detail_forbidden'")
    assert stale_at < forbidden_at
    assert "then 'open_human_search'" in lower
    assert "then 'refresh_suggested_evidence'" in lower
    assert "suggested_detail_forbidden" in lower
    assert "suggested_detail_invalid" in lower
    assert "suggested_detail_rejected" in lower
    assert "fasecolda_detail_4xx_backoff_not_match_or_buy_signal" in lower


def test_v0601_migration_is_routing_only_without_business_writes():
    lower = MIGRATION.lower()
    for forbidden in (
        "insert into public.",
        "update public.",
        "delete from public.",
        "lot_fasecolda_search_term_overrides",
        "lot_fasecolda_manual_resolutions",
        "lot_fasecolda_matches",
        "lot_fasecolda_candidates",
        "recommended_bid",
        "max_bid",
        "final_decision",
    ):
        assert forbidden not in lower


def test_v0601_edge_reads_wrapper_and_nonretryable_states_are_not_refresh_states():
    lower = DASH.lower()
    assert "dashboard_fasecolda_search_evidence_queue_v601" in lower
    assert "evidence_state_v601" in lower
    assert "operator_next_action_v601" in lower
    assert "suggested_term_reviewable_v601" in lower
    assert "evidence_state_rank_v601" in lower
    refresh_set = re.search(r"const refresh_states=new set\(\[(.*?)\]\);", lower)
    assert refresh_set
    refresh_body = refresh_set.group(1)
    for state in ("suggested_detail_forbidden", "suggested_detail_invalid", "suggested_detail_rejected"):
        assert state not in refresh_body
    assert "suggested_detail_unavailable" in refresh_body
    assert "suggested_evidence_stale" in refresh_body


def test_v0601_direct_post_cannot_bypass_backoff():
    lower = DASH.lower()
    guard_at = lower.index("if(!refresh_states.has(evidencestate))")
    rpc_at = lower.index("await refreshrpc(lot,term)", guard_at)
    assert guard_at < rpc_at
    assert "refresh no elegible" in lower
    assert "usa search humano o vuelve cuando el estado sea stale" in lower


def test_v0601_batch_remains_bounded_sequential_and_skips_nonretryable():
    lower = DASH.lower()
    assert "const batch_refresh_limit=6" in lower
    assert "for(const x of targets)" in lower
    assert "await refreshrpc" in lower
    assert "promise.all" not in lower
    assert "refresh_states.has(string(x.evidence_state_v601" in lower
    assert "4xx no reintentables frescos quedan fuera del batch" in lower


def test_v0601_authority_and_auth_contract_are_unchanged():
    assert rpc_names(DASH) == {
        "dashboard_token_valid",
        "dashboard_refresh_fasecolda_search_term_evidence_v60",
    }
    lower = DASH.lower()
    assert "httponly; secure; samesite=strict" in lower
    assert "fasecolda_detail_4xx_backoff_not_match_or_buy_signal" in lower
    for forbidden in (
        "dashboard_set_fasecolda_search_term_override",
        "fasecolda_match_lot",
        "dashboard_save_fasecolda_candidate_resolution",
        "recommended_bid",
        "max_bid",
        "final_decision",
    ):
        assert forbidden not in lower


def test_v0601_package_version_is_exact():
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    package = (ROOT / "src/superbid_collector/__init__.py").read_text(encoding="utf-8")
    pv = version_tuple(pyproject, r'version\s*=\s*"(\d+\.\d+\.\d+)"')
    iv = version_tuple(package, r'__version__\s*=\s*"(\d+\.\d+\.\d+)"')
    assert pv == iv == (0, 60, 1)
