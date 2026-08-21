from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
MIG = (ROOT / "supabase/migrations/20260821143358_operational_pressure_queue_v25.sql").read_text(encoding="utf-8").lower()
API = (ROOT / "supabase/functions/superbid-read-api/index.ts").read_text(encoding="utf-8").lower()


def test_operational_queue_is_backend_only():
    assert "create or replace view public.dashboard_operational_queue" in MIG
    assert "revoke all on public.dashboard_operational_queue from public,anon,authenticated" in MIG
    assert "grant select on public.dashboard_operational_queue to service_role" in MIG


def test_operational_queue_is_explicitly_not_buy_signal():
    assert "operational_triage_not_buy_signal" in MIG
    assert "operational_rank" in MIG
    assert "operational_reason" in MIG
    assert "closing_bucket" in MIG
    assert "pressure_level" in MIG


def test_private_api_exposes_filtered_operational_queue():
    assert 'p==="/operational-queue"' in API
    assert "dashboard_operational_queue" in API
    assert "pressure_level=eq." in API
    assert "closing_bucket=eq." in API
    assert "review_state=eq." in API
    assert "operational_rank.asc" in API
    match = re.search(r'version:"(\d+)\.(\d+)"', API)
    assert match is not None
    assert tuple(map(int, match.groups())) >= (0, 25)


def test_old_review_queue_remains_available():
    assert 'p==="/review-queue"' in API
    assert "dashboard_lot_current" in API
