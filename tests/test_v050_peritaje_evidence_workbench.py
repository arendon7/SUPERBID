from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MIG = ROOT / "supabase/migrations/20260826010000_peritaje_evidence_workbench_v50.sql"
WB = ROOT / "supabase/functions/superbid-peritaje-evidence-workbench/index.ts"
READY = ROOT / "supabase/functions/superbid-readiness-dashboard/index.ts"


def sql() -> str:
    return MIG.read_text(encoding="utf-8")


def wb() -> str:
    return WB.read_text(encoding="utf-8")


def rpc_names(source: str) -> set[str]:
    return set(re.findall(r"/rest/v1/rpc/([a-z0-9_]+)", source.lower()))


def test_v050_evidence_state_is_private_and_auditable():
    s = sql()
    assert "create table if not exists public.lot_peritaje_evidence_reviews" in s
    assert "create table if not exists public.lot_peritaje_evidence_review_history" in s
    assert "enable row level security" in s
    assert "revoke all on public.lot_peritaje_evidence_reviews,public.lot_peritaje_evidence_review_history from public,anon,authenticated" in s
    assert "MANUAL_PERITAJE_EVIDENCE_NOT_AUTOMATED_DIAGNOSIS_OR_BUY_SIGNAL" in s


def test_reviewed_requires_all_eight_dimensions_and_evidence_notes():
    s = sql()
    for dim in ("mechanical", "transmission", "body", "safety", "electrical", "tires", "documentation", "missing_parts"):
        assert f"'{dim}'" in s
    assert "reviewed evidence requires risk and note >=10 chars for dimension" in s
    assert "reviewed evidence requires all eight dimensions complete" in s
    assert "NOT_EVALUABLE" in s
    assert "unknown peritaje evidence dimension" in s


def test_reviewed_requires_valid_pdf_and_repair_range_basis():
    s = sql()
    assert "kind='PERITAJE' and url=p_source_attachment_url" in s
    assert "reviewed evidence requires source peritaje url" in s
    assert "reviewed evidence requires low, base and high repair estimates" in s
    assert "repair estimates must satisfy low <= base <= high" in s
    assert "reviewed evidence requires repair basis note of at least 20 characters" in s


def test_canonical_review_cannot_diverge_from_v050_evidence():
    s = sql()
    assert "create or replace function public.enforce_peritaje_evidence_review_gate_v50" in s
    assert "v0.50 evidence workbench is required before peritaje REVIEWED" in s
    assert "reviewed peritaje must match current v0.50 evidence record" in s
    assert "create trigger trg_peritaje_evidence_review_gate_v50" in s
    assert "before insert or update on public.lot_peritaje_reviews" in s


def test_new_rpc_has_no_cost_or_buy_authority():
    s = sql()
    rpc = s.split("create or replace function public.dashboard_save_peritaje_evidence_review", 1)[1]
    rpc = rpc.split("revoke all on function public.dashboard_save_peritaje_evidence_review", 1)[0]
    assert "'diagnosis_generated',false" in rpc
    assert "'buy_signal',false" in rpc
    assert "'cost_fields_modified',false" in rpc
    assert "'economic_fields_modified',false" in rpc
    for forbidden in (
        "dashboard_transfer_peritaje_repair_to_costs",
        "lot_cost_overrides",
        "final_decision=",
        "max_bid_market_validated_cop=",
        "expected_roi_current_pct=",
        "market_manual_evidence",
        "lot_fasecolda_matches",
    ):
        assert forbidden not in rpc


def test_workbench_is_case_preserving_private_and_narrow():
    t = wb()
    assert r"^\d{5,12}$" in t
    assert "function safeLot" in t
    assert "function lotFromPath" in t
    assert 'name="lot" value=' in t
    assert "HttpOnly; Secure; SameSite=Strict" in t
    assert rpc_names(t) == {"dashboard_token_valid", "dashboard_save_peritaje_evidence_review"}
    for token in ("return_to", "redirect_uri", "redirect_url"):
        assert token not in t.lower()


def test_workbench_keeps_pdf_and_human_evidence_in_same_case_flow():
    t = wb()
    assert "Peritaje Evidence Workbench" in t
    assert "sandbox=\"allow-same-origin\"" in t
    assert "NOT_EVALUABLE" in t
    assert "8 dimensiones de evidencia" in t
    assert "Fundamento del rango de reparación" in t
    assert "dashboard_peritaje_evidence_workbench_v50" in t
    assert "lot_peritaje_evidence_review_history" in t
    assert "superbid-readiness-dashboard?lot=${encodeURIComponent(external)}" in t
    assert "superbid-cost-governance-dashboard/lots/" not in t


def test_readiness_routes_review_peritaje_to_v050_exact_workbench():
    t = READY.read_text(encoding="utf-8")
    assert 'a==="REVIEW_PERITAJE"' in t
    assert "superbid-peritaje-evidence-workbench/lots/${id}" in t
    assert "PERITAJE_NOT_REVIEWED" in t


def test_package_version_is_v050():
    assert 'version = "0.50.0"' in (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert '__version__ = "0.50.0"' in (ROOT / "src/superbid_collector/__init__.py").read_text(encoding="utf-8")
