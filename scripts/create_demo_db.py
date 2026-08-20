from pathlib import Path
from superbid_collector.storage import Store
from superbid_collector.models import LotObservation, Outcome
from superbid_collector.market_storage import add_comparable
from superbid_collector.storage_extensions import save_attachments, save_bid_history
from superbid_collector.settings import set_cost_profile
from superbid_collector.valuation import CostProfile

db = Path("demo_superbid.db")
if db.exists():
    db.unlink()
s = Store(db)
s.init()

samples = [
    ("4972833","MAZDA 3 TOURING 2.0 MOD. 2017","MAZDA",2017,"Yumbo",48_500_000,"2026-08-20 16:45",True),
    ("4973043","KIA RIO ZENITH MOD. 2020","KIA",2020,"Cali",52_000_000,"2026-08-20 17:10",False),
    ("4970123","HINO XZU640L HKMLN3 MOD. 2018","HINO",2018,"Girardota",79_000_000,"2026-08-21 11:00",True),
]
for lotid,title,brand,year,city,bid,close,report in samples:
    obs=LotObservation(
        external_lot_id=lotid,url=f"https://www.superbid.com.co/oferta/demo-{lotid}",
        title=title,brand=brand,model_year=year,city=city,
        initial_bid_cop=int(bid*.7),displayed_price_cop=bid,
        closes_at_text=close,bid_count=8,outcome=Outcome.ACTIVE
    )
    lid=s.save(obs)
    for i,p in enumerate([int(bid*1.30),int(bid*1.34),int(bid*1.38),int(bid*1.41),int(bid*1.44)]):
        add_comparable(s.conn,lot_id=lid,source="demo_market",external_id=f"{lotid}-{i}",asking_price_cop=p)
    if report:
        save_attachments(s.conn,lid,[{"name":"Informe de peritaje","url":"https://example.com/peritaje.pdf","kind":"PERITAJE","source":"demo"}])
    save_bid_history(s.conn,lid,[{"sequence_no":1,"amount_cop":int(bid*.85),"bid_at_text":"10:00"},{"sequence_no":2,"amount_cop":bid,"bid_at_text":"11:00"}])

set_cost_profile(s.conn, CostProfile(
    buyer_commission_pct=.06, vat_on_commission_pct=.19,
    transfer_cop=900_000, transport_cop=600_000,
    repair_cop=1_500_000, admin_fee_cop=300_000,
    contingency_cop=1_000_000, target_profit_pct_of_resale=.12
))
print(db.resolve())
