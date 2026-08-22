from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MIG = (ROOT / "supabase/migrations/20260822022500_fasecolda_search_probe_v35.sql").read_text(encoding="utf-8").lower()


def test_probe_is_service_role_only_and_read_only():
    assert "dashboard_probe_fasecolda_search_term" in MIG
    assert "revoke all on function public.dashboard_probe_fasecolda_search_term(text,text) from public,anon,authenticated" in MIG
    assert "grant execute on function public.dashboard_probe_fasecolda_search_term(text,text) to service_role" in MIG
    for mutation in (
        "insert into public.lot_fasecolda_matches",
        "update public.lot_fasecolda_matches",
        "delete from public.lot_fasecolda_matches",
        "insert into public.lot_fasecolda_candidates",
        "update public.lot_fasecolda_candidates",
        "delete from public.lot_fasecolda_candidates",
    ):
        assert mutation not in MIG


def test_probe_preserves_brand_and_bounds_term():
    assert "invalid search term length" in MIG
    assert "search term must preserve vehicle brand" in MIG
    assert "char_length(v_term)<2 or char_length(v_term)>80" in MIG
    assert "v_term=v_brand or v_term like v_brand||' %'" in MIG


def test_probe_uses_only_public_fasecolda_search_endpoint():
    assert "https://fasecoldaback.quantil.co/api/busqueda/" in MIG
    assert "extensions.urlencode(v_term)" in MIG
    assert "v_resp.status not in (200,404)" in MIG
    assert "ord<=22" in MIG


def test_probe_output_is_explicitly_not_a_match():
    for field in (
        "current_search_term",
        "suggested_search_term",
        "http_status",
        "code_count",
        "has_codes",
        "codes",
    ):
        assert field in MIG
    assert "fasecolda_search_probe_not_match" in MIG
