from superbid_collector.canonical import canonical_offer_url
def test_canonical_absolute():
 d={"url":"https://www.superbid.com.co/oferta/abc-1234567"};assert canonical_offer_url(d,"x","1234567")==d["url"]
def test_canonical_relative():assert canonical_offer_url({"detail_url":"/oferta/abc-1234567"},"x","1234567")=="https://www.superbid.com.co/oferta/abc-1234567"
def test_canonical_slug():assert canonical_offer_url({"slug":"abc-1234567"},"x","1234567")=="https://www.superbid.com.co/oferta/abc-1234567"
