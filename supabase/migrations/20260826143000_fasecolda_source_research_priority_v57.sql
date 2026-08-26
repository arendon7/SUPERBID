-- SUPERBID v0.57 · Fasecolda Source Research Priority
-- Metadata-only prioritization for already registered lot sources.
-- It does not read document contents, create evidence, confirm a candidate, write valuation,
-- change readiness, or produce a buy signal.

create or replace function public.fasecolda_source_metadata_role_v57(p_kind text,p_name text)
returns text
language sql
immutable
set search_path=pg_catalog
as $$
  select case
    when lower(coalesce(p_name,'')) ~ '(matricul|tarjeta[ _-]*propiedad|certificad.*(tradicion|tradición|libertad)|licencia.*transito|licencia.*tránsito|registro.*vehicul)' then 'IDENTITY_PRIMARY'
    when lower(coalesce(p_name,'')) ~ '(^|[^a-z0-9])(soat|rtm|tp)([^a-z0-9]|$)'
      or lower(coalesce(p_name,'')) ~ '(revision.*tecn|revisión.*técn|informe.*tecn|informe.*técn)' then 'IDENTITY_SECONDARY'
    when upper(coalesce(p_kind,''))='PERITAJE'
      or lower(coalesce(p_name,'')) ~ '(peritaje|inspeccion|inspección)' then 'CONDITION_IDENTITY_POTENTIAL'
    when lower(coalesce(p_name,'')) ~ '(sagrilaft|sarlaft|habeas|contrato.*compraventa|acta.*compromiso|prevencion.*laft|prevención.*laft|formato[- _]*[bc]\.pdf)' then 'ADMINISTRATIVE_GENERIC'
    else 'OTHER_REGISTERED'
  end
$$;

create or replace function public.fasecolda_source_metadata_rank_v57(p_kind text,p_name text)
returns integer
language sql
immutable
set search_path=pg_catalog
as $$
  select case public.fasecolda_source_metadata_role_v57(p_kind,p_name)
    when 'IDENTITY_PRIMARY' then 10
    when 'IDENTITY_SECONDARY' then 20
    when 'CONDITION_IDENTITY_POTENTIAL' then 30
    when 'OTHER_REGISTERED' then 40
    when 'ADMINISTRATIVE_GENERIC' then 90
    else 95
  end
$$;

revoke all on function public.fasecolda_source_metadata_role_v57(text,text) from public,anon,authenticated;
revoke all on function public.fasecolda_source_metadata_rank_v57(text,text) from public,anon,authenticated;
grant execute on function public.fasecolda_source_metadata_role_v57(text,text) to service_role;
grant execute on function public.fasecolda_source_metadata_rank_v57(text,text) to service_role;

create or replace view public.dashboard_fasecolda_attachment_research_inventory_v57 as
with classified as (
  select
    a.id,
    a.lot_id,
    a.name,
    a.url,
    a.kind,
    a.source,
    a.discovered_at,
    public.fasecolda_source_metadata_role_v57(a.kind,a.name) as metadata_role,
    public.fasecolda_source_metadata_rank_v57(a.kind,a.name) as metadata_rank
  from public.lot_attachments a
), aggregated as (
  select
    c.lot_id,
    count(*)::integer as attachment_count,
    count(*) filter(where c.metadata_role='IDENTITY_PRIMARY')::integer as identity_primary_count,
    count(*) filter(where c.metadata_role='IDENTITY_SECONDARY')::integer as identity_secondary_count,
    count(*) filter(where c.metadata_role='CONDITION_IDENTITY_POTENTIAL')::integer as condition_identity_potential_count,
    count(*) filter(where c.metadata_role='ADMINISTRATIVE_GENERIC')::integer as administrative_generic_count,
    count(*) filter(where c.metadata_role='OTHER_REGISTERED')::integer as other_registered_count,
    (array_agg(c.url order by c.metadata_rank,c.id))[1] as first_review_source_url,
    (array_agg(c.name order by c.metadata_rank,c.id))[1] as first_review_source_name,
    (array_agg(c.metadata_role order by c.metadata_rank,c.id))[1] as first_review_source_role,
    coalesce(jsonb_agg(
      jsonb_build_object(
        'id',c.id,
        'name',c.name,
        'url',c.url,
        'kind',c.kind,
        'source',c.source,
        'discovered_at',c.discovered_at,
        'metadata_role',c.metadata_role,
        'metadata_rank',c.metadata_rank
      ) order by c.metadata_rank,c.id
    ),'[]'::jsonb) as source_inventory
  from classified c
  group by c.lot_id
)
select * from aggregated;

