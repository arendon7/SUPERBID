create or replace function public.dashboard_observed_bid_events(p_external_lot_id text, p_limit integer)
returns jsonb
language sql
security definer
set search_path=public,pg_catalog
as $$
  select coalesce(jsonb_agg(x.obj order by x.observed_at desc),'[]'::jsonb)
  from (
    select
      e.observed_at,
      jsonb_build_object(
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
      ) as obj
    from public.lot_observed_bid_events e
    where e.external_lot_id=p_external_lot_id
    order by e.observed_at desc
    limit greatest(1,least(coalesce(p_limit,100),500))
  ) x;
$$;

revoke all on function public.dashboard_observed_bid_events(text,integer) from public,anon,authenticated;
grant execute on function public.dashboard_observed_bid_events(text,integer) to service_role;
