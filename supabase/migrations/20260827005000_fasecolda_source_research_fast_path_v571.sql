-- SUPERBID v0.57.1 — Fasecolda Source Research Fast Path
--
-- Purpose:
--   Preserve the v0.56 source-triage/fingerprint semantics and the v0.57
--   metadata research priority while removing the board's dependency on the
--   economic/readiness graph. This is a read-only operational optimization.
--
-- Authority boundary:
--   * no candidate resolution evidence is created;
--   * no manual Fasecolda resolution is created/changed;
--   * no market/cost/bid/ROI/final-decision field is changed;
--   * registered attachment metadata only determines navigation priority;
--   * exact-lot human review continues through the canonical v0.57 detail
--     view and the existing v0.56 disposition RPC.

create or replace view public.dashboard_fasecolda_candidate_source_triage_fast_v571 as
with base as (
  select
    l.external_lot_id,
    l.id as lot_id,
    l.title,
    l.brand,
    l.line,
    l.model_year,
    l.city,
    l.seller,
    s.displayed_price_cop as current_bid_cop,
    s.closes_at,
    fm.status as automatic_status,
    fm.search_term,
    fm.best_code as automatic_best_code,
    fm.best_description as automatic_best_description,
    fm.best_score as automatic_best_score,
    fm.second_score as automatic_second_score,
    fm.candidate_count,
    l.url as auction_url,
    public.fasecolda_hint_engine_cc_v56(l.title) as title_engine_cc,
    public.fasecolda_hint_transmission_v56(l.title) as title_transmission,
    public.fasecolda_hint_drivetrain_v56(l.title) as title_drivetrain,
    public.fasecolda_hint_fuel_v56(l.title) as title_fuel
  from public.auction_lots l
  join public.lot_fasecolda_matches fm on fm.lot_id=l.id
  left join public.lot_fasecolda_manual_resolutions mr on mr.lot_id=l.id
  left join lateral (
    select ss.displayed_price_cop,ss.closes_at
    from public.auction_snapshots ss
    where ss.lot_id=l.id
    order by ss.observed_at desc
    limit 1
  ) s on true
  where fm.status in ('AMBIGUOUS','MEDIUM')
    and mr.lot_id is null
), raw as (
  select
    b.lot_id,
    c.code,
    c.model_year as candidate_model_year,
    c.description,
    c.score,
    c.rank_no,
    c.current_value_cop,
    public.fasecolda_hint_engine_cc_v56(c.description) as candidate_engine_cc,
    public.fasecolda_hint_transmission_v56(c.description) as candidate_transmission,
    public.fasecolda_hint_drivetrain_v56(c.description) as candidate_drivetrain,
    public.fasecolda_hint_fuel_v56(c.description) as candidate_fuel,
    regexp_replace(upper(trim(coalesce(c.description,''))),'[[:space:]]+',' ','g') as normalized_description
  from base b
  join public.lot_fasecolda_candidates c on c.lot_id=b.lot_id
), candidate_stats as (
  select
    b.lot_id,
    count(r.code)::integer as current_candidate_count,
    count(distinct r.candidate_engine_cc) filter(where r.candidate_engine_cc is not null)::integer as engine_value_count,
    count(distinct r.candidate_transmission) filter(where r.candidate_transmission is not null)::integer as transmission_value_count,
    count(distinct r.candidate_drivetrain) filter(where r.candidate_drivetrain is not null)::integer as drivetrain_value_count,
    count(distinct r.candidate_fuel) filter(where r.candidate_fuel is not null)::integer as fuel_value_count,
    md5(coalesce(string_agg(
      concat_ws('~',r.code,coalesce(r.candidate_model_year::text,''),r.normalized_description,
        coalesce(round(r.score::numeric,4)::text,''),coalesce(r.current_value_cop::text,'')),
      '||' order by r.rank_no nulls last,r.code
    ),'')) as candidate_fingerprint
  from base b
  left join raw r using(lot_id)
  group by b.lot_id
), match_stats as (
  select
    b.lot_id,
    count(*) filter(
      where cs.engine_value_count>1 and b.title_engine_cc is not null and r.candidate_engine_cc is not null
        and abs(r.candidate_engine_cc-b.title_engine_cc)<=50
    )::integer as engine_match_count,
    min(r.code) filter(
      where cs.engine_value_count>1 and b.title_engine_cc is not null and r.candidate_engine_cc is not null
        and abs(r.candidate_engine_cc-b.title_engine_cc)<=50
    ) as engine_target_code,
    count(*) filter(
      where cs.transmission_value_count>1 and b.title_transmission is not null and r.candidate_transmission=b.title_transmission
    )::integer as transmission_match_count,
    min(r.code) filter(
      where cs.transmission_value_count>1 and b.title_transmission is not null and r.candidate_transmission=b.title_transmission
    ) as transmission_target_code,
    count(*) filter(
      where cs.drivetrain_value_count>1 and b.title_drivetrain is not null and r.candidate_drivetrain=b.title_drivetrain
    )::integer as drivetrain_match_count,
    min(r.code) filter(
      where cs.drivetrain_value_count>1 and b.title_drivetrain is not null and r.candidate_drivetrain=b.title_drivetrain
    ) as drivetrain_target_code,
    count(*) filter(
      where cs.fuel_value_count>1 and b.title_fuel is not null and r.candidate_fuel=b.title_fuel
    )::integer as fuel_match_count,
    min(r.code) filter(
      where cs.fuel_value_count>1 and b.title_fuel is not null and r.candidate_fuel=b.title_fuel
    ) as fuel_target_code
  from base b
  join candidate_stats cs using(lot_id)
  left join raw r using(lot_id)
  group by b.lot_id
), targets as (
  select
    b.lot_id,
    ((cs.engine_value_count>1)::integer+(cs.transmission_value_count>1)::integer+
      (cs.drivetrain_value_count>1)::integer+(cs.fuel_value_count>1)::integer)::integer as structured_discriminator_count,
    array_remove(array[
      case when ms.engine_match_count=1 then ms.engine_target_code end,
      case when ms.transmission_match_count=1 then ms.transmission_target_code end,
      case when ms.drivetrain_match_count=1 then ms.drivetrain_target_code end,
      case when ms.fuel_match_count=1 then ms.fuel_target_code end
    ],null) as unique_title_target_codes,
    ((ms.engine_match_count=1)::integer+(ms.transmission_match_count=1)::integer+
      (ms.drivetrain_match_count=1)::integer+(ms.fuel_match_count=1)::integer)::integer as unique_title_discriminator_count,
    array_remove(array[
      case when cs.engine_value_count>1 then 'ENGINE_CC' end,
      case when cs.transmission_value_count>1 then 'TRANSMISSION' end,
      case when cs.drivetrain_value_count>1 then 'DRIVETRAIN' end,
      case when cs.fuel_value_count>1 then 'FUEL' end
    ],null) as structured_discriminators,
    array_remove(array[
      case when ms.engine_match_count=1 then 'ENGINE_CC' end,
      case when ms.transmission_match_count=1 then 'TRANSMISSION' end,
      case when ms.drivetrain_match_count=1 then 'DRIVETRAIN' end,
      case when ms.fuel_match_count=1 then 'FUEL' end
    ],null) as unique_title_discriminators
  from base b
  join candidate_stats cs using(lot_id)
  join match_stats ms using(lot_id)
), target_summary as (
  select
    t.*,
    coalesce(x.distinct_target_codes,0)::integer as distinct_title_target_codes,
    x.target_code as title_unique_target_code
  from targets t
  left join lateral (
    select count(distinct u.code)::integer as distinct_target_codes,min(u.code) as target_code
    from unnest(t.unique_title_target_codes) as u(code)
  ) x on true
), duplicate_stats as (
  select
    x.lot_id,
    count(*)::integer as duplicate_description_group_count,
    sum(x.group_size)::integer as candidates_in_duplicate_description_groups
  from (
    select lot_id,normalized_description,count(*)::integer as group_size
    from raw
    group by lot_id,normalized_description
    having count(*)>1
  ) x
  group by x.lot_id
), attachment_stats as (
  select
    a.lot_id,
    count(*)::integer as attachment_count,
    count(*) filter(where upper(coalesce(a.kind,''))='PERITAJE')::integer as peritaje_count,
    md5(coalesce(string_agg(
      concat_ws('~',coalesce(a.kind,''),coalesce(a.name,''),coalesce(a.url,''),coalesce(a.source,'')),
      '||' order by a.kind nulls last,a.id
    ),'')) as attachment_fingerprint
  from public.lot_attachments a
  join base b on b.lot_id=a.lot_id
  group by a.lot_id
), classified as (
  select
    b.*,
    cs.current_candidate_count,
    cs.engine_value_count,
    cs.transmission_value_count,
    cs.drivetrain_value_count,
    cs.fuel_value_count,
    cs.candidate_fingerprint,
    ts.structured_discriminator_count,
    ts.structured_discriminators,
    ts.unique_title_discriminator_count,
    ts.unique_title_discriminators,
    ts.distinct_title_target_codes,
    ts.title_unique_target_code,
    coalesce(ds.duplicate_description_group_count,0)::integer as duplicate_description_group_count,
    coalesce(ds.candidates_in_duplicate_description_groups,0)::integer as candidates_in_duplicate_description_groups,
    coalesce(ast.attachment_count,0)::integer as attachment_count,
    coalesce(ast.peritaje_count,0)::integer as peritaje_count,
    coalesce(ast.attachment_fingerprint,md5('')) as attachment_fingerprint,
    case
      when cs.current_candidate_count=1 then 'SINGLE_CANDIDATE_LOW_CONFIDENCE'
      when ts.unique_title_discriminator_count>0 and ts.distinct_title_target_codes=1
        and not exists(
          select 1 from raw tr
          where tr.lot_id=b.lot_id and tr.code=ts.title_unique_target_code
            and exists(
              select 1 from raw other
              where other.lot_id=tr.lot_id and other.code<>tr.code
                and other.normalized_description=tr.normalized_description
            )
        ) then 'TITLE_DISCRIMINATOR_AVAILABLE'
      when ts.distinct_title_target_codes>1 then 'TITLE_PROXY_CONFLICT'
      when ts.structured_discriminator_count>0 then 'STRUCTURED_DIFFERENCE_SOURCE_UNRESOLVED'
      else 'TRIM_OR_EXTERNAL_SOURCE_REQUIRED'
    end as source_triage_class
  from base b
  join candidate_stats cs using(lot_id)
  join target_summary ts using(lot_id)
  left join duplicate_stats ds using(lot_id)
  left join attachment_stats ast using(lot_id)
), fingerprinted as (
  select
    c.*,
    md5(concat_ws('|',
      c.external_lot_id,upper(coalesce(c.title,'')),upper(coalesce(c.brand,'')),upper(coalesce(c.line,'')),coalesce(c.model_year::text,''),
      coalesce(c.automatic_status,''),coalesce(c.search_term,''),coalesce(c.automatic_best_code,''),
      coalesce(round(c.automatic_best_score::numeric,4)::text,''),coalesce(round(c.automatic_second_score::numeric,4)::text,''),
      coalesce(c.current_candidate_count::text,''),c.candidate_fingerprint,coalesce(c.auction_url,''),c.attachment_fingerprint,c.source_triage_class,
      coalesce(c.title_unique_target_code,''),coalesce(array_to_string(c.structured_discriminators,','),''),
      coalesce(array_to_string(c.unique_title_discriminators,','),'')
    )) as evidence_fingerprint
  from classified c
)
select
  f.*,
  d.disposition_action,
  d.note as disposition_note,
  d.updated_at as disposition_updated_at,
  case
    when d.lot_id is null then 'NONE'
    when d.evidence_fingerprint=f.evidence_fingerprint then 'CURRENT'
    else 'STALE'
  end as disposition_status,
  case when d.evidence_fingerprint=f.evidence_fingerprint then d.disposition_action end as current_disposition_action,
  case
    when d.evidence_fingerprint=f.evidence_fingerprint and d.disposition_action='ROUTE_TO_EVIDENCE_REVIEW' then 'EVIDENCE_REVIEW'
    when d.evidence_fingerprint=f.evidence_fingerprint and d.disposition_action='CONFIRM_CURRENT_SOURCES_INSUFFICIENT' then 'SOURCE_INSUFFICIENT_ACKNOWLEDGED'
    when d.evidence_fingerprint=f.evidence_fingerprint and d.disposition_action='REQUEST_SOURCE_RESEARCH' then 'SOURCE_RESEARCH_REQUESTED'
    when d.evidence_fingerprint=f.evidence_fingerprint and d.disposition_action='REFER_IDENTITY_REVIEW' then 'IDENTITY_REVIEW_REQUESTED'
    when d.evidence_fingerprint=f.evidence_fingerprint and d.disposition_action='REQUEST_MATCHER_RECHECK' then 'MATCHER_RECHECK_REQUESTED'
    when f.source_triage_class='TITLE_DISCRIMINATOR_AVAILABLE' then 'EVIDENCE_REVIEW'
    else 'SOURCE_TRIAGE'
  end as operational_route,
  case
    when d.evidence_fingerprint=f.evidence_fingerprint and d.disposition_action='ROUTE_TO_EVIDENCE_REVIEW' then 'Revisor confirmó que las fuentes actuales ameritan completar evidencia v0.52; no confirma el código.'
    when d.evidence_fingerprint=f.evidence_fingerprint and d.disposition_action='CONFIRM_CURRENT_SOURCES_INSUFFICIENT' then 'Fuentes actuales revisadas y declaradas insuficientes; no repetir revisión hasta que cambie el fingerprint.'
    when d.evidence_fingerprint=f.evidence_fingerprint and d.disposition_action='REQUEST_SOURCE_RESEARCH' then 'Se requiere localizar o registrar una fuente adicional antes de intentar confirmar identidad exacta.'
    when d.evidence_fingerprint=f.evidence_fingerprint and d.disposition_action='REFER_IDENTITY_REVIEW' then 'La identidad pública requiere revisión antes de continuar con homologación exacta.'
    when d.evidence_fingerprint=f.evidence_fingerprint and d.disposition_action='REQUEST_MATCHER_RECHECK' then 'Se solicitó revisar el snapshot del matcher/candidatos; no se presume resolución.'
    when d.lot_id is not null and d.evidence_fingerprint<>f.evidence_fingerprint then 'La disposición anterior quedó obsoleta porque cambió identidad, candidatos o fuentes.'
    when f.source_triage_class='TITLE_DISCRIMINATOR_AVAILABLE' then 'El título contiene un discriminador literal que apunta de forma única y coherente a un candidato; todavía requiere evidencia humana v0.52.'
    when f.source_triage_class='SINGLE_CANDIDATE_LOW_CONFIDENCE' then 'Solo existe un candidato actual pero el automático no es HIGH; el gate v0.52 no puede usar un discriminador frente a alternativas inexistentes.'
    when f.source_triage_class='TITLE_PROXY_CONFLICT' then 'Discriminadores literales del título apuntan a códigos distintos; requiere investigación humana de fuente/identidad.'
    when f.source_triage_class='STRUCTURED_DIFFERENCE_SOURCE_UNRESOLVED' then 'Los candidatos difieren estructuralmente, pero el título no identifica de forma única uno de ellos.'
    else 'Motor/caja/tracción/combustible no separan suficientemente el set actual; trim, uso, equipamiento u otra fuente deben resolver identidad.'
  end as source_triage_reason,
  'CANDIDATE_SOURCE_TRIAGE_FAST_PATH_NOT_EVIDENCE_MATCH_OR_VALUATION'::text as interpretation
