-- v0.45.1 closes the Supabase performance advisor raised after v0.45.
-- This migration is index-only: it does not mutate cost profiles, lot costs,
-- readiness, evidence, decisions, or any business data.
create index if not exists ix_lot_cost_profile_application_profile
  on public.lot_cost_profile_application_history(profile_version_id);

comment on index public.ix_lot_cost_profile_application_profile is
'Covering index for lot_cost_profile_application_history.profile_version_id foreign key; v0.45.1 performance-only patch.';
