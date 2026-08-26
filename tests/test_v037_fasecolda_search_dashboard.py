import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DASH_RAW = (ROOT / "supabase/functions/superbid-fasecolda-search-dashboard/index.ts").read_text(encoding="utf-8")
DASH = DASH_RAW.lower()


def test_dashboard_is_private_server_rendered():
    assert "dashboard_token_valid" in DASH
    assert "httponly; secure; samesite=strict" in DASH
    assert "<script" not in DASH
    assert "deno.serve" in DASH


def test_board_reads_v034_diagnostics_without_writing():
    assert "dashboard_fasecolda_unmatched_diagnostics" in DASH
    assert "fasecolda_search_probe_not_match" in DASH
    assert "diagnostic_reason" in DASH
    assert "suggested_search_term" in DASH


def test_probe_precedes_override_confirmation():
    assert "dashboard_probe_fasecolda_search_term" in DASH
    assert "pr.has_codes ? overrideform" in DASH
    assert "el probe no devolvió códigos públicos. no se habilita confirmación de override" in DASH
    assert 'name="confirm_override" value="yes"' in DASH
    assert "no fuerza high" in DASH


def test_override_write_requires_explicit_checkbox_and_only_calls_v036_rpc():
    start = DASH.index("async function overrideterm")
    end = DASH.index("async function overridespage", start)
    fn = DASH[start:end]
    assert "confirm_override" in fn
    assert re.search(r'confirm_override[^\n]+!==\s*"yes"', fn)
    assert "dashboard_set_fasecolda_search_term_override" in fn
    assert re.search(r'p_action\s*:\s*"confirm"', fn)
    assert "fasecolda_match_lot" not in fn
    assert "lot_fasecolda_matches" not in fn


def test_clear_is_explicit_and_reversible():
    assert "/overrides" in DASH
    assert 'name="confirm_clear" value="yes"' in DASH
    start = DASH.index("async function clearoverride")
    fn = DASH[start:]
    assert "dashboard_set_fasecolda_search_term_override" in fn
    assert re.search(r'p_action\s*:\s*"clear"', fn)


def test_ui_repeats_search_term_guardrails():
    assert "fasecolda_search_probe_not_match" in DASH
    assert "manual_fasecolda_search_term_not_match" in DASH
    assert "cambia únicamente el término de búsqueda" in DASH
