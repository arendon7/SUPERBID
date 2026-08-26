from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FUNCTION_DIR = ROOT / "supabase/functions/superbid-fasecolda-candidate-cockpit"
COCKPIT = (FUNCTION_DIR / "index.ts").read_text(encoding="utf-8")
HELPER = (FUNCTION_DIR / "candidate_discriminators.ts").read_text(encoding="utf-8")
DENO_TEST = (FUNCTION_DIR / "candidate_discriminators_test.ts").read_text(encoding="utf-8")


def rpc_names(source: str) -> set[str]:
    return set(re.findall(r"/rest/v1/rpc/([a-z0-9_]+)", source.lower()))


def version_tuple(text: str, pattern: str) -> tuple[int, int, int]:
    match = re.search(pattern, text)
    assert match
    return tuple(int(part) for part in match.group(1).split("."))


def test_v055_helper_is_pure_bounded_and_reuses_identity_extraction():
    assert 'CANDIDATE_DISCRIMINATOR_GUARDRAIL = "CANDIDATE_DISCRIMINATOR_MAP_NOT_EVIDENCE_OR_RECOMMENDATION"' in HELPER
    assert "MAX_LITERAL_DELTA_TOKENS = 12" in HELPER
    assert 'from "./identity_hints.ts"' in HELPER
    assert "extractVehicleIdentityHints" in HELPER
    assert "known.size > 1" in HELPER
    assert ".slice(0, MAX_LITERAL_DELTA_TOKENS)" in HELPER
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
        "winner",
        "recommendedcandidate",
        "recommended_candidate",
        "auto_select",
        "hint_score",
        "final_decision",
        "max_bid",
        "roi",
    ):
        assert forbidden not in lower


def test_v055_map_marks_duplicates_without_resolving_them():
    lower = HELPER.lower()
    assert "duplicatedescriptiongroupsize" in lower
    assert "indistinguishablebydescription" in lower
    assert "hasindistinguishabledescriptions" in lower
    assert "descriptioncounts" in lower
    assert "groupsize > 1" in lower
    assert "descripción indistinguible" in COCKPIT.lower()
    assert "confirmación exacta bloqueada por el gate v0.52" in COCKPIT.lower()


def test_v055_cockpit_renders_read_only_discriminator_map_outside_evidence_payload():
    lower = COCKPIT.lower()
    assert 'from "./candidate_discriminators.ts"' in COCKPIT
    assert "mapa de diferencias actuales" in lower
    assert "deltas literales frente al conjunto" in lower
    assert "candidate_discriminator_map_not_evidence_or_recommendation" in lower
    assert "${selectedreadonly}${form}" in lower
    assert 'name="disc_' not in lower
    assert 'name="token_' not in lower
    save = lower[lower.index("async function save"):lower.index("async function clearresolution")]
    for forbidden in (
        "buildcandidatediscriminatormap",
        "selectedreadonly",
        "literaldeltatokens",
        "structureddiscriminators",
        "candidate_discriminator",
    ):
        assert forbidden not in save
    assert "p_dimensions:dimensions" in save
    assert "p_mark_reviewed:reviewed" in save


def test_v055_candidate_selection_invariant_is_unchanged():
    lower = COCKPIT.lower()
    start = lower.index("const requested=")
    end = lower.index("const selectedcandidate=", start)
    selection = lower[start:end]
    assert "automatic_best" not in selection
    assert "best_code" not in selection
    assert "discriminator" not in selection
    assert "hint" not in selection
    assert "selected=candidatecodes.has(requested)" in selection
    assert "ningún código se elige automáticamente" in lower


def test_v055_business_write_authority_does_not_expand():
    assert rpc_names(COCKPIT) == {
        "dashboard_token_valid",
        "dashboard_save_fasecolda_candidate_resolution",
        "dashboard_clear_fasecolda_candidate_resolution_v52",
    }
    assert "HttpOnly; Secure; SameSite=Strict" in COCKPIT
    assert "<script" not in COCKPIT.lower()


def test_v055_no_new_data_query_is_needed_for_discriminator_map():
    lower = COCKPIT.lower()
    detail = lower[lower.index("async function detail"):lower.index("async function save")]
    assert "buildcandidatediscriminatormap((candidates || []).map" in detail
    assert "candidate_discriminator" not in "\n".join(
        line for line in detail.splitlines() if "/rest/v1/" in line
    )


def test_v055_deno_tests_cover_unknowns_deltas_duplicates_order_and_no_recommendation():
    assert DENO_TEST.count("Deno.test(") >= 7
    for phrase in (
        "two distinct known values",
        "unknown structured values",
        "trim and use tokens",
        "indistinguishable",
        "candidate order",
        "deterministic and bounded",
        "fuel only discriminates",
    ):
        assert phrase in DENO_TEST.lower()
    assert '!("winner" in map)' in DENO_TEST
    assert '!("recommendedCandidate" in map)' in DENO_TEST


def test_v055_adds_no_database_migration():
    assert list((ROOT / "supabase/migrations").glob("*v55*.sql")) == []


def test_v055_package_version_is_exact_and_consistent():
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    package = (ROOT / "src/superbid_collector/__init__.py").read_text(encoding="utf-8")
    pv = version_tuple(pyproject, r'version\s*=\s*"(\d+\.\d+\.\d+)"')
    iv = version_tuple(package, r'__version__\s*=\s*"(\d+\.\d+\.\d+)"')
    assert pv == iv == (0, 55, 0)


def test_v055_does_not_gain_economic_or_purchase_authority():
    combined = (COCKPIT + "\n" + HELPER).lower()
    for forbidden in (
        "max_bid_market_validated_cop",
        "recommended_bid",
        "buy_signal=true",
        "final_decision=",
        "roi =",
        "roi=",
    ):
        assert forbidden not in combined
    assert "manual_fasecolda_candidate_evidence_not_automatic_match_or_buy_signal" in combined
    assert "candidate_discriminator_map_not_evidence_or_recommendation" in combined