from fingerprinted f
left join public.lot_fasecolda_candidate_source_dispositions d using(lot_id);

revoke all on public.dashboard_fasecolda_candidate_source_triage_fast_v571 from public,anon,authenticated;
grant select on public.dashboard_fasecolda_candidate_source_triage_fast_v571 to service_role;

create or replace view public.dashboard_fasecolda_source_research_queue_v571 as
select
  cst.external_lot_id,
  cst.lot_id,
  cst.title,
  cst.brand,
  cst.line,
  cst.model_year,
  cst.city,
  cst.seller,
  cst.current_bid_cop,
  cst.closes_at,
  cst.automatic_status,
  cst.current_candidate_count,
  cst.structured_discriminator_count,
  cst.structured_discriminators,
  cst.unique_title_discriminator_count,
  cst.unique_title_discriminators,
  cst.title_unique_target_code,
  cst.duplicate_description_group_count,
  cst.attachment_count,
  cst.peritaje_count,
  cst.source_triage_class,
  cst.evidence_fingerprint,
  cst.disposition_status,
  cst.current_disposition_action,
  cst.operational_route,
  cst.source_triage_reason,
  coalesce(inv.identity_primary_count,0)::integer as identity_primary_count,
  coalesce(inv.identity_secondary_count,0)::integer as identity_secondary_count,
  coalesce(inv.condition_identity_potential_count,0)::integer as condition_identity_potential_count,
  coalesce(inv.administrative_generic_count,0)::integer as administrative_generic_count,
  coalesce(inv.other_registered_count,0)::integer as other_registered_count,
  inv.first_review_source_name,
  inv.first_review_source_role,
  case
    when coalesce(inv.identity_primary_count,0)>0 then 'REVIEW_IDENTITY_PRIMARY_SOURCE'
    when coalesce(inv.identity_secondary_count,0)>0 then 'REVIEW_IDENTITY_SECONDARY_SOURCE'
    when coalesce(inv.condition_identity_potential_count,0)>0 then 'REVIEW_PERITAJE_FOR_IDENTITY_FACTS'
    when coalesce(inv.other_registered_count,0)>0 then 'REVIEW_OTHER_REGISTERED_SOURCE'
    else 'ACQUIRE_EXTERNAL_IDENTITY_SOURCE'
  end as research_route,
  case
    when coalesce(inv.identity_primary_count,0)>0 then 10
    when coalesce(inv.identity_secondary_count,0)>0 then 20
    when coalesce(inv.condition_identity_potential_count,0)>0 then 30
    when coalesce(inv.other_registered_count,0)>0 then 40
    else 80
  end::integer as research_rank,
  case
    when coalesce(inv.identity_primary_count,0)>0 then 'Existe anexo registrado cuya metadata sugiere fuente primaria de identidad; revisar contenido manualmente antes de registrar hechos en v0.52.'
    when coalesce(inv.identity_secondary_count,0)>0 then 'Existe anexo registrado cuya metadata sugiere fuente secundaria de identidad; revisar contenido manualmente y corroborar hechos antes de v0.52.'
    when coalesce(inv.condition_identity_potential_count,0)>0 then 'No hay fuente de identidad prioritaria, pero existe peritaje/informe técnico registrado que puede contener hechos discriminantes; inspección humana requerida.'
    when coalesce(inv.other_registered_count,0)>0 then 'Hay otras fuentes registradas no clasificadas como administrativas genéricas; revisar manualmente si contienen hechos de identidad.'
    else 'No existe fuente registrada con metadata útil para identidad exacta; se requiere adquirir o registrar una fuente externa antes de resolver.'
  end as research_reason,
  true::boolean as source_research_actionable,
  'SOURCE_RESEARCH_FAST_PATH_METADATA_ONLY_NOT_EVIDENCE_MATCH_OR_VALUATION'::text as research_interpretation
from public.dashboard_fasecolda_candidate_source_triage_fast_v571 cst
left join public.dashboard_fasecolda_attachment_research_inventory_v57 inv using(lot_id)
where cst.operational_route<>'EVIDENCE_REVIEW'
  and (cst.closes_at is null or cst.closes_at>clock_timestamp());

revoke all on public.dashboard_fasecolda_source_research_queue_v571 from public,anon,authenticated;
grant select on public.dashboard_fasecolda_source_research_queue_v571 to service_role;
