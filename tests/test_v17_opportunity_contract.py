from pathlib import Path


MIGRATION = Path("supabase/migrations/20260820223413_preliminary_opportunity_engine_v17.sql")


def test_preliminary_engine_never_claims_final_buy_recommendation():
    sql = MIGRATION.read_text(encoding="utf-8").lower()
    assert "final_buy_recommendation_available" in sql
    assert "false as final_buy_recommendation_available" in sql
    assert "configure_costs" in sql
    assert "market_validation_pending" in sql


def test_commission_plus_vat_formula_is_explicit():
    sql = MIGRATION.read_text(encoding="utf-8").lower()
    assert "commission_percent_public" in sql
    assert "vat_on_commission_pct" in sql
    assert "1 + (b.commission_percent_public/100.0)*(1+p.vat_on_commission_pct)" in sql


def test_unknown_fixed_costs_are_null_not_invented():
    sql = MIGRATION.read_text(encoding="utf-8").lower()
    for name in (
        "transfer_cop",
        "taxes_soat_cop",
        "transport_cop",
        "repair_cop",
        "detailing_cop",
        "financing_cop",
        "admin_fee_cop",
        "contingency_cop",
    ):
        assert name in sql
    assert "null,null,null,null,null,null,null,null" in sql
    assert "fixed_costs_complete" in sql


def test_only_high_fasecolda_can_feed_preliminary_resale():
    sql = MIGRATION.read_text(encoding="utf-8")
    assert "fasecolda_status='HIGH'" in sql
    assert "fasecolda_resale_factor" in sql
    assert "0.90" in sql


def test_sale_confirmation_is_not_modified_by_opportunity_engine():
    sql = MIGRATION.read_text(encoding="utf-8").lower()
    assert "sale_price_confirmed" not in sql
    assert "reservedprice" not in sql
    assert "winnerbid" not in sql
