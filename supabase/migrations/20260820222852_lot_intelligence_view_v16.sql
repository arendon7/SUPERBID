create or replace view public.lot_intelligence_current
with (security_invoker=true)
as
select
  l.id as lot_id,
  l.external_lot_id,
  l.title,
  l.brand,
  l.line,
  l.model_year,
  l.city,
  l.seller,
  l.url,
  l.initial_bid_cop,
  s.displayed_price_cop as current_bid_cop,
  s.bid_count,
  s.observed_at as bid_observed_at,
  q.closes_at,
  o.outcome,
  fm.status as fasecolda_status,
  fm.best_code as fasecolda_code,
  fm.best_description as fasecolda_description,
  fm.current_value_cop as fasecolda_current_cop,
  fm.candidate_min_cop as fasecolda_min_cop,
  fm.candidate_median_cop as fasecolda_median_cop,
  fm.candidate_max_cop as fasecolda_max_cop,
  fm.latest_history_date as fasecolda_latest_date,
  fm.confidence as fasecolda_confidence,
  h12.value_cop as fasecolda_12m_ago_cop,
  case when h12.value_cop>0 and fm.current_value_cop is not null
       then round(((fm.current_value_cop::numeric/h12.value_cop)-1)*100,2)
       else null end as fasecolda_change_12m_pct,
  coalesce(att.peritaje_count,0) as peritaje_count,
  coalesce(att.peritajes,'[]'::jsonb) as peritajes
from public.auction_lots l
left join public.auction_outcomes o on o.lot_id=l.id
left join public.collection_queue q on q.external_lot_id=l.external_lot_id
left join lateral (
  select ss.* from public.auction_snapshots ss
  where ss.lot_id=l.id order by ss.observed_at desc limit 1
) s on true
left join public.lot_fasecolda_matches fm on fm.lot_id=l.id
left join lateral (
  select vh.value_cop
  from public.fasecolda_value_history vh
  where vh.code=fm.best_code and vh.model_year=l.model_year
    and fm.latest_history_date is not null
    and vh.value_date<=fm.latest_history_date-interval '11 months'
  order by vh.value_date desc limit 1
) h12 on true
left join lateral (
  select count(*)::integer peritaje_count,
         jsonb_agg(jsonb_build_object('name',a.name,'url',a.url,'discovered_at',a.discovered_at) order by a.discovered_at desc) peritajes
  from public.lot_attachments a
  where a.lot_id=l.id and a.kind='PERITAJE'
) att on true;

revoke all on public.lot_intelligence_current from public,anon,authenticated;
grant select on public.lot_intelligence_current to service_role;
