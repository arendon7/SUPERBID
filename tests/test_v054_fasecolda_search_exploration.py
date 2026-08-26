from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FUNCTION_DIR = ROOT / "supabase/functions/superbid-fasecolda-search-dashboard"
DASH = (FUNCTION_DIR / "index.ts").read_text(encoding="utf-8")
HELPER = (FUNCTION_DIR / "search_exploration.ts").read_text(encoding="utf-8")
DENO_TEST = (FUNCTION_DIR / "search_exploration_test.ts").read_text(encoding="utf-8")
EDGE_GATE = (ROOT / "scripts/check_edge_functions.sh").read_text(encoding="utf-8")


def rpc_names(source: str) -> set[str]:
    return set(re.findall(r"/rest/v1/rpc/([a-z0-9_]+)", source.lower()))


def function_body(source: str, start_name: str, end_name: str) -> str:
    lower = source.lower()
    start = lower.index(f"async function {start_name.lower()}")
    end = lower.index(f"async function {end_name.lower()}", start)
    return source[start:end]


def version_tuple(text: str, pattern: str) -> tuple[int, int, int]:
    match = re.search(pattern, text)
    assert match
    return tuple(int(part) for part in match.group(1).split("."))


def test_v054_helper_has_bounded_fail_closed_contract():
    assert 'SEARCH_EXPLORATION_GUARDRAIL = "AUTOMATED_SEARCH_VARIANT_NOT_OVERRIDE_OR_MATCH"' in HELPER
    assert "MAX_SEARCH_VARIANTS = 4" in HELPER
    for state in ("EXPLORABLE", "IDENTITY_INPUT_REVIEW", "MISSING_YEAR"):
        assert state in HELPER
    for generic in ("COMBO", "AUTOMOVIL", "CAMION", "VOLQUETA", "TRACTOCAMION"):
        assert f'"{generic}"' in HELPER
    assert "out.slice(0, MAX_SEARCH_VARIANTS)" in HELPER
    assert "preservesBrand" in HELPER


def test_v054_helper_is_pure_and_cannot_write_or_call_external_services():
    lower = HELPER.lower()
    for forbidden in (
        "fetch(",
        "deno.env",
        "/rest/v1/",
        "dashboard_",
        "service_role",
        "insert ",
        "update ",
        "delete ",
        "max_bid",
        "roi",
        "final_decision",
        "buy_signal",
    ):
        assert forbidden not in lower


def test_matrix_uses_only_existing_auth_probe_and_override_rpcs():
    assert rpc_names(DASH) == {
        "dashboard_token_valid",
        "dashboard_probe_fasecolda_search_term",
        "dashboard_set_fasecolda_search_term_override",
    }
    assert "<script" not in DASH.lower()
    assert "HttpOnly; Secure; SameSite=Strict" in DASH


def test_explore_is_sequential_read_only_and_has_no_winner_logic():
    body = function_body(DASH, "explore", "singleProbe")
    lower = body.lower()
    assert 'ex.disposition !== "explorable"' in lower
    assert "no se ejecutó ningún probe" in lower
    assert "for (const variant of ex.variants)" in body
    assert "await runProbe(lot, variant)" in body
    assert "promise.all" not in lower
    assert "dashboard_set_fasecolda_search_term_override" not in lower
    for forbidden in ("best_term", "recommended_term", "winner", "auto_select", "bulk"):
        assert forbidden not in lower
    assert "no es un score de calidad" in lower
    assert "no elige ningún término ganador" in lower


def test_run_probe_has_read_only_probe_authority_only():
    body = DASH[DASH.index("async function runProbe"):DASH.index("function overrideForm")]
    assert rpc_names(body) == {"dashboard_probe_fasecolda_search_term"}
    lower = body.lower()
    assert "lot_fasecolda" not in lower
    assert "insert" not in lower
    assert "update" not in lower
    assert "delete" not in lower


def test_manual_probe_revalidates_case_before_external_probe():
    body = function_body(DASH, "singleProbe", "overrideTerm")
    lower = body.lower()
    disposition_at = lower.index('ex.disposition !== "explorable"')
    rpc_at = lower.index("dashboard_probe_fasecolda_search_term")
    assert disposition_at < rpc_at
    assert "no se llamó a fasecolda" in lower
    assert "loadcase(lot)" in lower


def test_override_is_single_term_explicit_human_action_and_fail_closed():
    body = function_body(DASH, "overrideTerm", "overridesPage")
    lower = body.lower()
    disposition_at = lower.index('ex.disposition !== "explorable"')
    rpc_at = lower.index("dashboard_set_fasecolda_search_term_override")
    assert disposition_at < rpc_at
    assert "confirm_override" in lower
    assert '!== "yes"' in lower
    assert "note.length < 10" in lower
    assert 'p_action: "confirm"' in lower
    assert "fasecolda_match_lot" not in lower
    assert "bulk" not in lower
    assert "all_terms" not in lower
    assert 'minlength="10"' in DASH.lower()
    assert 'name="confirm_override" value="yes" required' in DASH.lower()


def test_blocked_cases_do_not_render_manual_probe_form():
    lower = DASH.lower()
    assert 'const manualprobe = ex.disposition === "explorable"' in lower
    assert "corregir identidad antes de buscar" in lower
    assert "falta año de modelo" in lower


def test_v054_extends_edge_gate_with_deno_unit_tests():
    assert "find \"$FUNCTIONS_DIR\" -mindepth 2 -type f -name '*_test.ts'" in EDGE_GATE
    assert 'deno test --quiet "$test_file"' in EDGE_GATE
    assert "Deno unit tests failed" in EDGE_GATE
    assert DENO_TEST.count("Deno.test(") >= 7
    assert "COMBO:" in DENO_TEST
    assert "TOYOTA COROLLA CROSS" in DENO_TEST
    assert "MAX_SEARCH_VARIANTS" in DENO_TEST


def test_v054_adds_no_database_migration():
    assert list((ROOT / "supabase/migrations").glob("*v54*.sql")) == []


def test_v054_package_version_contract_is_forward_compatible():
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    package = (ROOT / "src/superbid_collector/__init__.py").read_text(encoding="utf-8")
    pv = version_tuple(pyproject, r'version\s*=\s*"(\d+\.\d+\.\d+)"')
    iv = version_tuple(package, r'__version__\s*=\s*"(\d+\.\d+\.\d+)"')
    assert pv == iv
    assert pv >= (0, 54, 0)


def test_v054_does_not_gain_economic_or_purchase_authority():
    combined = (DASH + "\n" + HELPER).lower()
    for forbidden in (
        "final_decision",
        "max_bid_market_validated_cop",
        "recommended_bid",
        "buy_signal=true",
        "roi =",
        "roi=",
    ):
        assert forbidden not in combined
    assert "automated_search_variant_not_override_or_match" in combined
    assert "case_context_routing_not_buy_signal" in combined
