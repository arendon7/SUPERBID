from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CI = ROOT / ".github/workflows/ci.yml"
CHECK = ROOT / "scripts/check_edge_functions.sh"
FUNCTIONS = ROOT / "supabase/functions"


def _version_tuple(text: str, pattern: str) -> tuple[int, int, int]:
    match = re.search(pattern, text)
    assert match, f"version pattern not found: {pattern}"
    return tuple(int(part) for part in match.group(1).split("."))


def test_ci_has_independent_edge_build_job_with_pinned_deno_toolchain():
    workflow = CI.read_text(encoding="utf-8")
    assert "edge-build:" in workflow
    assert "timeout-minutes: 10" in workflow
    assert "permissions:\n  contents: read" in workflow
    assert "denoland/setup-deno@22d081ff2d3a40755e97629de92e3bcbfa7cf2ed" in workflow
    assert 'deno-version: "2.9.5"' in workflow
    assert "bash scripts/check_edge_functions.sh" in workflow
    assert "pytest -q" in workflow


def test_edge_gate_discovers_every_function_instead_of_using_a_frozen_allowlist():
    script = CHECK.read_text(encoding="utf-8")
    assert "set -euo pipefail" in script
    assert 'find "$FUNCTIONS_DIR" -mindepth 2 -maxdepth 2 -type f -name index.ts' in script
    assert 'find "$FUNCTIONS_DIR" -mindepth 1 -maxdepth 1 -type d' in script
    assert "No Supabase Edge Function index.ts entrypoints were discovered" in script
    assert "Every immediate Supabase function directory must contain exactly one index.ts entrypoint" in script
    assert 'deno check --quiet "$entrypoint"' in script
    assert "::error file=$relative::Deno type/syntax check failed" in script


def test_every_current_supabase_function_directory_has_one_index_entrypoint():
    function_dirs = sorted(path for path in FUNCTIONS.iterdir() if path.is_dir())
    entrypoints = sorted(FUNCTIONS.glob("*/index.ts"))
    assert function_dirs
    assert len(function_dirs) == len(entrypoints)
    assert {path.name for path in function_dirs} == {path.parent.name for path in entrypoints}
    assert len(entrypoints) >= 13


def test_v051_is_release_engineering_only_and_does_not_add_business_authority():
    workflow = CI.read_text(encoding="utf-8")
    script = CHECK.read_text(encoding="utf-8")
    combined = (workflow + "\n" + script).lower()
    for forbidden in (
        "supabase db push",
        "supabase migration",
        "supabase functions deploy",
        "dashboard_save_",
        "service_role_key",
        "final_decision",
        "max_bid_market_validated_cop",
    ):
        assert forbidden not in combined


def test_v051_package_version_contract_is_forward_compatible():
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    package = (ROOT / "src/superbid_collector/__init__.py").read_text(encoding="utf-8")
    project_version = _version_tuple(pyproject, r'version\s*=\s*"(\d+\.\d+\.\d+)"')
    package_version = _version_tuple(package, r'__version__\s*=\s*"(\d+\.\d+\.\d+)"')
    assert project_version == package_version
    assert project_version >= (0, 51, 0)
