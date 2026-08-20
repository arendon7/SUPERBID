# v0.13 — Direct public API experiment

## Goal
Determine whether a monitored public Superbid lot can be refreshed directly through the public `offer-query.superbid.net/seo/offers/` endpoint without Chromium, browser cookies, authentication, CAPTCHA bypass or an opaque `filter` parameter.

## Method
The existing sanitized Chromium probe observes the public `/seo/offers/` request, keeps only a strict allow-list of public routing values (`portalId`, `locale`, `requestOrigin`, `timeZoneId`, `urlSeo`, pagination/search values), then creates a completely separate `httpx` client with no browser cookies and replays the read-only endpoint without `filter`.

## Safety
The report never persists authentication/session values, bidder/buyer identities, reserve prices, cookies, signatures, opaque filters or raw JSON responses.

## Decision rule
- If the stateless replay returns HTTP 200 and recognizes the expected lot, routine monitored-lot refresh can move to direct HTTP in a subsequent commit.
- Chromium remains the fallback for discovery, attachment/peritaje inspection and contract validation.
