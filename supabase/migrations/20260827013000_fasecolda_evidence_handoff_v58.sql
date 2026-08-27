-- SUPERBID v0.58 — Fasecolda Evidence Handoff
--
-- Purpose:
--   Give the candidate-resolution board a live fast path derived from the
--   already-certified v0.57.1 source-triage fast path, while keeping the
--   exact-lot v0.52 evidence contract and RPC as the only authority capable
--   of creating reviewed candidate evidence / manual Fasecolda resolution.
--
-- Authority boundary:
--   * this migration creates a read-only operational queue only;
--   * operational_route=EVIDENCE_REVIEW is routing, not evidence;
--   * source/disposition metadata never selects a candidate or dimension;
--   * no market, cost, bid, ROI, final-decision or buy-signal field is written.

create or replace view public.dashboard_fasecolda_candidate_resolution_queue_v58 as
select
  f.external_lot_id,
  f.lot_id,
  f.title,
  f.brand,
  f.line,
  f.model_year,
  f.city,
  f.seller,
  f.current_bid_cop,
  f.closes_at,
  f.automatic_status,
  f.automatic_best_code,
  f.automatic_best_description,
  f.automatic_best_score,
  f.automatic_second_score,
  f.current_candidate_count::integer as candidate_count,
  'CANDIDATE_RESOLUTION'::text as workflow_target,
  10::integer as triage_rank,
  f.source_triage_reason as triage_reason,
  'BLOCKED'::text as readiness_status,
  'REVIEW_VALUATION'::text as readiness_next_action,
  case
    when f.closes_at is null then null::numeric
    else extract(epoch from (f.closes_at-clock_timestamp()))/3600.0
  end as hours_to_close,
  case
    when e.id is null then 'UNREVIEWED'
    when e.reviewed_at is null then 'DRAFT'
    else 'REVIEWED'
  end::text as evidence_status,
  e.chosen_code as evidence_chosen_code,
  coalesce(e.evidence_complete_count::integer,0) as evidence_complete_count,
  coalesce(e.match_count::integer,0) as evidence_match_count,
  coalesce(e.conflict_count::integer,0) as evidence_conflict_count,
  coalesce(e.not_stated_count::integer,0) as evidence_not_stated_count,
  coalesce(e.discriminating_match_count::integer,0) as evidence_discriminating_match_count,
  e.updated_at as evidence_updated_at,
  case
    when f.disposition_status='CURRENT'
      and f.current_disposition_action='ROUTE_TO_EVIDENCE_REVIEW'
      then 'HUMAN_SOURCE_DISPOSITION'
    else 'TITLE_DISCRIMINATOR'
  end::text as evidence_route_origin,
  f.evidence_fingerprint as source_evidence_fingerprint,
  'MANUAL_FASECOLDA_CANDIDATE_EVIDENCE_NOT_AUTOMATIC_MATCH_OR_BUY_SIGNAL'::text as evidence_interpretation,
  'CANDIDATE_EVIDENCE_FAST_QUEUE_ROUTING_NOT_EVIDENCE_MATCH_OR_BUY_SIGNAL'::text as interpretation
from public.dashboard_fasecolda_candidate_source_triage_fast_v571 f
left join public.lot_fasecolda_candidate_resolution_evidence e
  on e.lot_id=f.lot_id
where f.operational_route='EVIDENCE_REVIEW'
  and (f.closes_at is null or f.closes_at>clock_timestamp());

revoke all on public.dashboard_fasecolda_candidate_resolution_queue_v58 from public,anon,authenticated;
grant select on public.dashboard_fasecolda_candidate_resolution_queue_v58 to service_role;
