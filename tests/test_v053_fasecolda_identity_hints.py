from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PY_HINTS = (ROOT / "src/superbid_collector/identity_hints.py").read_text(encoding="utf-8")
PARSER = (ROOT / "src/superbid_collector/parsers.py").read_text(encoding="utf-8")
EDGE_HINTS = (ROOT / "supabase/functions/superbid-fasecolda-candidate-cockpit/identity_hints.ts").read_text(encoding="utf-8")
COCKPIT = (ROOT / "supabase/functions/superbid-fasecolda-candidate-cockpit/index.ts").read_text(encoding="utf-8")


def rpc_names(source: str) -> set[str]:
    return set(re.findall(r"/rest/v1/rpc/([a-z0-9_]+)", source.lower()))


def version_tuple(text: str, pattern: str) -> tuple[int, int, int]:
    m = re.search(pattern, text)
    assert m
    return tuple(int(x) for x in m.group(1).split("."))


def test_python_and_edge_helpers_share_the_same_guardrail_dimensions_and_nominal_tolerance():
    guardrail = "AUTOMATED_IDENTITY_HINT_NOT_HUMAN_EVIDENCE_OR_MATCH"
    assert guardrail in PY_HINTS
    assert guardrail in EDGE_HINTS
    assert "IDENTITY_HINT_GUARDRAIL" in COCKPIT
    assert 'from "./identity_hints.ts"' in COCKPIT
    for token in ("engine_cc", "transmission", "drivetrain", "fuel"):
        assert token in PY_HINTS
        assert token in EDGE_HINTS
    assert "ENGINE_CC_NOMINAL_TOLERANCE = 50" in PY_HINTS
    assert "ENGINE_CC_NOMINAL_TOLERANCE = 50" in EDGE_HINTS
    assert "NOMINAL_COMPATIBLE" in PY_HINTS
    assert "NOMINAL_COMPATIBLE" in EDGE_HINTS
    assert "COMPATIBLE ±50 CC" in COCKPIT


def test_existing_html_parser_reuses_canonical_cc_regex_without_persisting_new_hints():
    assert "from .identity_hints import ENGINE_CC_RE" in PARSER
    assert "cc = first_match(ENGINE_CC_RE, vehicle_text)" in PARSER
    assert "CC_RE =" not in PARSER
    assert "identity_hints" not in PARSER.split("evidence={", 1)[-1]


def test_edge_hint_helper_is_pure_and_has_no_data_or_business_authority():
    lower = EDGE_HINTS.lower()
    for forbidden in (
        "fetch(",
        "deno.env",
        "/rest/v1/",
        "dashboard_",
        "service_role",
        "final_decision",
        "max_bid",
        "roi",
        "insert",
        "update ",
        "delete ",
    ):
        assert forbidden not in lower


def test_hints_are_visible_but_explicitly_not_evidence_or_ranking():
    lower = COCKPIT.lower()
    assert 'from "./identity_hints.ts"' in COCKPIT
    assert "pistas automáticas" in lower
    assert "read-only" in lower
    assert "no se guardan como evidencia" in lower
    assert "no se copian a estos campos" in lower
    assert "las pistas tampoco crean un nuevo score" in lower
    assert "coincide, compatible o difiere no equivalen a match/conflict humano" in lower
    assert "compatible ±50 cc reconoce únicamente la diferencia habitual entre desplazamiento real y nominal" in lower
    assert "hint_score" not in lower
    assert "recommended_candidate" not in lower
    assert "auto_select" not in lower


def test_hints_do_not_enter_form_data_or_rpc_payload():
    lower = COCKPIT.lower()
    save = lower.split("async function save", 1)[1].split("async function clearresolution", 1)[0]
    assert "extractvehicleidentityhints" not in save
    assert "comparevehicleidentityhints" not in save
    assert "hintrows" not in save
    assert "identity_hint" not in save
    assert 'name="hint_' not in lower
    assert "p_dimensions:dimensions" in save
    assert "p_mark_reviewed:reviewed" in save


def test_candidate_selection_still_ignores_automatic_best_and_hint_outcomes():
    lower = COCKPIT.lower()
    selection = lower[lower.index("const requested="):lower.index("const selectedcandidate=")]
    assert "best_code" not in selection
    assert "best_score" not in selection
    assert "hint" not in selection
    assert "selected=candidatecodes.has(requested)" in selection
    assert "ningún código se elige automáticamente" in lower


def test_business_write_authority_did_not_expand_in_v053():
    assert rpc_names(COCKPIT) == {
        "dashboard_token_valid",
        "dashboard_save_fasecolda_candidate_resolution",
        "dashboard_clear_fasecolda_candidate_resolution_v52",
    }
    assert "<script" not in COCKPIT.lower()
    assert "HttpOnly; Secure; SameSite=Strict" in COCKPIT


def test_v053_adds_no_database_migration():
    migrations = list((ROOT / "supabase/migrations").glob("*v53*.sql"))
    assert migrations == []


def test_v053_package_version_contract_is_forward_compatible():
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    package = (ROOT / "src/superbid_collector/__init__.py").read_text(encoding="utf-8")
    pv = version_tuple(pyproject, r'version\s*=\s*"(\d+\.\d+\.\d+)"')
    iv = version_tuple(package, r'__version__\s*=\s*"(\d+\.\d+\.\d+)"')
    assert pv == iv
    assert pv >= (0, 53, 0)
