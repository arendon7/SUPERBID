create or replace view public.dashboard_fasecolda_year_reference_diagnostics as
with q as (
  select
    d.external_lot_id,
    d.lot_id,
    d.title,
    d.brand as stored_brand,
    d.line as stored_line,
    d.model_year,
    d.city,
    d.seller,
    d.review_state,
    d.review_score,
    d.current_search_term,
    split_part(d.current_search_term,' ',1) as term_brand,
    trim(regexp_replace(d.current_search_term,'^[^ ]+\s+','')) as line_term
  from public.dashboard_fasecolda_unmatched_diagnostics d
  where d.diagnostic_reason='NO_YEAR_COMPATIBLE_REFERENCE'
), refs as (
  select
    q.lot_id,
    f.code,
    f.brand as reference_brand,
    f.model_year as reference_year,
    f.value_cop,
    concat_ws(' ',f.reference1,f.reference2,f.reference3) as reference_description,
    f.source_file,
    f.imported_at
  from q
  join public.fasecolda_values f
    on upper(f.brand)=upper(q.term_brand)
   and position(upper(q.line_term) in upper(concat_ws(' ',f.reference1,f.reference2,f.reference3)))>0
), years as (
  select
    q.*,
    count(r.code) as reference_row_count,
    count(distinct r.code) as reference_code_count,
    array_agg(distinct r.reference_year order by r.reference_year) filter (where r.reference_year is not null) as available_years,
    count(r.code) filter (where r.reference_year=q.model_year) as same_year_row_count,
    max(r.reference_year) filter (where r.reference_year<q.model_year) as nearest_lower_year,
    min(r.reference_year) filter (where r.reference_year>q.model_year) as nearest_upper_year,
    max(r.imported_at) as evidence_imported_at
  from q
  left join refs r using(lot_id)
  group by q.external_lot_id,q.lot_id,q.title,q.stored_brand,q.stored_line,q.model_year,q.city,q.seller,q.review_state,q.review_score,q.current_search_term,q.term_brand,q.line_term
)
select
  y.external_lot_id,
  y.lot_id,
  y.title,
  y.stored_brand,
  y.stored_line,
  y.term_brand,
  y.line_term,
  y.model_year,
  y.city,
  y.seller,
  y.review_state,
  y.review_score,
  y.current_search_term,
  y.reference_row_count,
  y.reference_code_count,
  y.available_years,
  y.same_year_row_count,
  y.nearest_lower_year,
  case when y.nearest_lower_year is null then null else y.model_year-y.nearest_lower_year end as lower_year_distance,
  min(r.value_cop) filter (where r.reference_year=y.nearest_lower_year) as nearest_lower_min_value_cop,
  max(r.value_cop) filter (where r.reference_year=y.nearest_lower_year) as nearest_lower_max_value_cop,
  array_agg(distinct r.code order by r.code) filter (where r.reference_year=y.nearest_lower_year) as nearest_lower_codes,
  y.nearest_upper_year,
  case when y.nearest_upper_year is null then null else y.nearest_upper_year-y.model_year end as upper_year_distance,
  min(r.value_cop) filter (where r.reference_year=y.nearest_upper_year) as nearest_upper_min_value_cop,
  max(r.value_cop) filter (where r.reference_year=y.nearest_upper_year) as nearest_upper_max_value_cop,
  array_agg(distinct r.code order by r.code) filter (where r.reference_year=y.nearest_upper_year) as nearest_upper_codes,
  y.evidence_imported_at,
  case
    when upper(y.stored_brand)<>upper(y.term_brand) then 'STORED_BRAND_DIFFERS_FROM_SEARCH_TERM'
    when y.reference_row_count=0 then 'LINE_NOT_PRESENT_IN_IMPORTED_VALUES'
    when y.same_year_row_count>0 then 'SAME_YEAR_REFERENCE_EXISTS_DIAGNOSTIC_STALE'
    when y.nearest_lower_year is not null and y.nearest_upper_year is not null then 'YEAR_GAP_BETWEEN_REFERENCES'
    when y.nearest_lower_year is not null then 'ONLY_OLDER_REFERENCES'
    when y.nearest_upper_year is not null then 'ONLY_NEWER_REFERENCES'
    else 'REFERENCE_YEARS_UNAVAILABLE'
  end as year_reference_reason,
  case
    when upper(y.stored_brand)<>upper(y.term_brand) then 10
    when y.same_year_row_count>0 then 15
    when y.nearest_lower_year is not null and y.nearest_upper_year is not null then 20
    when y.nearest_lower_year is not null then 30
    when y.nearest_upper_year is not null then 40
    when y.reference_row_count=0 then 50
    else 60
  end as diagnostic_rank,
  case
    when upper(y.stored_brand)<>upper(y.term_brand) then 'REVIEW_BRAND_IDENTITY'
    when y.same_year_row_count>0 then 'RECHECK_MATCHER_FRESHNESS'
    when y.nearest_lower_year is not null and y.nearest_upper_year is not null then 'REVIEW_YEAR_GAP_EVIDENCE'
    when y.nearest_lower_year is not null then 'REVIEW_OLDER_REFERENCE_EVIDENCE'
    when y.nearest_upper_year is not null then 'REVIEW_NEWER_REFERENCE_EVIDENCE'
    else 'REVIEW_SOURCE_COVERAGE'
  end as next_action,
  'FASECOLDA_YEAR_REFERENCE_DIAGNOSTIC_NOT_VALUATION'::text as interpretation
from years y
left join refs r using(lot_id)
group by y.external_lot_id,y.lot_id,y.title,y.stored_brand,y.stored_line,y.term_brand,y.line_term,y.model_year,y.city,y.seller,y.review_state,y.review_score,y.current_search_term,y.reference_row_count,y.reference_code_count,y.available_years,y.same_year_row_count,y.nearest_lower_year,y.nearest_upper_year,y.evidence_imported_at;

