-- v0.46 extends the existing due-diligence read contract only.
-- The first 40 columns remain in the exact pre-v0.46 order; provenance is appended.
create or replace view public.dashboard_due_diligence_queue as
select
  r.external_lot_id,
  r.lot_id,
  r.title,
  r.city,
  r.seller,
  r.current_bid_cop,
  r.closes_at,
  r.hours_to_close,
  r.review_state,
  r.review_score,
  r.peritaje_count,
  r.peritaje_review_status,
  r.peritaje_overall_risk,
  r.fasecolda_status,
  r.commission_percent_public,
  r.market_status,
  r.market_validation_available,
  r.cost_review_status,
  r.completed_cost_fields,
  r.max_bid_market_validated_cop,
  r.expected_profit_current_cop,
  r.expected_roi_current_pct,
  r.final_decision,
  r.blockers,
  r.blocker_count,
  r.readiness_status,
  r.next_action,
  r.evidence_warning,
  o.pressure_level,
  o.pressure_changes_2h,
  o.pressure_bid_up_2h,
  o.pressure_price_up_2h_cop,
  o.close_extension_count,
  o.pressure_last_change_at,
  o.closing_bucket,
  o.operational_rank,
  o.operational_reason,
  case
    when r.readiness_status='CLOSED' then 999
    when r.readiness_status='READY_FOR_DECISION' and o.closing_bucket='CLOSING_2H' then 5
    when r.readiness_status='BLOCKED' and o.closing_bucket='CLOSING_2H' then 10
    when r.readiness_status='READY_FOR_DECISION' and o.closing_bucket='CLOSING_6H' then 15
    when r.readiness_status='BLOCKED' and o.closing_bucket='CLOSING_6H' then 20
    when r.readiness_status='READY_FOR_DECISION' and o.closing_bucket='CLOSING_24H' then 25
    when r.readiness_status='BLOCKED' and o.closing_bucket='CLOSING_24H' then 30
    when r.readiness_status='BLOCKED' and o.pressure_level='HIGH' then 35
    when r.readiness_status='READY_FOR_DECISION' then 40
    when r.review_state='REVIEW_NOW' then 50
    when r.review_state='REVIEW_SOON' then 60
    when r.review_state='WATCH' then 70
    else 80
  end as due_diligence_rank,
  case
    when r.readiness_status='CLOSED' then 'CLOSED_NO_ACTION'
    when r.readiness_status='READY_FOR_DECISION' and o.closing_bucket='CLOSING_2H' then 'DECIDE_NOW'
    when r.readiness_status='BLOCKED' and o.closing_bucket='CLOSING_2H' then 'UNBLOCK_NOW'
    when r.readiness_status='READY_FOR_DECISION' and o.closing_bucket='CLOSING_6H' then 'DECIDE_SOON'
    when r.readiness_status='BLOCKED' and o.closing_bucket='CLOSING_6H' then 'UNBLOCK_SOON'
    when r.readiness_status='READY_FOR_DECISION' and o.closing_bucket='CLOSING_24H' then 'DECIDE_TODAY'
    when r.readiness_status='BLOCKED' and o.closing_bucket='CLOSING_24H' then 'UNBLOCK_TODAY'
    when r.readiness_status='BLOCKED' and o.pressure_level='HIGH' then 'UNBLOCK_HIGH_PRESSURE'
    when r.readiness_status='READY_FOR_DECISION' then 'DECISION_AVAILABLE'
    when r.review_state='REVIEW_NOW' then 'PRIORITY_REVIEW'
    when r.review_state='REVIEW_SOON' then 'PREPARE_REVIEW'
    else 'BACKLOG'
  end as due_diligence_stage,
  'DUE_DILIGENCE_PRIORITY_NOT_BUY_SIGNAL'::text as due_diligence_interpretation,
  r.fasecolda_match_origin,
  r.fasecolda_automatic_status,
  r.fasecolda_match_interpretation
from public.dashboard_economic_readiness_current r
join public.dashboard_operational_queue o using(lot_id);

revoke all on public.dashboard_due_diligence_queue from public,anon,authenticated;
grant select on public.dashboard_due_diligence_queue to service_role;

comment on view public.dashboard_due_diligence_queue is
'Operational due-diligence priority derived from economic readiness and observed pressure. v0.46 appends Fasecolda provenance without changing the existing 40-column order, ranking, blockers, readiness or decision authority. DUE_DILIGENCE_PRIORITY_NOT_BUY_SIGNAL.';
