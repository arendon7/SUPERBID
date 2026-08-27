# SUPERBID v0.60 — Fasecolda Search Evidence Cache

## Purpose

v0.60 adds a preflight/evidence layer before the existing human Fasecolda Search workflow. It reduces repeated public-search calls across lots that share the same suggested term, makes model-year compatibility visible before a human override decision, and keeps automated evidence strictly separate from match/valuation authority.

Guardrail:

`FASECOLDA_SEARCH_EVIDENCE_NOT_OVERRIDE_MATCH_OR_VALUATION`

A cached search result is evidence only. It never confirms a search term, chooses a Fasecolda code, runs the matcher, creates candidates, changes valuation, modifies max bid/ROI, or creates a buy signal.

## Production evidence before implementation

The v0.59 fast control plane had 145 active Fasecolda workstream cases:

- 11 `CANDIDATE_EVIDENCE`
- 45 `SOURCE_REGISTERED_REVIEW`
- 50 `SEARCH_REVIEW`
- 7 `YEAR_REVIEW`
- 17 `SOURCE_ACQUISITION`
- 15 `CATALOG_INDISTINGUISHABLE`

The 50 `SEARCH_REVIEW` cases were decomposed with the same fail-closed semantics already used by the v0.54 Search dashboard:

- 43 `EXPLORABLE`
- 5 `IDENTITY_INPUT_REVIEW`
- 2 `MISSING_YEAR`

The 43 explorable lots used only 30 distinct suggested terms. Eight repeated terms covered 21 lots, including:

- `CHEVROLET CAPTIVA TURBO` — 6 lots
- `CHEVROLET BLAZER RS` — 3 lots
- `CHEVROLET CAPTIVA PREMIER` — 2 lots
- `CITROEN C4 CACTUS` — 2 lots
- `NISSAN FRONTIER NP300` — 2 lots
- `NISSAN X TRAIL` — 2 lots
- `RENAULT NUEVA KOLEOS` — 2 lots
- `VOLKSWAGEN T CROSS` — 2 lots

Eight real read-only probes were executed, one per repeated term, using the existing `dashboard_probe_fasecolda_search_term` RPC. Four terms returned public codes and four returned 404/zero codes. Post-probe audit remained zero for search overrides, search override history, manual resolutions and candidate evidence.

This supports caching by normalized search term rather than repeating the same public GET independently for every lot.

## Data model

### `fasecolda_search_term_evidence_current`

Latest automated observation keyed by normalized search term.

Stores:

- search HTTP status
- up to 22 public search codes
- detail HTTP status
- explicit `detail_payload_valid`
- detail payload when it is a valid JSON array
- public source URLs
- provenance lot used for the observation
- evidence fingerprint
- observed timestamp
- fixed non-authoritative interpretation

### `fasecolda_search_term_evidence_history`

Append-only observation history with the same evidence payload plus `recorded_at`.

Both tables:

- have RLS enabled
- deny public/anon/authenticated access
- are service-role-only
- do not contain human disposition fields

## Fail-closed detail semantics

HTTP 200 from the detail endpoint is not sufficient evidence by itself.

`detail_payload_valid=true` is set only when the body parses as JSON and the top-level value is an array. A malformed/non-array HTTP 200 is treated as `SUGGESTED_DETAIL_UNAVAILABLE`.

It must never become `SUGGESTED_NO_YEAR_COMPATIBLE_CODES`, because that would convert non-interpretable evidence into negative evidence.

## Input classifier

`fasecolda_search_input_disposition_v60(brand, model_year, suggested_term)` mirrors the v0.54 Search dashboard semantics using the canonical SQL `vehicle_norm` normalization.

States:

- `EXPLORABLE`
- `IDENTITY_INPUT_REVIEW`
- `MISSING_YEAR`

Generic brands such as `CAMION`, `CAMIONETA`, `AUTOMOVIL`, `VOLQUETA`, `TRACTOCAMION`, etc. fail closed. Suggested terms must preserve the normalized canonical brand.

