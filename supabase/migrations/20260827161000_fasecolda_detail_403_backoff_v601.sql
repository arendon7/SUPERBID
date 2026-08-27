-- SUPERBID v0.60.1 — Fasecolda detail 4xx backoff
-- Operational resilience only. This migration does not create or confirm search-term
-- overrides, matches, candidates, valuations, bids, ROI, or buy decisions.

create or replace function public.fasecolda_detail_retry_class_v601(
  p_http_status integer,
  p_payload_valid boolean
) returns text
language sql
immutable
set search_path=public,extensions,pg_catalog
as $$
  select case
    when p_http_status = 200 and p_payload_valid is true then 'VALID'
    when p_http_status = 200 then 'INVALID_NONRETRYABLE'
    when p_http_status = 403 then 'FORBIDDEN_NONRETRYABLE'
    when p_http_status between 400 and 499 and p_http_status not in (408,425,429)
      then 'REJECTED_NONRETRYABLE'
    when p_http_status is null
      or p_http_status in (408,425,429)
      or p_http_status between 500 and 599
      then 'UNAVAILABLE_RETRYABLE'
    else 'UNAVAILABLE_RETRYABLE'
  end;
$$;

revoke all on function public.fasecolda_detail_retry_class_v601(integer,boolean)
  from public,anon,authenticated;
grant execute on function public.fasecolda_detail_retry_class_v601(integer,boolean)
  to service_role;

create or replace view public.dashboard_fasecolda_search_evidence_queue_v601 as
select
  q.*,
  public.fasecolda_detail_retry_class_v601(
    q.evidence_detail_http_status,
    q.evidence_detail_payload_valid
  ) as detail_retry_class_v601,
  case
    when q.input_disposition='IDENTITY_INPUT_REVIEW' then 'IDENTITY_INPUT_REVIEW'
    when q.input_disposition='MISSING_YEAR' then 'MISSING_YEAR'
    when q.evidence_observed_at is null then 'SUGGESTED_EVIDENCE_MISSING'
    when not q.evidence_fresh then 'SUGGESTED_EVIDENCE_STALE'
    when coalesce(q.evidence_code_count,0)=0 then 'SUGGESTED_NO_CODES'
    when public.fasecolda_detail_retry_class_v601(q.evidence_detail_http_status,q.evidence_detail_payload_valid)='FORBIDDEN_NONRETRYABLE'
      then 'SUGGESTED_DETAIL_FORBIDDEN'
    when public.fasecolda_detail_retry_class_v601(q.evidence_detail_http_status,q.evidence_detail_payload_valid)='INVALID_NONRETRYABLE'
      then 'SUGGESTED_DETAIL_INVALID'
    when public.fasecolda_detail_retry_class_v601(q.evidence_detail_http_status,q.evidence_detail_payload_valid)='REJECTED_NONRETRYABLE'
      then 'SUGGESTED_DETAIL_REJECTED'
    when public.fasecolda_detail_retry_class_v601(q.evidence_detail_http_status,q.evidence_detail_payload_valid)='UNAVAILABLE_RETRYABLE'
      then 'SUGGESTED_DETAIL_UNAVAILABLE'
    when q.year_compatible_code_count=0 then 'SUGGESTED_NO_YEAR_COMPATIBLE_CODES'
    else 'SUGGESTED_YEAR_COMPATIBLE_CODES'
  end as evidence_state_v601,
  case
    when q.input_disposition='IDENTITY_INPUT_REVIEW' then 'REVIEW_IDENTITY_INPUT'
    when q.input_disposition='MISSING_YEAR' then 'REVIEW_MODEL_YEAR_INPUT'
    when q.evidence_observed_at is null or not q.evidence_fresh then 'REFRESH_SUGGESTED_EVIDENCE'
    when coalesce(q.evidence_code_count,0)=0 then 'EXPLORE_ALTERNATE_VARIANTS'
    when public.fasecolda_detail_retry_class_v601(q.evidence_detail_http_status,q.evidence_detail_payload_valid)
      in ('FORBIDDEN_NONRETRYABLE','INVALID_NONRETRYABLE','REJECTED_NONRETRYABLE')
      then 'OPEN_HUMAN_SEARCH'
    when public.fasecolda_detail_retry_class_v601(q.evidence_detail_http_status,q.evidence_detail_payload_valid)='UNAVAILABLE_RETRYABLE'
      then 'REFRESH_SUGGESTED_EVIDENCE'
    when q.year_compatible_code_count=0 then 'REVIEW_YEAR_OR_ALTERNATE_TERM'
    else 'REVIEW_SUGGESTED_TERM'
  end as operator_next_action_v601,
  case
    when q.input_disposition='EXPLORABLE'
      and q.evidence_fresh
      and public.fasecolda_detail_retry_class_v601(q.evidence_detail_http_status,q.evidence_detail_payload_valid)='VALID'
      and q.year_compatible_code_count>0
      then true else false
  end as suggested_term_reviewable_v601,
  case
    when q.input_disposition='IDENTITY_INPUT_REVIEW' then 10
    when q.input_disposition='MISSING_YEAR' then 15
    when q.evidence_observed_at is null then 20
    when not q.evidence_fresh then 25
    when public.fasecolda_detail_retry_class_v601(q.evidence_detail_http_status,q.evidence_detail_payload_valid)='VALID'
      and q.year_compatible_code_count>0 then 30
    when public.fasecolda_detail_retry_class_v601(q.evidence_detail_http_status,q.evidence_detail_payload_valid)='VALID'
      and q.year_compatible_code_count=0 then 40
    when coalesce(q.evidence_code_count,0)=0 then 50
    when public.fasecolda_detail_retry_class_v601(q.evidence_detail_http_status,q.evidence_detail_payload_valid)
      in ('FORBIDDEN_NONRETRYABLE','INVALID_NONRETRYABLE','REJECTED_NONRETRYABLE') then 55
    else 60
  end as evidence_state_rank_v601,
  'FASECOLDA_DETAIL_4XX_BACKOFF_NOT_MATCH_OR_BUY_SIGNAL'::text as v601_interpretation
from public.dashboard_fasecolda_search_evidence_queue_v60 q;

revoke all on public.dashboard_fasecolda_search_evidence_queue_v601
  from public,anon,authenticated;
grant select on public.dashboard_fasecolda_search_evidence_queue_v601 to service_role;

comment on view public.dashboard_fasecolda_search_evidence_queue_v601 is
'v0.60.1 operational wrapper over v0.60 search evidence. Fresh non-retryable detail responses (including HTTP 403) route to human Search instead of repeated refresh. Stale evidence becomes refreshable again after the existing 24h freshness window. No match, override, valuation, bid, ROI, or buy authority.';