revoke all on public.dashboard_fasecolda_year_reference_diagnostics from public, anon, authenticated;
grant select on public.dashboard_fasecolda_year_reference_diagnostics to service_role;
comment on view public.dashboard_fasecolda_year_reference_diagnostics is
'Read-only evidence for NO_YEAR_COMPATIBLE_REFERENCE cases. Adjacent-year values are direct Fasecolda observations only; they are never interpolated, carried forward/back, or treated as a valuation for the lot year.';

create or replace view public.dashboard_fasecolda_valuation_workbench as
select
  d.external_lot_id,
  d.lot_id,
  d.title,
  d.brand,
  d.line,
  d.model_year,
  d.city,
  d.seller,
  d.current_bid_cop,
  d.closes_at,
  d.hours_to_close,
  d.review_state,
  d.review_score,
  er.readiness_status,
  er.next_action as readiness_next_action,
  coalesce(ef.status, ud.effective_status, 'NO_MATCH_ROW') as effective_status,
  ef.automatic_status,
  ef.match_origin,
  ef.search_term,
  ef.search_term_origin,
  ef.search_term_override,
  ef.best_code,
  ef.best_description,
  ef.best_score,
  ef.second_score,
  coalesce(rq.candidate_count, ud.candidate_count, ef.candidate_count, 0) as candidate_count,
  coalesce(rq.manual_resolution_status, 'UNRESOLVED') as manual_resolution_status,
  ud.diagnostic_reason,
  ud.current_search_term,
  ud.suggested_search_term,
  ud.suggestion_differs,
  case
    when er.readiness_status = 'CLOSED' then 'NO_ACTION_CLOSED'
    when coalesce(ef.status, ud.effective_status) in ('AMBIGUOUS','MEDIUM') then 'CANDIDATE_RESOLUTION'
    when ud.diagnostic_reason in ('SEARCH_TERM_CAN_BE_EXPANDED','NO_MATCH_ROW','PUBLIC_SEARCH_RETURNED_NO_CODES','UNMATCHED_OTHER') then 'SEARCH_TERM_WORKFLOW'
    when ud.diagnostic_reason = 'NO_YEAR_COMPATIBLE_REFERENCE' then 'YEAR_REFERENCE_REVIEW'
    else 'VALUATION_REVIEW_OTHER'
  end as workflow_target,
  case
    when er.readiness_status = 'CLOSED' then 900
    when coalesce(ef.status, ud.effective_status) in ('AMBIGUOUS','MEDIUM') and coalesce(rq.candidate_count,0) between 1 and 3 then 10
    when coalesce(ef.status, ud.effective_status) in ('AMBIGUOUS','MEDIUM') then 20
    when ud.diagnostic_reason = 'SEARCH_TERM_CAN_BE_EXPANDED' then 30
    when ud.diagnostic_reason = 'NO_MATCH_ROW' then 40
    when ud.diagnostic_reason = 'PUBLIC_SEARCH_RETURNED_NO_CODES' then 45
    when ud.diagnostic_reason = 'NO_YEAR_COMPATIBLE_REFERENCE' then 50
    else 60
  end as triage_rank,
  case
    when er.readiness_status = 'CLOSED' then 'Lote cerrado; no requiere trabajo operativo de valoración.'
    when coalesce(ef.status, ud.effective_status) in ('AMBIGUOUS','MEDIUM') and coalesce(rq.candidate_count,0) between 1 and 3 then 'Pocos candidatos públicos: revisión humana acotada.'
    when coalesce(ef.status, ud.effective_status) in ('AMBIGUOUS','MEDIUM') then 'El matcher produjo candidatos pero no evidencia suficiente para HIGH.'
    when ud.diagnostic_reason = 'SEARCH_TERM_CAN_BE_EXPANDED' then 'El término derivado puede ampliarse y debe probarse antes de cualquier override.'
    when ud.diagnostic_reason = 'NO_MATCH_ROW' then 'No existe fila de match; revisar término y fuente pública.'
    when ud.diagnostic_reason = 'PUBLIC_SEARCH_RETURNED_NO_CODES' then 'La búsqueda pública no devolvió códigos para el término actual.'
    when ud.diagnostic_reason = 'NO_YEAR_COMPATIBLE_REFERENCE' then 'Hay códigos/candidatos, pero no referencia utilizable para el año del vehículo.'
    else 'Bloqueo de valoración no cubierto por un workflow especializado.'
  end as triage_reason,
  case
    when coalesce(ef.status, ud.effective_status) in ('AMBIGUOUS','MEDIUM') then 'superbid-fasecolda-dashboard'
    when ud.diagnostic_reason = 'NO_YEAR_COMPATIBLE_REFERENCE' then 'superbid-fasecolda-year-dashboard'
    when ud.diagnostic_reason is not null then 'superbid-fasecolda-search-dashboard'
    else 'superbid-readiness-dashboard'
  end as workflow_function,
  'FASECOLDA_VALUATION_TRIAGE_NOT_MATCH'::text as interpretation
from public.dashboard_lot_current d
join public.dashboard_economic_readiness_current er using (lot_id)
left join public.lot_fasecolda_effective_current ef using (lot_id)
left join public.dashboard_fasecolda_resolution_queue rq using (lot_id)
left join public.dashboard_fasecolda_unmatched_diagnostics ud using (lot_id)
where er.next_action = 'REVIEW_VALUATION';

revoke all on public.dashboard_fasecolda_valuation_workbench from public, anon, authenticated;
grant select on public.dashboard_fasecolda_valuation_workbench to service_role;