revoke all on public.dashboard_fasecolda_attachment_research_inventory_v57 from public,anon,authenticated;
grant select on public.dashboard_fasecolda_attachment_research_inventory_v57 to service_role;

create or replace view public.dashboard_fasecolda_source_research_priority_v57 as
select
  cst.*,
  coalesce(inv.identity_primary_count,0)::integer as identity_primary_count,
  coalesce(inv.identity_secondary_count,0)::integer as identity_secondary_count,
  coalesce(inv.condition_identity_potential_count,0)::integer as condition_identity_potential_count,
  coalesce(inv.administrative_generic_count,0)::integer as administrative_generic_count,
  coalesce(inv.other_registered_count,0)::integer as other_registered_count,
  inv.first_review_source_url,
  inv.first_review_source_name,
  inv.first_review_source_role,
  coalesce(inv.source_inventory,'[]'::jsonb) as source_inventory,
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
  end as research_rank,
  case
    when coalesce(inv.identity_primary_count,0)>0 then 'Existe al menos una fuente registrada cuya metadata sugiere identidad vehicular primaria (matrícula, propiedad, tradición/libertad o tránsito). Debe ser inspeccionada por un humano; la clasificación no prueba su contenido.'
    when coalesce(inv.identity_secondary_count,0)>0 then 'Existe una fuente registrada cuya metadata sugiere identidad secundaria o especificaciones (SOAT, RTM, TP o informe técnico). Debe ser inspeccionada por un humano antes de usar cualquier dato como evidencia.'
    when coalesce(inv.condition_identity_potential_count,0)>0 then 'No hay documento de identidad priorizado, pero existe peritaje/inspección registrado que puede contener hechos de identidad. Su contenido no ha sido extraído ni interpretado automáticamente.'
    when coalesce(inv.other_registered_count,0)>0 then 'Hay anexos registrados no clasificados como identidad, condición o administración genérica. Requieren revisión humana para determinar si aportan hechos discriminantes.'
    else 'No existe un anexo registrado con potencial de identidad según metadata. El siguiente trabajo es adquirir o registrar una fuente externa; la página pública del lote sigue siendo solo contexto.'
  end as research_reason,
  'SOURCE_RESEARCH_PRIORITY_METADATA_ONLY_NOT_EVIDENCE_MATCH_OR_VALUATION'::text as research_interpretation
from public.dashboard_fasecolda_candidate_source_triage_v56 cst
left join public.dashboard_fasecolda_attachment_research_inventory_v57 inv using(lot_id);

revoke all on public.dashboard_fasecolda_source_research_priority_v57 from public,anon,authenticated;
grant select on public.dashboard_fasecolda_source_research_priority_v57 to service_role;

comment on function public.fasecolda_source_metadata_role_v57(text,text) is
  'Deterministic metadata classifier for registered lot attachments. It does not inspect file contents or establish evidence.';
comment on view public.dashboard_fasecolda_attachment_research_inventory_v57 is
  'Metadata-only ordered inventory of registered lot attachments for human research prioritization.';
comment on view public.dashboard_fasecolda_source_research_priority_v57 is
  'Human research routing from source metadata only. It never creates candidate evidence, a Fasecolda match, valuation, readiness change, or buy signal.';
