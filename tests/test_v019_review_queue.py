from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SQL = (ROOT / "supabase/migrations/20260821043826_review_queue_v19.sql").read_text(encoding="utf-8")
LOW = SQL.lower()


def test_review_queue_never_emits_buy_decisions():
    assert "'comprar'" not in LOW
    assert "'vigilar'" not in LOW
    assert "'no_pujar'" not in LOW
    assert "review_now" in LOW
    assert "review_soon" in LOW


def test_review_queue_requires_high_fasecolda_before_priority_state():
    high_pos = LOW.index("when fasecolda_status<>'high' then 'blocked_valuation'")
    review_pos = LOW.index("when review_score>=65 then 'review_now'")
    assert high_pos < review_pos


def test_review_queue_requires_positive_preliminary_headroom():
    assert "preliminary_headroom_before_fixed_costs_cop<=0" in LOW
    assert "'no_headroom'" in LOW


def test_peritaje_is_priority_boost_not_safety_guarantee():
    assert "case when peritaje_count>0 then 25 else 0 end" in LOW
    assert "'needs_market_validation',true" in LOW
    assert "'needs_cost_review',true" in LOW


def test_review_view_is_backend_only():
    assert "revoke all on public.lot_review_queue_current from public,anon,authenticated" in LOW
    assert "grant select on public.lot_review_queue_current to service_role" in LOW
