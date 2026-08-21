create or replace view public.dashboard_economic_readiness_current as
with base as (
  select
    d.external_lot_id,
    d.lot_id,
    d.title,
    d.city,
    d.seller,
    d.current_bid_cop,
    d.closes_at,
    d.hours_to_close,
    d.review_state,
    d.review_score,
    d.peritaje_count,
    case
      when coalesce(d.peritaje_count,0)=0 then 'NOT_AVAILABLE'
      when p.lot_id is null then 'UNREVIEWED'
      when p.reviewed_at is null then 'DRAFT'
      else 'REVIEWED'
    end as peritaje_review_status,
    p.overall_risk as peritaje_overall_risk,
    d.fasecolda_status,
    d.commission_percent_public,
    d.market_status,
    coalesce(d.market_validation_available,false) as market_validation_available,
    case
      when c.lot_id is null then 'NO_COSTS'
      when c.reviewed_at is not null then 'REVIEWED'
      else 'DRAFT'
    end as cost_review_status,
    (((c.transfer_cop is not null)::int +
      (c.taxes_soat_cop is not null)::int +
      (c.transport_cop is not null)::int +
      (c.repair_cop is not null)::int +
      (c.detailing_cop is not null)::int +
      (c.financing_cop is not null)::int +
      (c.admin_fee_cop is not null)::int +
      (c.contingency_cop is not null)::int)) as completed_cost_fields,
    c.reviewed_at as costs_reviewed_at,
    d.max_bid_market_validated_cop,
    d.expected_profit_current_cop,
    d.expected_roi_current_pct,
    d.market_final_buy_recommendation_available,
    d.final_decision
  from public.dashboard_lot_current d
  left join public.lot_peritaje_reviews p on p.lot_id=d.lot_id
  left join public.lot_cost_overrides c on c.lot_id=d.lot_id
), blockers as (
  select b.*,
    array_remove(array[
      case when b.closes_at is not null and b.closes_at <= clock_timestamp() then 'CLOSED_OR_PAST' end,
      case when b.fasecolda_status is distinct from 'HIGH' then 'FASECOLDA_NOT_HIGH' end,
      case when b.commission_percent_public is null then 'COMMISSION_MISSING' end,
      case when b.peritaje_count > 0 and b.peritaje_review_status <> 'REVIEWED' then 'PERITAJE_NOT_REVIEWED' end,
      case when not b.market_validation_available then 'MARKET_NOT_VALIDATED' end,
      case when b.cost_review_status = 'NO_COSTS' then 'LOT_COSTS_MISSING' end,
      case when b.completed_cost_fields < 8 then 'LOT_COSTS_INCOMPLETE' end,
      case when b.cost_review_status <> 'REVIEWED' then 'LOT_COSTS_NOT_REVIEWED' end,
      case when b.current_bid_cop is null then 'CURRENT_BID_MISSING' end
    ]::text[], null) as blockers
  from base b
)
select
  x.*,
  cardinality(x.blockers) as blocker_count,
  case
    when x.closes_at is not null and x.closes_at <= clock_timestamp() then 'CLOSED'
    when cardinality(x.blockers)=0 then 'READY_FOR_DECISION'
    else 'BLOCKED'
  end as readiness_status,
  case
    when x.closes_at is not null and x.closes_at <= clock_timestamp() then 'NO_ACTION_CLOSED'
    when x.fasecolda_status is distinct from 'HIGH' then 'REVIEW_VALUATION'
    when x.commission_percent_public is null then 'REVIEW_COMMISSION'
    when x.peritaje_count > 0 and x.peritaje_review_status <> 'REVIEWED' then 'REVIEW_PERITAJE'
    when not x.market_validation_available then 'VALIDATE_MARKET'
    when x.cost_review_status = 'NO_COSTS' then 'ENTER_LOT_COSTS'
    when x.completed_cost_fields < 8 then 'COMPLETE_LOT_COSTS'
    when x.cost_review_status <> 'REVIEWED' then 'REVIEW_LOT_COSTS'
    when x.current_bid_cop is null then 'WAIT_CURRENT_BID'
    else 'DECISION_AVAILABLE'
  end as next_action,
  case
    when x.peritaje_count=0 then 'NO_PUBLIC_PERITAJE_AVAILABLE'
    else null::text
  end as evidence_warning,
  'ECONOMIC_READINESS_NOT_BUY_SIGNAL'::text as interpretation
from blockers x;

revoke all on public.dashboard_economic_readiness_current from public, anon, authenticated;
grant select on public.dashboard_economic_readiness_current to service_role;

comment on view public.dashboard_economic_readiness_current is
'Operational explanation of economic decision readiness. READY_FOR_DECISION means required evidence/reviews are complete; it is not a buy recommendation.';
