-- SUPERBID v0.49 · Condition Evidence Gate
-- Missing public peritaje is no longer only a warning. An explicit reviewed
-- human disposition is required before READY_FOR_DECISION can be reached.
-- This layer never writes a buy signal, final decision, market evidence,
-- Fasecolda resolution, bid or cost values.

create table if not exists public.lot_condition_dispositions(
  id bigint generated always as identity primary key,
  lot_id bigint not null unique references public.auction_lots(id) on delete cascade,
  external_lot_id text not null,
  disposition text,
  evidence_note text,
  reviewed_at timestamptz,
  created_at timestamptz not null default clock_timestamp(),
  updated_at timestamptz not null default clock_timestamp(),
  interpretation text not null default 'MANUAL_CONDITION_RISK_DISPOSITION_NOT_DIAGNOSIS_OR_BUY_SIGNAL',
  constraint lot_condition_disposition_allowed check(disposition is null or disposition in ('ACCEPT_UNKNOWN_WITH_RESERVE','DECLINE_UNKNOWN_CONDITION')),
  constraint lot_condition_note_len check(evidence_note is null or char_length(evidence_note)<=4000),
  constraint lot_condition_interpretation_guard check(interpretation='MANUAL_CONDITION_RISK_DISPOSITION_NOT_DIAGNOSIS_OR_BUY_SIGNAL')
);

create table if not exists public.lot_condition_disposition_history(
  id bigint generated always as identity primary key,
  lot_id bigint not null references public.auction_lots(id) on delete cascade,
  external_lot_id text not null,
  disposition text,
  evidence_note text,
  marked_reviewed boolean not null default false,
  created_at timestamptz not null default clock_timestamp(),
  interpretation text not null default 'MANUAL_CONDITION_RISK_DISPOSITION_NOT_DIAGNOSIS_OR_BUY_SIGNAL',
  constraint lot_condition_history_disposition_allowed check(disposition is null or disposition in ('ACCEPT_UNKNOWN_WITH_RESERVE','DECLINE_UNKNOWN_CONDITION')),
  constraint lot_condition_history_note_len check(evidence_note is null or char_length(evidence_note)<=4000),
  constraint lot_condition_history_interpretation_guard check(interpretation='MANUAL_CONDITION_RISK_DISPOSITION_NOT_DIAGNOSIS_OR_BUY_SIGNAL')
);

alter table public.lot_condition_dispositions enable row level security;
alter table public.lot_condition_disposition_history enable row level security;
revoke all on public.lot_condition_dispositions,public.lot_condition_disposition_history from public,anon,authenticated;
grant select,insert,update on public.lot_condition_dispositions to service_role;
grant select,insert on public.lot_condition_disposition_history to service_role;

create or replace function public.dashboard_save_condition_disposition(
  p_external_lot_id text,
  p_disposition text default null,
  p_evidence_note text default null,
  p_mark_reviewed boolean default false
) returns jsonb
language plpgsql
security definer
set search_path=public,pg_catalog
as $$
declare
  v_lot_id bigint;
  v_disposition text:=nullif(upper(trim(coalesce(p_disposition,''))), '');
  v_note text:=nullif(trim(coalesce(p_evidence_note,'')), '');
  v_reviewed_at timestamptz;
begin
  if p_external_lot_id is null or p_external_lot_id !~ '^[0-9]{5,12}$' then
    raise exception 'invalid external lot id';
  end if;

  select id into v_lot_id
  from public.auction_lots
  where external_lot_id=p_external_lot_id
  limit 1;
  if v_lot_id is null then raise exception 'lot not found'; end if;

  if exists(select 1 from public.lot_attachments where lot_id=v_lot_id and kind='PERITAJE') then
    raise exception 'public peritaje exists; use peritaje review workflow';
  end if;

  if v_disposition is not null and v_disposition not in ('ACCEPT_UNKNOWN_WITH_RESERVE','DECLINE_UNKNOWN_CONDITION') then
    raise exception 'invalid condition disposition';
  end if;
  if v_note is not null and char_length(v_note)>4000 then raise exception 'evidence note too long'; end if;

  if p_mark_reviewed then
    if v_disposition is null then raise exception 'reviewed condition disposition is required'; end if;
    if v_note is null or char_length(v_note)<20 then raise exception 'reviewed condition disposition requires an evidence note of at least 20 characters'; end if;
  end if;

  v_reviewed_at:=case when p_mark_reviewed then clock_timestamp() else null end;

  insert into public.lot_condition_dispositions(
    lot_id,external_lot_id,disposition,evidence_note,reviewed_at,updated_at
  ) values(
    v_lot_id,p_external_lot_id,v_disposition,v_note,v_reviewed_at,clock_timestamp()
  )
  on conflict(lot_id) do update set
    external_lot_id=excluded.external_lot_id,
    disposition=excluded.disposition,
    evidence_note=excluded.evidence_note,
    reviewed_at=excluded.reviewed_at,
    updated_at=clock_timestamp();

  insert into public.lot_condition_disposition_history(
    lot_id,external_lot_id,disposition,evidence_note,marked_reviewed
  ) values(
    v_lot_id,p_external_lot_id,v_disposition,v_note,p_mark_reviewed
  );

  return jsonb_build_object(
    'ok',true,
    'external_lot_id',p_external_lot_id,
    'disposition',v_disposition,
    'reviewed',p_mark_reviewed,
    'buy_signal',false,
    'economic_fields_modified',false,
    'interpretation','MANUAL_CONDITION_RISK_DISPOSITION_NOT_DIAGNOSIS_OR_BUY_SIGNAL'
  );
