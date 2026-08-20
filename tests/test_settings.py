from superbid_collector.storage import Store
from superbid_collector.settings import get_cost_profile,set_cost_profile
from superbid_collector.valuation import CostProfile
def test_settings_roundtrip(tmp_path):
 s=Store(tmp_path/"s.db");s.init();set_cost_profile(s.conn,CostProfile(buyer_commission_pct=.07,repair_cop=123456));g=get_cost_profile(s.conn);assert g.buyer_commission_pct==.07 and g.repair_cop==123456
