# SUPERBID v0.60.1 — Fasecolda Detail 403 Backoff

## Why this hotfix exists

v0.60 introduced reusable evidence for the public Fasecolda search endpoint and, when public codes exist, a second request to the public detail endpoint so SUPERBID can check model-year compatibility without creating a match or valuation.

Production transactional smoke after the v0.60 release exposed an operational failure mode: the search endpoint is reachable, but the detail endpoint currently rejects the tested code requests with HTTP 403.

Four distinct code-bearing terms were exercised against the live v0.60 RPC inside `BEGIN ... ROLLBACK`:

| Term | Search HTTP | Public codes | Detail HTTP | Payload valid |
| --- | ---: | ---: | ---: | --- |
| CHEVROLET BLAZER RS | 200 | 6 | 403 | false |
| CHEVROLET CAPTIVA PREMIER | 200 | 1 | 403 | false |
| NISSAN X TRAIL | 200 | 22 | 403 | false |
| VOLKSWAGEN T CROSS | 200 | 20 | 403 | false |

All four calls returned `buy_signal=false`. The transaction was rolled back and v0.60 current/history plus human-authority tables remained at zero.

The v0.60 fail-closed semantics correctly prevented 403 from becoming negative model-year evidence. However, `SUGGESTED_DETAIL_UNAVAILABLE` was still considered refreshable by the UI. A fresh persistent 403 could therefore be retried by every explicit batch execution, generating useless network calls and append-only history.

v0.60.1 closes that operational loop without increasing business authority.

## Contract

New SQL helper:

`fasecolda_detail_retry_class_v601(http_status, payload_valid)`

Classification:

- HTTP 200 + valid array payload -> `VALID`
- HTTP 200 + invalid/non-array payload -> `INVALID_NONRETRYABLE`
- HTTP 403 -> `FORBIDDEN_NONRETRYABLE`
- other non-transient 4xx -> `REJECTED_NONRETRYABLE`
- HTTP 408, 425, 429, 5xx, null/other unavailable -> `UNAVAILABLE_RETRYABLE`

New wrapper view:

`dashboard_fasecolda_search_evidence_queue_v601`

It does not replace or mutate v0.60 evidence. It wraps `dashboard_fasecolda_search_evidence_queue_v60` and adds v0.60.1 operational fields.

### Fresh evidence ordering

The queue evaluates evidence freshness before detail retry disposition.

Therefore:

1. no observation -> `SUGGESTED_EVIDENCE_MISSING`
2. observation older than 24 h -> `SUGGESTED_EVIDENCE_STALE`
3. fresh 403 -> `SUGGESTED_DETAIL_FORBIDDEN`
4. fresh invalid HTTP-200 payload -> `SUGGESTED_DETAIL_INVALID`
5. fresh other non-retryable 4xx -> `SUGGESTED_DETAIL_REJECTED`
6. fresh transient/unavailable detail -> `SUGGESTED_DETAIL_UNAVAILABLE`
7. only valid detail payload can reach year-compatible / no-year-compatible states

A fresh 403 therefore routes to `OPEN_HUMAN_SEARCH` and cannot be refreshed again. Once the existing 24-hour freshness window expires, the same evidence becomes `STALE` and is eligible for a new explicit refresh.

## Edge enforcement

The Search Evidence dashboard now reads the v0.60.1 wrapper and uses only these refreshable states:

- `SUGGESTED_EVIDENCE_MISSING`
- `SUGGESTED_EVIDENCE_STALE`
- `SUGGESTED_DETAIL_UNAVAILABLE`

The following are explicitly non-refreshable while fresh:

- `SUGGESTED_DETAIL_FORBIDDEN`
- `SUGGESTED_DETAIL_INVALID`
- `SUGGESTED_DETAIL_REJECTED`

This is enforced twice:

1. the button is not rendered;
2. the POST handler re-checks the state and returns HTTP 409 before calling the refresh RPC.

The bounded batch remains explicit POST-only, deduplicated by normalized term, sequential, and capped at six terms. Non-retryable fresh detail states are excluded from batch selection.

## Authority boundaries

v0.60.1 does not add an RPC and does not change the v0.60 refresh RPC.

The Search Evidence Edge function may call only:

- `dashboard_token_valid`
- `dashboard_refresh_fasecolda_search_term_evidence_v60`

The migration contains no business DML. It does not write:

- Fasecolda search-term overrides
- Fasecolda manual resolutions
- Fasecolda matches
- Fasecolda candidates
- valuations
- market evidence
- cost fields
- max bid
- ROI / expected profit
- final decision

The human Search dashboard remains the only search-term override authority.

Guardrails:

- `FASECOLDA_SEARCH_EVIDENCE_NOT_OVERRIDE_MATCH_OR_VALUATION`
- `FASECOLDA_DETAIL_4XX_BACKOFF_NOT_MATCH_OR_BUY_SIGNAL`

## Release plan

1. CI must pass full pytest, all Edge `deno check`, and Deno unit tests.
2. Branch must be `behind_by=0` immediately before merge.
3. Merge using the expected hotfix head SHA.
4. Apply only `fasecolda_detail_403_backoff_v601` from the immutable merged SHA.
5. Transactionally seed a synthetic current evidence row with a fresh 403 for an existing Search Review term, assert `SUGGESTED_DETAIL_FORBIDDEN` + `OPEN_HUMAN_SEARCH`, then rollback.
6. Assert the same row with `observed_at` older than 24 h becomes `SUGGESTED_EVIDENCE_STALE` + `REFRESH_SUGGESTED_EVIDENCE`, then rollback.
7. Re-certify permissions and zero business writes.
8. Deploy only `superbid-fasecolda-search-evidence-dashboard` with `verify_jwt=false` because custom auth remains in the body.
9. Read back the deployed function and verify v0.60.1/backoff markers and authority.
10. Do not claim manual/browser UAT unless actually performed.