## Refresh RPC

`dashboard_refresh_fasecolda_search_term_evidence_v60(external_lot_id, term)`:

1. validates exact 5–12 digit lot ID;
2. reloads the live lot;
3. revalidates identity/year disposition;
4. normalizes and revalidates brand preservation;
5. calls the existing read-only v0.54 public-search probe;
6. if codes exist, calls the public Fasecolda detail endpoint;
7. records current + history evidence only;
8. returns explicit false flags for override/match/candidate/valuation/economic modification and `buy_signal=false`.

It does **not** call `fasecolda_match_lot` and does not touch:

- `lot_fasecolda_matches`
- `lot_fasecolda_candidates`
- `lot_fasecolda_search_term_overrides`
- `lot_fasecolda_manual_resolutions`
- market/cost/readiness/economic decision state

## Search Evidence Queue

`dashboard_fasecolda_search_evidence_queue_v60` starts from the 50 v0.59 `SEARCH_REVIEW` cases and joins shared term evidence.

It derives:

- input disposition
- evidence freshness (24 h)
- public code count
- detail availability/validity
- count of codes with a `valorModelo` entry for the lot model year and `USADO` state
- evidence state
- operator next action
- whether the suggested term is reviewable by a human

It intentionally does not expose or calculate COP valuation fields.

Evidence states:

- `IDENTITY_INPUT_REVIEW`
- `MISSING_YEAR`
- `SUGGESTED_EVIDENCE_MISSING`
- `SUGGESTED_EVIDENCE_STALE`
- `SUGGESTED_NO_CODES`
- `SUGGESTED_DETAIL_UNAVAILABLE`
- `SUGGESTED_NO_YEAR_COMPATIBLE_CODES`
- `SUGGESTED_YEAR_COMPATIBLE_CODES`

`SUGGESTED_YEAR_COMPATIBLE_CODES` means only that the suggested term returned at least one public code with a used-value entry for that model year. It is not a match and not a valuation.

## Edge dashboard

New function:

`superbid-fasecolda-search-evidence-dashboard`

Authority surface is intentionally limited to:

- `dashboard_token_valid`
- `dashboard_refresh_fasecolda_search_term_evidence_v60`

The existing v0.54 `superbid-fasecolda-search-dashboard` remains the human authority for manual probes and explicit search-term override confirmation/clear.

The v0.60 dashboard provides:

- exact-lot completion-safe routing
- state filters and metrics
- evidence freshness/provenance
- public codes and year-compatible count
- detail payload validity
- individual explicit POST refresh
- bounded batch refresh: maximum six unique normalized suggested terms, sequentially
- handoff to the existing Search human workflow

The dashboard is server-rendered and contains no client JavaScript.

## Workbench handoff

For `SEARCH_REVIEW`, the primary v0.60 Workbench CTA routes to Search Evidence preflight. A secondary `Search humano` shortcut remains available.

The Workbench itself stays auth-only/read-only and does not gain evidence-refresh authority.

## Transactional migration smoke

The complete current v0.60 migration was executed against the live production schema inside `BEGIN ... ROLLBACK`.

An internal assertion required the temporary queue to equal:

- total: 50
- explorable: 43
- identity review: 5
- missing year: 2

The assertion passed. After rollback, all v0.60 tables, view and refresh RPC were verified absent.

No v0.60 schema object is currently persisted in production before release merge/deploy.

## Release gates

Before production release:

- full pytest green
- Edge `deno check` green for every function
- Deno unit tests green
- branch `behind_by=0`
- immutable merge SHA captured
- apply migration once from merged SHA
- certify permissions
- certify 50-case queue or explain natural auction-time drift
- certify current/history start at zero
- deploy new Search Evidence dashboard with `verify_jwt=false` because body implements custom auth
- deploy Workbench routing update from the same immutable merge SHA
- read back both live Edge bundles
- verify zero human/business writes after deployment

External/manual browser UAT must be reported only if actually performed. Runtime safe-open/DNS limitations are not evidence of successful UAT.
