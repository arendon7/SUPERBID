create or replace view public.lot_bid_pressure_current as
with event_agg as (
  select
    l.id as lot_id,
    l.external_lot_id,
    count(e.*) filter (where e.observed_event_type <> 'INITIAL_OBSERVATION')::integer as observed_change_events,
    coalesce(sum(greatest(coalesce(e.price_delta_cop,0),0)) filter (where e.observed_event_type <> 'INITIAL_OBSERVATION'),0)::bigint as observed_price_up_cop,
    coalesce(sum(greatest(coalesce(e.bid_count_delta,0),0)) filter (where e.observed_event_type <> 'INITIAL_OBSERVATION'),0)::integer as observed_bid_up,
    max(e.observed_at) filter (where e.observed_event_type <> 'INITIAL_OBSERVATION') as last_change_at,
    count(e.*) filter (where e.observed_event_type <> 'INITIAL_OBSERVATION' and e.observed_at >= clock_timestamp()-interval '2 hours')::integer as changes_2h,
    coalesce(sum(greatest(coalesce(e.bid_count_delta,0),0)) filter (where e.observed_event_type <> 'INITIAL_OBSERVATION' and e.observed_at >= clock_timestamp()-interval '2 hours'),0)::integer as bid_up_2h,
    coalesce(sum(greatest(coalesce(e.price_delta_cop,0),0)) filter (where e.observed_event_type <> 'INITIAL_OBSERVATION' and e.observed_at >= clock_timestamp()-interval '2 hours'),0)::bigint as price_up_2h_cop,
    count(e.*) filter (where e.observed_event_type <> 'INITIAL_OBSERVATION' and e.observed_at >= clock_timestamp()-interval '6 hours')::integer as changes_6h,
    coalesce(sum(greatest(coalesce(e.bid_count_delta,0),0)) filter (where e.observed_event_type <> 'INITIAL_OBSERVATION' and e.observed_at >= clock_timestamp()-interval '6 hours'),0)::integer as bid_up_6h,
    coalesce(sum(greatest(coalesce(e.price_delta_cop,0),0)) filter (where e.observed_event_type <> 'INITIAL_OBSERVATION' and e.observed_at >= clock_timestamp()-interval '6 hours'),0)::bigint as price_up_6h_cop,
    count(e.*) filter (where e.observed_event_type <> 'INITIAL_OBSERVATION' and e.observed_at >= clock_timestamp()-interval '24 hours')::integer as changes_24h,
    coalesce(sum(greatest(coalesce(e.bid_count_delta,0),0)) filter (where e.observed_event_type <> 'INITIAL_OBSERVATION' and e.observed_at >= clock_timestamp()-interval '24 hours'),0)::integer as bid_up_24h
  from public.auction_lots l
  left join public.lot_observed_bid_events e on e.lot_id=l.id
  group by l.id,l.external_lot_id
), ordered_snapshots as (
  select
    s.lot_id,
    s.observed_at,
    s.closes_at,
    lag(s.closes_at) over(partition by s.lot_id order by s.observed_at,s.id) as prev_closes_at
  from public.auction_snapshots s
), snapshot_agg as (
  select
    lot_id,
    min(observed_at) as first_snapshot_at,
    max(observed_at) as last_snapshot_at,
    count(*)::integer as snapshot_count,
    count(*) filter (
      where closes_at is not null and prev_closes_at is not null and closes_at > prev_closes_at + interval '1 second'
    )::integer as close_extension_count
  from ordered_snapshots
  group by lot_id
), joined as (
  select
    e.*,
    s.first_snapshot_at,
    s.last_snapshot_at,
    coalesce(s.snapshot_count,0) as snapshot_count,
    coalesce(s.close_extension_count,0) as close_extension_count,
    case
      when s.first_snapshot_at is null or s.last_snapshot_at is null then null
      else round((extract(epoch from (s.last_snapshot_at-s.first_snapshot_at))/3600.0)::numeric,2)
    end as observation_hours
  from event_agg e
  left join snapshot_agg s on s.lot_id=e.lot_id
)
select
  j.*,
  case
    when j.changes_2h >= 2 or j.bid_up_2h >= 4 or j.close_extension_count >= 2 then 'HIGH'
    when j.changes_6h >= 1 or j.observed_change_events >= 3 or j.observed_bid_up >= 5 or j.close_extension_count = 1 then 'MEDIUM'
    when j.observed_change_events >= 1 then 'LOW'
    else 'NONE'
  end as pressure_level,
  jsonb_build_object(
    'changes_2h',j.changes_2h,
    'bid_up_2h',j.bid_up_2h,
    'price_up_2h_cop',j.price_up_2h_cop,
    'changes_6h',j.changes_6h,
    'bid_up_6h',j.bid_up_6h,
    'observed_change_events',j.observed_change_events,
    'observed_bid_up',j.observed_bid_up,
    'observed_price_up_cop',j.observed_price_up_cop,
    'close_extension_count',j.close_extension_count,
    'last_change_at',j.last_change_at,
    'interpretation','OBSERVATIONAL_ONLY_NOT_BUY_SIGNAL'
  ) as pressure_evidence
from joined j;

revoke all on public.lot_bid_pressure_current from public,anon,authenticated;
grant select on public.lot_bid_pressure_current to service_role;

create or replace function public.dashboard_bid_pressure(p_external_lot_id text)
returns jsonb
language sql
security definer
set search_path=public,pg_catalog
as $$
  select coalesce(to_jsonb(p),'{}'::jsonb)
  from public.lot_bid_pressure_current p
  where p.external_lot_id=p_external_lot_id;
$$;

revoke all on function public.dashboard_bid_pressure(text) from public,anon,authenticated;
grant execute on function public.dashboard_bid_pressure(text) to service_role;
