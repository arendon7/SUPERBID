from superbid_collector.valuation import CostProfile,estimate_market,calculate_opportunity,total_cost_for_bid
def test_market_and_max_bid():
 m=estimate_market([68000000,70000000,72000000,67000000,71000000],fasecolda_cop=69000000,quick_sale_discount_pct=.05);assert m.comparable_count==5 and m.conservative_resale_cop is not None;p=CostProfile(buyer_commission_pct=.06,vat_on_commission_pct=.19,transfer_cop=900000,transport_cop=600000,repair_cop=2500000,contingency_cop=1000000,target_profit_pct_of_resale=.12);o=calculate_opportunity(m,45000000,p);assert o.max_bid_cop>0 and o.expected_total_cost_cop==total_cost_for_bid(45000000,p) and o.expected_profit_cop==o.conservative_resale_cop-o.expected_total_cost_cop and o.score>=0
def test_no_market_data():
 o=calculate_opportunity(estimate_market([]),10000000,CostProfile());assert o.decision=="SIN_DATOS" and o.max_bid_cop is None
