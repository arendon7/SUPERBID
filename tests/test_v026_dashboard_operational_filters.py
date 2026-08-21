from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DASH = (ROOT / "supabase/functions/superbid-dashboard/index.ts").read_text(encoding="utf-8").lower()


def test_home_reads_operational_queue_not_legacy_lot_view():
    start = DASH.index("async function operationallots")
    end = DASH.index("function option", start)
    fn = DASH[start:end]
    assert "dashboard_operational_queue" in fn
    assert "operational_rank.asc" in fn
    assert "review_score.desc" in fn
    assert "closes_at.asc" in fn


def test_dashboard_exposes_state_pressure_and_closing_filters():
    assert 'name="state"' in DASH
    assert 'name="pressure"' in DASH
    assert 'name="closing"' in DASH
    assert "closing_2h" in DASH
    assert "closing_6h" in DASH
    assert "closing_24h" in DASH
    assert "presión alta" in DASH


def test_dashboard_visually_separates_operational_rank_from_review_score():
    assert "prioridad operativa" in DASH
    assert "operational_rank" in DASH
    assert "operational_reason" in DASH
    assert "review_score" in DASH
    assert "presión y urgencia son señales de atención, no decisiones económicas" in DASH


def test_operational_ui_does_not_mutate_economic_decision_fields():
    start = DASH.index("async function operationallots")
    end = DASH.index("const input", start)
    home = DASH[start:end]
    assert "max_bid_market_validated_cop" not in home
    assert "final_decision" not in home
    assert "dashboard_save_lot_costs" not in home
    assert "no modifica score, puja máxima ni decisión final" in home


def test_v026_remains_server_rendered():
    assert "<script" not in DASH
    assert "deno.serve" in DASH
    assert 'method="get"' in DASH
