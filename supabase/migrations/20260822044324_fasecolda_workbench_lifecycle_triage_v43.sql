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
  coalesce(ef.status,ud.effective_status,'NO_MATCH_ROW') as effective_status,
  ef.automatic_status,
  ef.match_origin,
  ef.search_term,
  ef.search_term_origin,
  ef.search_term_override,
  ef.best_code,
  ef.best_description,
  ef.best_score,
  ef.second_score,
  coalesce(rq.candidate_count,ud.candidate_count,ef.candidate_count,0) as candidate_count,
  coalesce(rq.manual_resolution_status,'UNRESOLVED') as manual_resolution_status,
  ud.diagnostic_reason,
  ud.current_search_term,
  ud.suggested_search_term,
  ud.suggestion_differs,
  case
    when er.readiness_status='CLOSED' then 'NO_ACTION_CLOSED'
    when coalesce(ef.status,ud.effective_status) in ('AMBIGUOUS','MEDIUM') then 'CANDIDATE_RESOLUTION'
    when ud.diagnostic_reason in ('SEARCH_TERM_CAN_BE_EXPANDED','NO_MATCH_ROW','PUBLIC_SEARCH_RETURNED_NO_CODES','UNMATCHED_OTHER') then 'SEARCH_TERM_WORKFLOW'
    when ud.diagnostic_reason='NO_YEAR_COMPATIBLE_REFERENCE' and yrs.disposition_action='CONFIRM_COVERAGE_GAP' and ylc.evidence_review_status='DISPOSITION_CURRENT' then 'KNOWN_YEAR_COVERAGE_GAP'
    when ud.diagnostic_reason='NO_YEAR_COMPATIBLE_REFERENCE' and ylc.evidence_review_status='REVIEW_REQUIRED' then 'YEAR_EVIDENCE_REVIEW'
    when ud.diagnostic_reason='NO_YEAR_COMPATIBLE_REFERENCE' and yrs.disposition_action='REQUEST_SOURCE_REFRESH' then 'YEAR_SOURCE_REFRESH_REQUESTED'
    when ud.diagnostic_reason='NO_YEAR_COMPATIBLE_REFERENCE' and yrs.disposition_action='REFER_IDENTITY_REVIEW' then 'YEAR_IDENTITY_REVIEW'
    when ud.diagnostic_reason='NO_YEAR_COMPATIBLE_REFERENCE' and yrs.disposition_action='REQUEST_MATCHER_RECHECK' then 'YEAR_MATCHER_RECHECK'
    when ud.diagnostic_reason='NO_YEAR_COMPATIBLE_REFERENCE' then 'YEAR_REFERENCE_REVIEW'
    else 'VALUATION_REVIEW_OTHER'
  end as workflow_target,
  case
    when er.readiness_status='CLOSED' then 900
    when coalesce(ef.status,ud.effective_status) in ('AMBIGUOUS','MEDIUM') and coalesce(rq.candidate_count,0) between 1 and 3 then 10
    when coalesce(ef.status,ud.effective_status) in ('AMBIGUOUS','MEDIUM') then 20
    when ud.diagnostic_reason='NO_YEAR_COMPATIBLE_REFERENCE' and ylc.evidence_review_status='REVIEW_REQUIRED' then 25
    when ud.diagnostic_reason='SEARCH_TERM_CAN_BE_EXPANDED' then 30
    when ud.diagnostic_reason='NO_YEAR_COMPATIBLE_REFERENCE' and yrs.disposition_action='REFER_IDENTITY_REVIEW' then 32
    when ud.diagnostic_reason='NO_YEAR_COMPATIBLE_REFERENCE' and yrs.disposition_action='REQUEST_MATCHER_RECHECK' then 33
    when ud.diagnostic_reason='NO_YEAR_COMPATIBLE_REFERENCE' and yrs.disposition_action='REQUEST_SOURCE_REFRESH' then 35
    when ud.diagnostic_reason='NO_MATCH_ROW' then 40
    when ud.diagnostic_reason='PUBLIC_SEARCH_RETURNED_NO_CODES' then 45
    when ud.diagnostic_reason='NO_YEAR_COMPATIBLE_REFERENCE' and yrs.disposition_action='CONFIRM_COVERAGE_GAP' and ylc.evidence_review_status='DISPOSITION_CURRENT' then 85
    when ud.diagnostic_reason='NO_YEAR_COMPATIBLE_REFERENCE' then 50
    else 60
  end as triage_rank,
  case
    when er.readiness_status='CLOSED' then 'Lote cerrado; no requiere trabajo operativo de valoración.'
    when coalesce(ef.status,ud.effective_status) in ('AMBIGUOUS','MEDIUM') and coalesce(rq.candidate_count,0) between 1 and 3 then 'Pocos candidatos públicos: revisión humana acotada.'
    when coalesce(ef.status,ud.effective_status) in ('AMBIGUOUS','MEDIUM') then 'El matcher produjo candidatos pero no evidencia suficiente para HIGH.'
    when ud.diagnostic_reason='NO_YEAR_COMPATIBLE_REFERENCE' and ylc.evidence_review_status='REVIEW_REQUIRED' then 'La evidencia Fasecolda del vehículo/año es nueva, cambió o reapareció y requiere revisión humana.'
    when ud.diagnostic_reason='SEARCH_TERM_CAN_BE_EXPANDED' then 'El término derivado puede ampliarse y debe probarse antes de cualquier override.'
    when ud.diagnostic_reason='NO_YEAR_COMPATIBLE_REFERENCE' and yrs.disposition_action='REFER_IDENTITY_REVIEW' then 'La revisión humana derivó este caso a identidad; sigue bloqueado hasta resolverla.'
    when ud.diagnostic_reason='NO_YEAR_COMPATIBLE_REFERENCE' and yrs.disposition_action='REQUEST_MATCHER_RECHECK' then 'Existe una solicitud humana de recheck del matcher; no se presume resolución.'
    when ud.diagnostic_reason='NO_YEAR_COMPATIBLE_REFERENCE' and yrs.disposition_action='REQUEST_SOURCE_REFRESH' then 'Existe una solicitud humana de actualización de la fuente Fasecolda.'
    when ud.diagnostic_reason='NO_MATCH_ROW' then 'No existe fila de match; revisar término y fuente pública.'
    when ud.diagnostic_reason='PUBLIC_SEARCH_RETURNED_NO_CODES' then 'La búsqueda pública no devolvió códigos para el término actual.'
    when ud.diagnostic_reason='NO_YEAR_COMPATIBLE_REFERENCE' and yrs.disposition_action='CONFIRM_COVERAGE_GAP' and ylc.evidence_review_status='DISPOSITION_CURRENT' then 'Gap de cobertura confirmado para el fingerprint vigente; no requiere repetición hasta que cambie la evidencia, pero el readiness económico sigue bloqueado.'
    when ud.diagnostic_reason='NO_YEAR_COMPATIBLE_REFERENCE' then 'Hay códigos/candidatos, pero no referencia utilizable para el año del vehículo.'
    else 'Bloqueo de valoración no cubierto por un workflow especializado.'
  end as triage_reason,
  case
    when coalesce(ef.status,ud.effective_status) in ('AMBIGUOUS','MEDIUM') then 'superbid-fasecolda-dashboard'
    when ud.diagnostic_reason='NO_YEAR_COMPATIBLE_REFERENCE' and yrs.disposition_action='CONFIRM_COVERAGE_GAP' and ylc.evidence_review_status='DISPOSITION_CURRENT' then 'superbid-fasecolda-evidence-dashboard'
    when ud.diagnostic_reason='NO_YEAR_COMPATIBLE_REFERENCE' then 'superbid-fasecolda-year-dashboard'
    when ud.diagnostic_reason is not null then 'superbid-fasecolda-search-dashboard'
    else 'superbid-readiness-dashboard'
  end as workflow_function,
  'FASECOLDA_VALUATION_TRIAGE_NOT_MATCH'::text as interpretation,
  yrs.case_key as year_case_key,
  yrs.year_reference_reason,
  yrs.disposition_action as year_disposition_action,
  yrs.operational_status as year_operational_status,
  ylc.logical_key as year_logical_key,
  ylc.evidence_event_type as year_evidence_event_type,
  ylc.evidence_review_status as year_evidence_review_status,
  ylc.lifecycle_next_action as year_lifecycle_next_action
from public.dashboard_lot_current d
join public.dashboard_economic_readiness_current er using(lot_id)
left join public.lot_fasecolda_effective_current ef using(lot_id)
left join public.dashboard_fasecolda_resolution_queue rq using(lot_id)
left join public.dashboard_fasecolda_unmatched_diagnostics ud using(lot_id)
left join public.dashboard_fasecolda_year_reference_lot_status yrs using(lot_id)
left join public.dashboard_fasecolda_year_reference_evidence_lifecycle ylc on ylc.case_key=yrs.case_key
where er.next_action='REVIEW_VALUATION';

revoke all on public.dashboard_fasecolda_valuation_workbench from public,anon,authenticated;
grant select on public.dashboard_fasecolda_valuation_workbench to service_role;

comment on view public.dashboard_fasecolda_valuation_workbench is
'Human valuation triage. v0.43 uses Fasecolda year-evidence lifecycle only to prioritize workflow. Confirmed unchanged gaps are deprioritized but remain economically blocked. Lifecycle never creates a match or valuation.';