end;
$$;

revoke all on function public.dashboard_save_condition_disposition(text,text,text,boolean) from public,anon,authenticated;
grant execute on function public.dashboard_save_condition_disposition(text,text,text,boolean) to service_role;

-- Preserve every v0.33 output column in its existing order and append the
-- condition-risk provenance fields at the end.
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
    ((c.transfer_cop is not null)::int +
     (c.taxes_soat_cop is not null)::int +
     (c.transport_cop is not null)::int +
     (c.repair_cop is not null)::int +
     (c.detailing_cop is not null)::int +
     (c.financing_cop is not null)::int +
     (c.admin_fee_cop is not null)::int +
     (c.contingency_cop is not null)::int) as completed_cost_fields,
    c.reviewed_at as costs_reviewed_at,
    c.repair_cop as condition_repair_reserve_cop,
    d.max_bid_market_validated_cop,
    d.expected_profit_current_cop,
    d.expected_roi_current_pct,
    d.market_final_buy_recommendation_available,
    d.final_decision,
    case
      when coalesce(d.peritaje_count,0)>0 then 'NOT_APPLICABLE'
      when cd.lot_id is null then 'UNREVIEWED'
      when cd.reviewed_at is null then 'DRAFT'
      when cd.disposition='ACCEPT_UNKNOWN_WITH_RESERVE' then 'REVIEWED_ACCEPT'
      when cd.disposition='DECLINE_UNKNOWN_CONDITION' then 'REVIEWED_DECLINE'
      else 'UNREVIEWED'
    end as condition_disposition_status,
    cd.disposition as condition_disposition,
    cd.evidence_note as condition_evidence_note,
    cd.reviewed_at as condition_reviewed_at
  from public.dashboard_lot_current d
  left join public.lot_peritaje_reviews p on p.lot_id=d.lot_id
  left join public.lot_cost_overrides c on c.lot_id=d.lot_id
  left join public.lot_condition_dispositions cd on cd.lot_id=d.lot_id
), blockers as (
  select b.*,
    array_remove(array[
      case when b.closes_at is not null and b.closes_at <= clock_timestamp() then 'CLOSED_OR_PAST' end,
      case when b.fasecolda_status is distinct from 'HIGH' then 'FASECOLDA_NOT_HIGH' end,
      case when b.commission_percent_public is null then 'COMMISSION_MISSING' end,
      case when b.peritaje_count > 0 and b.peritaje_review_status <> 'REVIEWED' then 'PERITAJE_NOT_REVIEWED' end,
      case when b.peritaje_count=0 and b.condition_disposition_status in ('UNREVIEWED','DRAFT') then 'CONDITION_RISK_UNREVIEWED' end,
      case when b.peritaje_count=0 and b.condition_disposition_status='REVIEWED_DECLINE' then 'CONDITION_RISK_DECLINED' end,
      case when not b.market_validation_available then 'MARKET_NOT_VALIDATED' end,
      case when b.cost_review_status='NO_COSTS' then 'LOT_COSTS_MISSING' end,
      case when b.completed_cost_fields < 8 then 'LOT_COSTS_INCOMPLETE' end,
      case when b.cost_review_status <> 'REVIEWED' then 'LOT_COSTS_NOT_REVIEWED' end,
      case when b.peritaje_count=0 and b.condition_disposition_status='REVIEWED_ACCEPT' and coalesce(b.condition_repair_reserve_cop,0)<=0 then 'CONDITION_REPAIR_RESERVE_MISSING' end,
      case when b.current_bid_cop is null then 'CURRENT_BID_MISSING' end
    ]::text[],null) as blockers
  from base b
)
select
  x.external_lot_id,
  x.lot_id,
  x.title,
  x.city,
  x.seller,
  x.current_bid_cop,
  x.closes_at,
  x.hours_to_close,
  x.review_state,
  x.review_score,
  x.peritaje_count,
  x.peritaje_review_status,
  x.peritaje_overall_risk,
  x.fasecolda_status,
  x.commission_percent_public,
  x.market_status,
  x.market_validation_available,
  x.cost_review_status,
  x.completed_cost_fields,
  x.costs_reviewed_at,
  x.max_bid_market_validated_cop,
  x.expected_profit_current_cop,
  x.expected_roi_current_pct,
  x.market_final_buy_recommendation_available,
  x.final_decision,
  x.blockers,
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
    when x.peritaje_count=0 and x.condition_disposition_status in ('UNREVIEWED','DRAFT') then 'REVIEW_CONDITION_RISK'
    when x.peritaje_count=0 and x.condition_disposition_status='REVIEWED_DECLINE' then 'NO_ACTION_CONDITION_DECLINED'
    when not x.market_validation_available then 'VALIDATE_MARKET'
    when x.cost_review_status='NO_COSTS' then 'ENTER_LOT_COSTS'
    when x.completed_cost_fields < 8 then 'COMPLETE_LOT_COSTS'
    when x.cost_review_status <> 'REVIEWED' then 'REVIEW_LOT_COSTS'
    when x.peritaje_count=0 and x.condition_disposition_status='REVIEWED_ACCEPT' and coalesce(x.condition_repair_reserve_cop,0)<=0 then 'REVIEW_CONDITION_RESERVE'
    when x.current_bid_cop is null then 'WAIT_CURRENT_BID'
    else 'DECISION_AVAILABLE'
  end as next_action,
  case
    when x.peritaje_count>0 then null::text
    when x.condition_disposition_status in ('UNREVIEWED','DRAFT') then 'NO_PUBLIC_PERITAJE_REQUIRES_EXPLICIT_DISPOSITION'
    when x.condition_disposition_status='REVIEWED_DECLINE' then 'NO_PUBLIC_PERITAJE_DECLINED'
    when x.condition_disposition_status='REVIEWED_ACCEPT' then 'NO_PUBLIC_PERITAJE_ACCEPTED_UNKNOWN_RISK'
    else 'NO_PUBLIC_PERITAJE_REQUIRES_EXPLICIT_DISPOSITION'
  end as evidence_warning,
  'ECONOMIC_READINESS_NOT_BUY_SIGNAL'::text as interpretation,
  d.fasecolda_match_origin,
  d.fasecolda_automatic_status,
  d.fasecolda_match_interpretation,
  x.condition_disposition_status,
  x.condition_disposition,
  x.condition_evidence_note,
  x.condition_reviewed_at,
  x.condition_repair_reserve_cop,
  'CONDITION_EVIDENCE_GATE_NOT_BUY_SIGNAL'::text as condition_interpretation
