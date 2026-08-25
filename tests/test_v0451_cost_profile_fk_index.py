from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MIGRATION = ROOT / "supabase/migrations/20260825150000_cost_profile_fk_index_v451.sql"
V45 = ROOT / "supabase/migrations/20260825040000_cost_assumption_governance_v45.sql"


def test_v0451_release_artifact_remains_identifiable_after_later_versions():
    # Patch-release tests protect the migration and v0.45.1 contract rather
    # than permanently pinning the repository's global package version.
    assert MIGRATION.exists()
    sql = MIGRATION.read_text(encoding="utf-8")
    assert "ix_lot_cost_profile_application_profile" in sql
    assert "profile_version_id" in sql


def test_v0451_adds_covering_index_for_profile_version_fk_only():
    sql = MIGRATION.read_text(encoding="utf-8")
    assert "create index if not exists ix_lot_cost_profile_application_profile" in sql
    assert "on public.lot_cost_profile_application_history(profile_version_id)" in sql
    lowered = sql.lower()
    for forbidden in ("insert into", "update public.", "delete from", "alter table", "create or replace function", "create or replace view"):
        assert forbidden not in lowered


def test_v0451_preserves_v045_cost_governance_contract():
    sql = V45.read_text(encoding="utf-8")
    assert "profile_version_id bigint not null references public.cost_assumption_profile_versions(id) on delete restrict" in sql
    assert "COST_PROFILE_ASSUMPTION_NOT_LOT_COST" in sql
    assert "COST_PROFILE_APPLICATION_REQUIRES_LOT_CONFIRMATION" in sql
    assert "COST_GOVERNANCE_NOT_BUY_SIGNAL" in sql
    assert "dashboard_cost_governance_queue_v45" in sql
