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

comment on view public.dashboard_fasecolda_valuation_workbench is
'Read-only triage for Fasecolda valuation blockers. Routes cases to existing human workflows; never confirms a match, changes a search term, or produces a buy recommendation.';
