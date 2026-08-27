-- SUPERBID v0.59 — Fasecolda Resolution Workstreams
-- Routing-only control plane. It does not create matches, valuations, evidence, bids, ROI, or buy decisions.

create or replace view public.dashboard_fasecolda_resolution_workstreams_v59 as
with candidate_source as (
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
    case
      when f.closes_at is null then null::numeric
      else extract(epoch from (f.closes_at - clock_timestamp())) / 3600.0
    end as hours_to_close,
    f.automatic_status as effective_status,
    f.current_candidate_count as candidate_count,
    f.search_term as current_search_term,
    null::text as suggested_search_term,
    null::text as diagnostic_reason,
    f.source_triage_class,
    f.operational_route as source_operational_route,
    f.current_disposition_action as source_disposition_action,
    f.disposition_status as source_disposition_status,
    f.duplicate_description_group_count,
    coalesce(inv.identity_primary_count, 0) as identity_primary_count,
    coalesce(inv.identity_secondary_count, 0) as identity_secondary_count,
    coalesce(inv.condition_identity_potential_count, 0) as condition_identity_potential_count,
    coalesce(inv.other_registered_count, 0) as other_registered_count,
    inv.first_review_source_name,
    inv.first_review_source_role,
    case
      when f.operational_route = 'EVIDENCE_REVIEW' then 'CANDIDATE_EVIDENCE'
      when f.duplicate_description_group_count > 0 then 'CATALOG_INDISTINGUISHABLE'
      when coalesce(inv.identity_primary_count, 0) > 0
        or coalesce(inv.identity_secondary_count, 0) > 0
        or coalesce(inv.condition_identity_potential_count, 0) > 0
        or coalesce(inv.other_registered_count, 0) > 0
        then 'SOURCE_REGISTERED_REVIEW'
      else 'SOURCE_ACQUISITION'
    end as workstream,
    case
      when f.operational_route = 'EVIDENCE_REVIEW' then 'La fuente y el conjunto candidato permiten revisión humana de evidencia; no implica homologación.'
      when f.duplicate_description_group_count > 0 then 'Hay candidatos con descripciones normalizadas indistinguibles. Revisar catálogo/matcher antes de tratar un documento como discriminador.'
      when coalesce(inv.identity_primary_count, 0) > 0
        or coalesce(inv.identity_secondary_count, 0) > 0
        or coalesce(inv.condition_identity_potential_count, 0) > 0
        or coalesce(inv.other_registered_count, 0) > 0
        then 'Existe al menos una fuente registrada potencialmente útil para revisar identidad de forma humana.'
      else 'No hay una fuente registrada suficiente para discriminar candidatos; se requiere adquisición/investigación externa.'
    end as workstream_reason,
    case
      when f.operational_route = 'EVIDENCE_REVIEW' then 'CANDIDATE_RESOLUTION'
      else 'CANDIDATE_SOURCE_TRIAGE'
    end as workflow_target,
    case
      when f.operational_route = 'EVIDENCE_REVIEW' then 'superbid-fasecolda-candidate-cockpit'
      else 'superbid-fasecolda-source-dashboard'
    end as workflow_function
  from public.dashboard_fasecolda_candidate_source_triage_fast_v571 f
  left join lateral (
    select
      count(*) filter (where x.metadata_role = 'IDENTITY_PRIMARY')::integer as identity_primary_count,
      count(*) filter (where x.metadata_role = 'IDENTITY_SECONDARY')::integer as identity_secondary_count,
      count(*) filter (where x.metadata_role = 'CONDITION_IDENTITY_POTENTIAL')::integer as condition_identity_potential_count,
      count(*) filter (where x.metadata_role = 'OTHER_REGISTERED')::integer as other_registered_count,
      (array_agg(x.name order by x.metadata_rank, x.id))[1] as first_review_source_name,
      (array_agg(x.metadata_role order by x.metadata_rank, x.id))[1] as first_review_source_role
    from (
      select
        a.id,
        a.name,
        public.fasecolda_source_metadata_role_v57(a.kind, a.name) as metadata_role,
        public.fasecolda_source_metadata_rank_v57(a.kind, a.name) as metadata_rank
      from public.lot_attachments a
      where a.lot_id = f.lot_id
    ) x
  ) inv on true
  where f.closes_at is null or f.closes_at > clock_timestamp()
),
search_year as (
  select
    l.external_lot_id,
    l.id as lot_id,
    l.title,
    l.brand,
    l.line,
    l.model_year,
    l.city,
    l.seller,
    snap.displayed_price_cop as current_bid_cop,
    snap.closes_at,
    case
      when snap.closes_at is null then null::numeric
      else extract(epoch from (snap.closes_at - clock_timestamp())) / 3600.0
    end as hours_to_close,
    coalesce(e.status, 'NO_MATCH_ROW') as effective_status,
    coalesce(e.candidate_count, 0) as candidate_count,
    e.search_term as current_search_term,
    public.fasecolda_suggest_search_term(l.title) as suggested_search_term,
    case
      when e.lot_id is null then 'NO_MATCH_ROW'
      when e.status = 'UNMATCHED'
        and public.fasecolda_suggest_search_term(l.title) is not null
        and public.fasecolda_suggest_search_term(l.title) is distinct from e.search_term
        then 'SEARCH_TERM_CAN_BE_EXPANDED'
      when e.status = 'UNMATCHED' and coalesce(e.note, '') ilike '%model year%'
        then 'NO_YEAR_COMPATIBLE_REFERENCE'
      when e.status = 'UNMATCHED' and coalesce(e.note, '') ilike '%no codes%'
        then 'PUBLIC_SEARCH_RETURNED_NO_CODES'
      else 'UNMATCHED_OTHER'
    end as diagnostic_reason,
    null::text as source_triage_class,
    null::text as source_operational_route,
    null::text as source_disposition_action,
    null::text as source_disposition_status,
    0::integer as duplicate_description_group_count,
    0::integer as identity_primary_count,
    0::integer as identity_secondary_count,
    0::integer as condition_identity_potential_count,
    0::integer as other_registered_count,
    null::text as first_review_source_name,
    null::text as first_review_source_role,
    case
      when e.lot_id is null then 'SEARCH_REVIEW'
      when e.status = 'UNMATCHED'
        and public.fasecolda_suggest_search_term(l.title) is not null
        and public.fasecolda_suggest_search_term(l.title) is distinct from e.search_term
        then 'SEARCH_REVIEW'
      when e.status = 'UNMATCHED' and coalesce(e.note, '') ilike '%model year%'
        then 'YEAR_REVIEW'
      else 'SEARCH_REVIEW'
    end as workstream,
    case
      when e.lot_id is null then 'No existe fila efectiva de homologación; revisar el término de búsqueda sin inferir una referencia.'
      when e.status = 'UNMATCHED'
        and public.fasecolda_suggest_search_term(l.title) is not null
        and public.fasecolda_suggest_search_term(l.title) is distinct from e.search_term
        then 'Existe un término sugerido distinto al vigente; requiere revisión humana del término.'
      when e.status = 'UNMATCHED' and coalesce(e.note, '') ilike '%model year%'
        then 'La búsqueda no encontró una referencia compatible con el año; revisar evidencia/cobertura de año.'
      else 'La búsqueda pública sigue sin resolver la referencia; revisar el workflow de término.'
    end as workstream_reason,
    case
      when e.status = 'UNMATCHED' and coalesce(e.note, '') ilike '%model year%'
        and not (
          public.fasecolda_suggest_search_term(l.title) is not null
          and public.fasecolda_suggest_search_term(l.title) is distinct from e.search_term
        ) then 'YEAR_REFERENCE_REVIEW'
      else 'SEARCH_TERM_WORKFLOW'
    end as workflow_target,
    case
      when e.status = 'UNMATCHED' and coalesce(e.note, '') ilike '%model year%'
        and not (
          public.fasecolda_suggest_search_term(l.title) is not null
          and public.fasecolda_suggest_search_term(l.title) is distinct from e.search_term
        ) then 'superbid-fasecolda-year-dashboard'
      else 'superbid-fasecolda-search-dashboard'
    end as workflow_function
  from public.auction_lots l
  left join public.lot_fasecolda_effective_current e on e.lot_id = l.id
  left join lateral (
    select s.displayed_price_cop, s.closes_at
    from public.auction_snapshots s
    where s.lot_id = l.id
    order by s.observed_at desc
    limit 1
  ) snap on true
  where (snap.closes_at is null or snap.closes_at > clock_timestamp())
    and coalesce(e.status, 'NO_MATCH_ROW') in ('UNMATCHED', 'NO_MATCH_ROW')
),
combined as (
  select * from candidate_source
  union all
  select * from search_year
)
select
  c.*,
  case c.workstream
    when 'CANDIDATE_EVIDENCE' then 10
    when 'SOURCE_REGISTERED_REVIEW' then 20
    when 'SEARCH_REVIEW' then 30
    when 'YEAR_REVIEW' then 40
    when 'SOURCE_ACQUISITION' then 60
    when 'CATALOG_INDISTINGUISHABLE' then 90
    else 99
  end as workstream_rank,
  'FASECOLDA_RESOLUTION_WORKSTREAM_ROUTING_NOT_MATCH_VALUATION_OR_BUY_SIGNAL'::text as interpretation
from combined c;

revoke all on public.dashboard_fasecolda_resolution_workstreams_v59 from public, anon, authenticated;
grant select on public.dashboard_fasecolda_resolution_workstreams_v59 to service_role;

comment on view public.dashboard_fasecolda_resolution_workstreams_v59 is
'v0.59 routing-only Fasecolda control plane. Human/source/search/year workstreams only; not a match, valuation, economic readiness result, bid recommendation, or buy signal.';