from blockers x
join public.dashboard_lot_current d on d.lot_id=x.lot_id;

revoke all on public.dashboard_economic_readiness_current from public,anon,authenticated;
grant select on public.dashboard_economic_readiness_current to service_role;

comment on view public.dashboard_economic_readiness_current is
'v0.49 economic readiness. Missing public peritaje requires explicit reviewed condition-risk disposition; accepting unknown condition also requires a positive reviewed lot repair reserve before readiness. READY_FOR_DECISION is not a buy recommendation.';

-- Preserve the v0.46 due-diligence contract and append condition provenance.
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
    when r.next_action='NO_ACTION_CONDITION_DECLINED' then 990
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
    when r.next_action='NO_ACTION_CONDITION_DECLINED' then 'CONDITION_DECLINED_NO_ACTION'
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
  r.fasecolda_match_interpretation,
  r.condition_disposition_status,
  r.condition_disposition,
  r.condition_evidence_note,
  r.condition_reviewed_at,
  r.condition_repair_reserve_cop,
  r.condition_interpretation
from public.dashboard_economic_readiness_current r
join public.dashboard_operational_queue o using(lot_id);

revoke all on public.dashboard_due_diligence_queue from public,anon,authenticated;
grant select on public.dashboard_due_diligence_queue to service_role;

create or replace view public.dashboard_condition_review_queue_v49 as
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
  r.fasecolda_status,
  r.market_validation_available,
  r.cost_review_status,
  r.completed_cost_fields,
  r.condition_disposition_status,
  r.condition_disposition,
  r.condition_evidence_note,
  r.condition_reviewed_at,
  r.condition_repair_reserve_cop,
  r.blockers,
  r.blocker_count,
  r.readiness_status,
  r.next_action,
  r.evidence_warning,
  'CONDITION_EVIDENCE_GATE_NOT_BUY_SIGNAL'::text as interpretation
from public.dashboard_economic_readiness_current r
where r.peritaje_count=0
  and r.readiness_status<>'CLOSED'
  and (
    r.condition_disposition_status in ('UNREVIEWED','DRAFT','REVIEWED_DECLINE')
    or (r.condition_disposition_status='REVIEWED_ACCEPT' and coalesce(r.condition_repair_reserve_cop,0)<=0)
  );

revoke all on public.dashboard_condition_review_queue_v49 from public,anon,authenticated;
grant select on public.dashboard_condition_review_queue_v49 to service_role;

comment on view public.dashboard_condition_review_queue_v49 is
'v0.49 operator queue for lots with no public peritaje that require explicit condition-risk disposition or a positive repair reserve. CONDITION_EVIDENCE_GATE_NOT_BUY_SIGNAL.';