create or replace view public.lot_observed_bid_events as
with ordered as (
  select
    s.id as snapshot_id,
    s.lot_id,
    s.observed_at,
    s.displayed_price_cop,
    s.bid_count,
    s.outcome,
    s.closes_at,
    lag(s.displayed_price_cop) over(partition by s.lot_id order by s.observed_at,s.id) as prev_price_cop,
    lag(s.bid_count) over(partition by s.lot_id order by s.observed_at,s.id) as prev_bid_count,
    row_number() over(partition by s.lot_id order by s.observed_at,s.id) as rn
  from public.auction_snapshots s
), changed as (
  select
    o.*,
    case when o.prev_price_cop is null or o.displayed_price_cop is null then null else o.displayed_price_cop-o.prev_price_cop end as price_delta_cop,
    case when o.prev_bid_count is null or o.bid_count is null then null else o.bid_count-o.prev_bid_count end as bid_count_delta
  from ordered o
  where o.rn=1
     or o.displayed_price_cop is distinct from o.prev_price_cop
     or o.bid_count is distinct from o.prev_bid_count
)
select
  c.snapshot_id,
  c.lot_id,
  l.external_lot_id,
  c.observed_at,
  c.displayed_price_cop,
  c.prev_price_cop,
  c.price_delta_cop,
  c.bid_count,
  c.prev_bid_count,
  c.bid_count_delta,
  c.outcome,
  c.closes_at,
  case
    when c.rn=1 then 'INITIAL_OBSERVATION'
    when coalesce(c.price_delta_cop,0)<>0 and coalesce(c.bid_count_delta,0)<>0 then 'PRICE_AND_BID_COUNT_CHANGE'
    when coalesce(c.price_delta_cop,0)<>0 then 'PRICE_CHANGE_OBSERVED'
    when coalesce(c.bid_count_delta,0)<>0 then 'BID_COUNT_CHANGE_OBSERVED'
    else 'OBSERVED_CHANGE'
  end as observed_event_type,
  false as is_individual_bid
from changed c
join public.auction_lots l on l.id=c.lot_id;

revoke all on public.lot_observed_bid_events from public,anon,authenticated;
grant select on public.lot_observed_bid_events to service_role;

create or replace function public.dashboard_observed_bid_events(p_external_lot_id text)
returns jsonb
language sql
security definer
set search_path=public,pg_catalog
as $$
  select coalesce(jsonb_agg(jsonb_build_object(
    'observed_at',e.observed_at,
    'displayed_price_cop',e.displayed_price_cop,
    'prev_price_cop',e.prev_price_cop,
    'price_delta_cop',e.price_delta_cop,
    'bid_count',e.bid_count,
    'prev_bid_count',e.prev_bid_count,
    'bid_count_delta',e.bid_count_delta,
    'outcome',e.outcome,
    'closes_at',e.closes_at,
    'observed_event_type',e.observed_event_type,
    'is_individual_bid',false
  ) order by e.observed_at),'[]'::jsonb)
  from public.lot_observed_bid_events e
  where e.external_lot_id=p_external_lot_id;
$$;

revoke all on function public.dashboard_observed_bid_events(text) from public,anon,authenticated;
grant execute on function public.dashboard_observed_bid_events(text) to service_role;
