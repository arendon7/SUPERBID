from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MIGRATION = (ROOT / "supabase/migrations/20260827050000_fasecolda_search_evidence_cache_v60.sql").read_text(encoding="utf-8")
DASH = (ROOT / "supabase/functions/superbid-fasecolda-search-evidence-dashboard/index.ts").read_text(encoding="utf-8")


def test_v060_detail_payload_validity_is_persisted_in_current_and_history():
    lower = MIGRATION.lower()
    assert lower.count("detail_payload_valid boolean") >= 2
    assert "detail_http_status,detail_payload_valid,details" in lower
    assert "'detail_payload_valid',v_detail_payload_valid" in lower
    assert "coalesce(v_detail_payload_valid::text,'')" in lower


def test_v060_http_200_only_becomes_valid_when_detail_payload_is_array():
    lower = MIGRATION.lower()
    start = lower.index("v_detail_payload_valid := false")
    parse = lower.index("v_details := v_resp.content::jsonb", start)
    array_check = lower.index("jsonb_typeof(v_details)='array'", parse)
    mark_valid = lower.index("v_detail_payload_valid := true", array_check)
    assert start < parse < array_check < mark_valid
    assert "exception when others then" in lower[parse:mark_valid + 500]
    assert "v_detail_payload_valid := false" in lower[parse:mark_valid + 500]


def test_v060_invalid_detail_payload_cannot_become_negative_year_evidence():
    lower = MIGRATION.lower()
    view = lower[lower.index("create or replace view public.dashboard_fasecolda_search_evidence_queue_v60"):]
    unavailable = view.index("a.evidence_detail_payload_valid is distinct from true then 'suggested_detail_unavailable'")
    no_year = view.index("a.year_compatible_code_count=0 then 'suggested_no_year_compatible_codes'")
    assert unavailable < no_year
    assert "case when j.evidence_detail_payload_valid is true and jsonb_typeof(j.evidence_details)='array'" in view
    assert "and a.evidence_detail_payload_valid is true" in view


def test_v060_dashboard_exposes_payload_validity_to_operator():
    lower = DASH.lower()
    assert "evidence_detail_payload_valid" in lower
    assert "payload detalle válido" in lower
    assert 'detailvalid:j.detail_payload_valid' in lower
    assert 'r.detailvalid===true?"válido":r.detailvalid===false?"inválido":"no aplica"' in lower
