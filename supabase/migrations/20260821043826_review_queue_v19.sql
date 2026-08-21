create or replace view public.lot_review_queue_current as
with b as (
  select
    o.*,
    case when o.fasecolda_current_cop>0 and o.preliminary_headroom_before_fixed_costs_cop is not null
         then greatest(0,o.preliminary_headroom_before_fixed_costs_cop::numeric/o.fasecolda_current_cop)
         else 0 end as headroom_ratio,
    case when o.closes_at is not null then extract(epoch from (o.closes_at-clock_timestamp()))/3600.0 end as hours_to_close
  from public.lot_opportunity_preliminary o
), s as (
  select b.*,
    least(40,greatest(0,round((headroom_ratio/0.30)*40)::integer)) as headroom_points,
    case when peritaje_count>0 then 25 else 0 end as peritaje_points,
    case when hours_to_close is null or hours_to_close<=0 then 0
         when hours_to_close<=24 then 20
         when hours_to_close<=72 then 12
         when hours_to_close<=168 then 5
         else 0 end as urgency_points,
    case when coalesce(bid_count,0)>=5 then 10 when coalesce(bid_count,0)>=1 then 5 else 0 end as activity_points,
    case when commission_percent_public is null then 0 when commission_percent_public<=5 then 5 when commission_percent_public<=6.5 then 3 else 0 end as commission_points
  from b
), r as (
  select s.*,
    least(100,headroom_points+peritaje_points+urgency_points+activity_points+commission_points) as review_score
  from s
)
select r.*,
  case
    when closes_at is not null and closes_at<=clock_timestamp() then 'CLOSED_OR_PAST'
    when fasecolda_status<>'HIGH' then 'BLOCKED_VALUATION'
    when preliminary_headroom_before_fixed_costs_cop is null or preliminary_headroom_before_fixed_costs_cop<=0 then 'NO_HEADROOM'
    when review_score>=65 then 'REVIEW_NOW'
    when review_score>=45 then 'REVIEW_SOON'
    else 'WATCH'
  end as review_state,
  (peritaje_count>0) as peritaje_ready,
  jsonb_strip_nulls(jsonb_build_object(
    'headroom_points',headroom_points,
    'peritaje_points',peritaje_points,
    'urgency_points',urgency_points,
    'activity_points',activity_points,
    'commission_points',commission_points,
    'needs_market_validation',true,
    'needs_cost_review',true
  )) as review_reasons
from r;

revoke all on public.lot_review_queue_current from public,anon,authenticated;
grant select on public.lot_review_queue_current to service_role;
