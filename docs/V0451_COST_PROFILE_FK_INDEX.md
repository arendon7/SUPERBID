# v0.45.1 — Cost profile FK index patch

## Origin

After deploying v0.45, the Supabase performance advisor reported one new actionable INFO finding introduced by the new cost-governance schema:

- table: `lot_cost_profile_application_history`;
- foreign key: `profile_version_id -> cost_assumption_profile_versions(id)`;
- issue: no covering index on `profile_version_id`.

## Scope

v0.45.1 adds only:

`ix_lot_cost_profile_application_profile(profile_version_id)`

The patch is intentionally index-only.

It does not:

- insert, update or delete business data;
- alter cost profiles;
- apply costs to any lot;
- alter lot readiness;
- change Fasecolda or market evidence;
- change current bid, commission or peritaje;
- change the v0.45 RPCs or views;
- create a buy signal or final decision.

## Release invariant

v0.45 guardrails remain authoritative:

- `COST_PROFILE_ASSUMPTION_NOT_LOT_COST`;
- `COST_PROFILE_APPLICATION_REQUIRES_LOT_CONFIRMATION`;
- `COST_GOVERNANCE_NOT_BUY_SIGNAL`.

## Acceptance

The patch is complete only when:

1. exact PR HEAD passes the complete test suite;
2. branch remains `behind_by=0`;
3. the index migration prevalidates/applies successfully;
4. the Supabase performance advisor no longer reports the `profile_version_id` foreign-key finding;
5. production still contains zero automatically created profiles, profile applications and lot-cost overrides.
