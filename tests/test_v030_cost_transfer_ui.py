from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
API = (ROOT / "supabase/functions/superbid-read-api/index.ts").read_text(encoding="utf-8").lower()
DASH = (ROOT / "supabase/functions/superbid-dashboard/index.ts").read_text(encoding="utf-8").lower()


def test_dashboard_requires_explicit_confirmation():
    assert "/peritaje-cost-transfer" in DASH
    assert 'name="confirm_transfer"' in DASH
    assert 'value="yes"' in DASH
    assert "debe confirmar explícitamente la transferencia" in DASH
    assert "manual_peritaje_cost_transfer_not_automatic" in DASH
    assert "transferir escenario a costos" in DASH


def test_transfer_handler_does_not_review_costs_or_touch_decision():
    start = DASH.index("async function transferperitajecost")
    end = DASH.index("async function savecosts", start)
    fn = DASH[start:end]
    assert "dashboard_transfer_peritaje_repair_to_costs" in fn
    assert "dashboard_save_lot_costs" not in fn
    assert "p_mark_reviewed" not in fn
    assert "max_bid_market_validated_cop" not in fn
    assert "final_decision" not in fn


def test_dashboard_exposes_cost_readiness_queue():
    assert "/superbid-dashboard/costos" in DASH
    assert "dashboard_cost_readiness_current" in DASH
    assert "preparación de costos" in DASH
    assert "repair_cost_source_status" in DASH


def test_read_api_v030_capability_remains_get_only():
    match = re.search(r'version:"(\d+)\.(\d+)"', API)
    assert match and tuple(map(int, match.groups())) >= (0, 30)
    assert 'req.method!=="get"' in API
    assert 'p==="/cost-readiness"' in API
    assert "dashboard_cost_readiness_current" in API


def test_v030_dashboard_remains_server_rendered():
    assert "<script" not in DASH
    assert "deno.serve" in DASH
