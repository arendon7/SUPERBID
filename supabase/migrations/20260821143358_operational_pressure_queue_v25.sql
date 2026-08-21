create or replace view public.dashboard_operational_queue as
select
  d.*,
  coalesce(p.pressure_level,'NONE') as pressure_level,
  coalesce(p.changes_2h,0) as pressure_changes_2h,
  coalesce(p.bid_up_2h,0) as pressure_bid_up_2h,
  coalesce(p.price_up_2h_cop,0) as pressure_price_up_2h_cop,
  coalesce(p.close_extension_count,0) as close_extension_count,
  p.last_change_at as pressure_last_change_at,
  case
    when d.closes_at is null then 'NO_CLOSE_TIME'
    when d.closes_at <= clock_timestamp() then 'PAST'
    when d.closes_at <= clock_timestamp()+interval '2 hours' then 'CLOSING_2H'
    when d.closes_at <= clock_timestamp()+interval '6 hours' then 'CLOSING_6H'
    when d.closes_at <= clock_timestamp()+interval '24 hours' then 'CLOSING_24H'
    else 'LATER'
  end as closing_bucket,
  case
    when d.closes_at is not null and d.closes_at <= clock_timestamp() then 999
    when d.review_state='REVIEW_NOW' and d.closes_at <= clock_timestamp()+interval '2 hours' then 10
    when d.review_state='REVIEW_NOW' and coalesce(p.pressure_level,'NONE')='HIGH' then 20
    when d.review_state='REVIEW_NOW' and d.closes_at <= clock_timestamp()+interval '6 hours' then 30
    when d.review_state='REVIEW_NOW' then 40
    when d.review_state='REVIEW_SOON' and d.closes_at <= clock_timestamp()+interval '6 hours' then 50
    when d.review_state='REVIEW_SOON' and coalesce(p.pressure_level,'NONE') in ('HIGH','MEDIUM') then 60
    when d.review_state='REVIEW_SOON' then 70
    when d.review_state='WATCH' then 80
    else 90
  end as operational_rank,
  case
    when d.closes_at is not null and d.closes_at <= clock_timestamp() then 'PAST_CLOSE'
    when d.review_state='REVIEW_NOW' and d.closes_at <= clock_timestamp()+interval '2 hours' then 'REVIEW_NOW_AND_CLOSING_2H'
    when d.review_state='REVIEW_NOW' and coalesce(p.pressure_level,'NONE')='HIGH' then 'REVIEW_NOW_AND_HIGH_PRESSURE'
    when d.review_state='REVIEW_NOW' and d.closes_at <= clock_timestamp()+interval '6 hours' then 'REVIEW_NOW_AND_CLOSING_6H'
    when d.review_state='REVIEW_NOW' then 'REVIEW_NOW'
    when d.review_state='REVIEW_SOON' and d.closes_at <= clock_timestamp()+interval '6 hours' then 'REVIEW_SOON_AND_CLOSING_6H'
    when d.review_state='REVIEW_SOON' and coalesce(p.pressure_level,'NONE') in ('HIGH','MEDIUM') then 'REVIEW_SOON_AND_ACTIVE_PRESSURE'
    when d.review_state='REVIEW_SOON' then 'REVIEW_SOON'
    when d.review_state='WATCH' then 'WATCH'
    else coalesce(d.review_state,'OTHER')
  end as operational_reason,
  'OPERATIONAL_TRIAGE_NOT_BUY_SIGNAL'::text as operational_interpretation
from public.dashboard_lot_current d
left join public.lot_bid_pressure_current p using(external_lot_id);

revoke all on public.dashboard_operational_queue from public,anon,authenticated;
grant select on public.dashboard_operational_queue to service_role;
