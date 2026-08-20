from superbid_collector.bid_history import extract_bid_history
def test_extract_bid_history_without_bidder_identity():
    rows=extract_bid_history({"bid_history":[{"amount":10000000,"created_at":"2026-08-20 10:00","user":"abc"},{"amount":10500000,"created_at":"2026-08-20 10:02","user":"xyz"}]});assert [x["amount_cop"] for x in rows]==[10000000,10500000];assert all("user" not in x for x in rows)
