# SUPERBID v0.53 — Fasecolda Identity Hints / Candidate Difference Matrix

## Purpose

v0.53 reduces operator context-switching inside the v0.52 Fasecolda Candidate Resolution Cockpit without weakening the human-evidence gate.

The release adds deterministic, read-only textual hints for four identity dimensions:

- engine displacement (`engine_cc`)
- transmission
- drivetrain
- fuel / propulsion

The hints compare literal tokens found in the public auction title against literal tokens found in each current Fasecolda candidate description.

They are **not evidence, not a match, not a score, not a candidate recommendation and not a buy signal**.

Guardrail:

`AUTOMATED_IDENTITY_HINT_NOT_HUMAN_EVIDENCE_OR_MATCH`

## Production evidence behind the design

The v0.52 production queue contained 153 `REVIEW_VALUATION` cases:

- 99 `CANDIDATE_RESOLUTION`
- 39 `SEARCH_TERM_WORKFLOW`
- 15 `YEAR_REFERENCE_REVIEW`

v0.53 deliberately targets only the 99 candidate-resolution cases.

Those 99 cases contain 424 current candidate rows. A literal-token audit using the same families of patterns used by v0.53 found:

### Auction-title coverage

- explicit cc: 73 / 99 cases
- transmission: 59 / 99
- drivetrain: 12 / 99
- fuel / propulsion: 5 / 99

No current title in the audited queue contained simultaneous contradictory transmission flags or simultaneous contradictory drivetrain flags under the v0.53 patterns.

### Candidate-description coverage

Across 424 candidate rows:

- explicit cc: 347 rows
- transmission: 424 rows
- drivetrain: 115 rows
- fuel / propulsion: 9 rows

The hints therefore have useful coverage for engine and transmission, lower coverage for drivetrain, and intentionally sparse coverage for fuel.

## Why exact cc equality was rejected

A first-pass comparison using exact numeric equality produced misleading conflicts because auction titles often publish actual engine displacement while Fasecolda descriptions use nominal family displacement.

Real production examples include:

- `1598 CC` versus `1600CC`
- `2999 CC` versus `3000CC`
- `5193 CC` versus `5200CC`
- `1451 CC` versus `1500CC`

Treating those pairs as direct `DIFIERE` would create false certainty.

v0.53 therefore uses a dedicated diagnostic state for engine displacement:

`NOMINAL_COMPATIBLE`

when the absolute difference is at most **50 cc**.

The cockpit renders this as:

`COMPATIBLE ±50 CC`

This is intentionally separate from `COINCIDE`. It only states that the two literal values fall within a narrow nominal-displacement tolerance. It does **not** prove that the candidate is the correct version and it does not satisfy the v0.52 human `MATCH` requirement.

Differences larger than 50 cc remain `DIFIERE`.

## Fail-closed extraction rules

The extractor returns an unknown hint instead of guessing when multiple contradictory literal values are present in the same text. Examples:

- `1000 CC / 1600 CC` → engine unknown
- `MT AT` → transmission unknown
- `4X2 4X4` → drivetrain unknown
- `DIESEL GASOLINA` → fuel unknown

Hybrid and electric declarations have precedence over a secondary fuel word where that wording describes the propulsion architecture, e.g. `HÍBRIDO GASOLINA` remains the hint `HYBRID`.

## Diagnostic effect after the ±50 cc hardening

A production audit of the 99 candidate-resolution cases, using cc/transmission/drivetrain differences and the 50 cc nominal tolerance, produced:

- 48 cases where hints identify at least one candidate with a literal difference
- 10 cases where every current candidate has at least one literal difference
- 51 cases where no current candidate is flagged by the available hints
- 12 cases where exactly one candidate remains without a literal difference
- average candidates without a literal difference: 3.13 per case

The **12 single-survivor cases are not automatic resolutions**. They only indicate that, among the dimensions for which both sides expose literal text, one candidate happens not to show a difference. Missing attributes, trim, body/use distinctions and other evidence can still be decisive.

Accordingly v0.53 does not:

- preselect that candidate
- change its rank
- create a new hint score
- mark a human evidence dimension
- mark a discriminator
- create `REVIEWED`
- write a manual Fasecolda resolution

## Architecture

### Canonical Python helper

`src/superbid_collector/identity_hints.py`

Provides deterministic extraction and comparison primitives. The existing HTML parser now reuses the helper's canonical engine-cc regex, preserving the existing persisted `engine_cc` behavior while avoiding a duplicated pattern.

The parser does **not** persist the new v0.53 hint structure.

### Edge helper

`supabase/functions/superbid-fasecolda-candidate-cockpit/identity_hints.ts`

Mirrors the Python semantics for server-rendered cockpit use. It is deliberately pure:

- no `fetch`
- no Supabase environment access
- no REST/RPC calls
- no service-role authority
- no mutation

### Cockpit rendering

The existing `superbid-fasecolda-candidate-cockpit` imports the pure helper and renders, per candidate:

- `COINCIDE`
- `COMPATIBLE ±50 CC`
- `DIFIERE`
- `SIN PISTA LOTE`
- `SIN PISTA CANDIDATO`

No aggregate score is calculated and candidate order remains the canonical Fasecolda candidate order already supplied by the backend.

The v0.52 evidence form remains separate. Hint values are not copied into form controls and do not enter `FormData`, `p_dimensions`, or any RPC payload.

## Authority boundary

v0.53 adds **no migration**, no table, no view, no RPC and no business write authority.

The cockpit retains exactly the v0.52 RPC surface:

- `dashboard_token_valid`
- `dashboard_save_fasecolda_candidate_resolution`
- `dashboard_clear_fasecolda_candidate_resolution_v52`

Candidate confirmation remains governed entirely by the v0.52 backend evidence gate and defense-in-depth trigger.

## Selection invariant

A candidate can still enter the evidence form only through:

1. explicit `?candidate=<code>` operator navigation, or
2. an already persisted v0.52 evidence snapshot for that lot.

Automatic `best_code`, fuzzy `best_score`, hint outcomes, nominal compatibility and literal differences are never used as candidate-selection inputs.

## Release gates

v0.53 must pass:

1. full historical pytest suite
2. dedicated extraction and nominal-compatibility tests
3. static authority regressions proving hints do not enter `FormData` or RPC payloads
4. dynamic Deno check for every Supabase Edge Function, including the cockpit relative helper module
5. branch `behind_by=0` before merge
6. post-merge `main` CI
7. immutable-source Edge deployment and read-back certification
8. postdeploy zero-write audit

No manual browser UAT should be claimed unless it is actually performed.
