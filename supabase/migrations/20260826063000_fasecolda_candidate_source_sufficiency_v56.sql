-- SUPERBID v0.56 · Fasecolda candidate source sufficiency lifecycle
-- Operational triage only. It never confirms a Fasecolda code, writes valuation,
-- changes readiness, or creates a buy signal.

create or replace function public.fasecolda_hint_engine_cc_v56(p_text text)
returns integer
language sql
immutable
set search_path=pg_catalog
as $$
  with vals as (
    select distinct (m)[1]::integer as value
    from regexp_matches(coalesce(p_text,''), '\m([0-9]{3,5})[[:space:]]*CC\M', 'gi') as m
  )
  select case when count(*)=1 then min(value) end from vals
$$;

create or replace function public.fasecolda_hint_transmission_v56(p_text text)
returns text
language sql
immutable
set search_path=pg_catalog
as $$
  select case
    when upper(coalesce(p_text,'')) ~ '\m(MT|MANUAL|MEC[ÁA]NIC[AO])\M'
      and not upper(coalesce(p_text,'')) ~ '\m(AT|TP|CVT|DCT|DSG|AUT|AUTOM[ÁA]TIC[AO])\M' then 'MANUAL'
    when upper(coalesce(p_text,'')) ~ '\m(AT|TP|CVT|DCT|DSG|AUT|AUTOM[ÁA]TIC[AO])\M'
      and not upper(coalesce(p_text,'')) ~ '\m(MT|MANUAL|MEC[ÁA]NIC[AO])\M' then 'AUTOMATIC'
    else null
  end
$$;

create or replace function public.fasecolda_hint_drivetrain_v56(p_text text)
returns text
language sql
immutable
set search_path=pg_catalog
as $$
  select case
    when upper(coalesce(p_text,'')) ~ '(4[[:space:]]*[Xx][[:space:]]*4|4WD|AWD)' then '4X4_AWD'
    when upper(coalesce(p_text,'')) ~ '(4[[:space:]]*[Xx][[:space:]]*2|2WD)' then '4X2_2WD'
    else null
  end
$$;

create or replace function public.fasecolda_hint_fuel_v56(p_text text)
returns text
language sql
immutable
set search_path=pg_catalog
as $$
  select case
    when upper(coalesce(p_text,'')) ~ '\m(H[IÍ]BRID[AO]|HYBRID|HEV|PHEV)\M' then 'HYBRID'
    when upper(coalesce(p_text,'')) ~ '\m(EL[EÉ]CTRIC[AO]|ELECTRIC|EV|BEV)\M' then 'ELECTRIC'
    when upper(coalesce(p_text,'')) ~ '\m(DI[EÉ]SEL|DIESEL)\M'
      and not (upper(coalesce(p_text,'')) ~ '\m(GNV|GNC|CNG|GASOLINA|GASOLINE|PETROL)\M' or upper(coalesce(p_text,'')) ~ 'GAS[[:space:]]+NATURAL') then 'DIESEL'
    when (upper(coalesce(p_text,'')) ~ '\m(GNV|GNC|CNG)\M' or upper(coalesce(p_text,'')) ~ 'GAS[[:space:]]+NATURAL')
      and not upper(coalesce(p_text,'')) ~ '\m(DI[EÉ]SEL|DIESEL|GASOLINA|GASOLINE|PETROL)\M' then 'CNG'
    when upper(coalesce(p_text,'')) ~ '\m(GASOLINA|GASOLINE|PETROL)\M'
      and not (upper(coalesce(p_text,'')) ~ '\m(DI[EÉ]SEL|DIESEL|GNV|GNC|CNG)\M' or upper(coalesce(p_text,'')) ~ 'GAS[[:space:]]+NATURAL') then 'GASOLINE'
    else null
  end
$$;

revoke all on function public.fasecolda_hint_engine_cc_v56(text) from public,anon,authenticated;
revoke all on function public.fasecolda_hint_transmission_v56(text) from public,anon,authenticated;
revoke all on function public.fasecolda_hint_drivetrain_v56(text) from public,anon,authenticated;
revoke all on function public.fasecolda_hint_fuel_v56(text) from public,anon,authenticated;
grant execute on function public.fasecolda_hint_engine_cc_v56(text) to service_role;
grant execute on function public.fasecolda_hint_transmission_v56(text) to service_role;
grant execute on function public.fasecolda_hint_drivetrain_v56(text) to service_role;
grant execute on function public.fasecolda_hint_fuel_v56(text) to service_role;

create table if not exists public.lot_fasecolda_candidate_source_dispositions(
  lot_id bigint primary key references public.auction_lots(id) on delete cascade,
  external_lot_id text not null,
  evidence_fingerprint text not null check(evidence_fingerprint ~ '^[0-9a-f]{32}$'),
  source_triage_class text not null,
  disposition_action text not null check(disposition_action in (
    'ROUTE_TO_EVIDENCE_REVIEW',
    'CONFIRM_CURRENT_SOURCES_INSUFFICIENT',
    'REQUEST_SOURCE_RESEARCH',
    'REFER_IDENTITY_REVIEW',
    'REQUEST_MATCHER_RECHECK'
  )),
  note text not null check(char_length(trim(note)) between 10 and 2000),
  created_at timestamptz not null default clock_timestamp(),
  updated_at timestamptz not null default clock_timestamp(),
  interpretation text not null default 'CANDIDATE_SOURCE_DISPOSITION_NOT_EVIDENCE_MATCH_OR_VALUATION',
  constraint candidate_source_disposition_interpretation_guard check(
    interpretation='CANDIDATE_SOURCE_DISPOSITION_NOT_EVIDENCE_MATCH_OR_VALUATION'
  )
);

create table if not exists public.lot_fasecolda_candidate_source_disposition_history(
  id bigint generated always as identity primary key,
  lot_id bigint not null references public.auction_lots(id) on delete cascade,
  external_lot_id text not null,
  evidence_fingerprint text not null check(evidence_fingerprint ~ '^[0-9a-f]{32}$'),
  source_triage_class text not null,
  action text not null check(action in (
    'ROUTE_TO_EVIDENCE_REVIEW',
    'CONFIRM_CURRENT_SOURCES_INSUFFICIENT',
    'REQUEST_SOURCE_RESEARCH',
    'REFER_IDENTITY_REVIEW',
    'REQUEST_MATCHER_RECHECK',
    'CLEAR'
  )),
  note text,
  created_at timestamptz not null default clock_timestamp(),
  interpretation text not null default 'CANDIDATE_SOURCE_DISPOSITION_NOT_EVIDENCE_MATCH_OR_VALUATION',
  constraint candidate_source_disposition_history_note_len check(note is null or char_length(note)<=2000),
  constraint candidate_source_disposition_history_interpretation_guard check(
    interpretation='CANDIDATE_SOURCE_DISPOSITION_NOT_EVIDENCE_MATCH_OR_VALUATION'
  )
);

alter table public.lot_fasecolda_candidate_source_dispositions enable row level security;
alter table public.lot_fasecolda_candidate_source_disposition_history enable row level security;
revoke all on public.lot_fasecolda_candidate_source_dispositions from public,anon,authenticated;
revoke all on public.lot_fasecolda_candidate_source_disposition_history from public,anon,authenticated;
grant select,insert,update,delete on public.lot_fasecolda_candidate_source_dispositions to service_role;
grant select,insert on public.lot_fasecolda_candidate_source_disposition_history to service_role;
grant usage,select on sequence public.lot_fasecolda_candidate_source_disposition_history_id_seq to service_role;

create index if not exists ix_candidate_source_disposition_history_lot_created
  on public.lot_fasecolda_candidate_source_disposition_history(lot_id,created_at desc);

create or replace view public.dashboard_fasecolda_candidate_source_triage_v56 as
with base as (
  select
    r.external_lot_id,r.lot_id,r.title,r.brand,r.line,r.model_year,r.city,r.seller,
    r.current_bid_cop,r.closes_at,r.review_state,r.automatic_status,r.search_term,
    r.automatic_best_code,r.automatic_best_description,r.automatic_best_score,
    r.automatic_second_score,r.candidate_count,r.manual_resolution_status,r.candidates,
    a.url as auction_url,
    public.fasecolda_hint_engine_cc_v56(r.title) as title_engine_cc,
    public.fasecolda_hint_transmission_v56(r.title) as title_transmission,
    public.fasecolda_hint_drivetrain_v56(r.title) as title_drivetrain,
    public.fasecolda_hint_fuel_v56(r.title) as title_fuel
  from public.dashboard_fasecolda_resolution_queue r
  join public.auction_lots a on a.id=r.lot_id
  where r.automatic_status in ('AMBIGUOUS','MEDIUM')
    and coalesce(r.manual_resolution_status,'UNRESOLVED')='UNRESOLVED'
), raw as (
  select
    b.lot_id,c.code,c.model_year as candidate_model_year,c.description,c.score,c.rank_no,c.current_value_cop,
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
    b.*,cs.current_candidate_count,cs.engine_value_count,cs.transmission_value_count,
    cs.drivetrain_value_count,cs.fuel_value_count,cs.candidate_fingerprint,
    ts.structured_discriminator_count,ts.structured_discriminators,
    ts.unique_title_discriminator_count,ts.unique_title_discriminators,
    ts.distinct_title_target_codes,ts.title_unique_target_code,
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
  'CANDIDATE_SOURCE_TRIAGE_NOT_EVIDENCE_MATCH_OR_VALUATION'::text as interpretation
from fingerprinted f
left join public.lot_fasecolda_candidate_source_dispositions d using(lot_id);

revoke all on public.dashboard_fasecolda_candidate_source_triage_v56 from public,anon,authenticated;
grant select on public.dashboard_fasecolda_candidate_source_triage_v56 to service_role;

create or replace function public.dashboard_set_fasecolda_candidate_source_disposition_v56(
  p_external_lot_id text,
  p_action text,
  p_note text default null
) returns jsonb
language plpgsql
security definer
set search_path=public,pg_catalog
as $$
declare
  v_case record;
  v_existing public.lot_fasecolda_candidate_source_dispositions%rowtype;
  v_action text:=upper(trim(coalesce(p_action,'')));
  v_note text:=nullif(trim(coalesce(p_note,'')),'');
begin
  if p_external_lot_id is null or p_external_lot_id !~ '^[0-9]{5,12}$' then raise exception 'invalid external lot id'; end if;
  if v_action not in (
    'ROUTE_TO_EVIDENCE_REVIEW','CONFIRM_CURRENT_SOURCES_INSUFFICIENT','REQUEST_SOURCE_RESEARCH',
    'REFER_IDENTITY_REVIEW','REQUEST_MATCHER_RECHECK','CLEAR'
  ) then raise exception 'invalid candidate source disposition action'; end if;
  if v_action<>'CLEAR' and (v_note is null or char_length(v_note)<10) then raise exception 'candidate source disposition note must be at least 10 characters'; end if;
  if v_note is not null and char_length(v_note)>2000 then raise exception 'candidate source disposition note too long'; end if;

  select * into v_case
  from public.dashboard_fasecolda_candidate_source_triage_v56
  where external_lot_id=p_external_lot_id
  order by lot_id desc limit 1;
  if v_case.lot_id is null then raise exception 'current candidate source triage case not found'; end if;

  if v_action='ROUTE_TO_EVIDENCE_REVIEW' and v_case.current_candidate_count<2 then
    raise exception 'single-candidate low-confidence case cannot satisfy the v0.52 discriminating-alternative contract';
  end if;
  if v_action='CONFIRM_CURRENT_SOURCES_INSUFFICIENT' and char_length(v_note)<20 then
    raise exception 'insufficient-source confirmation note must be at least 20 characters';
  end if;

  select * into v_existing from public.lot_fasecolda_candidate_source_dispositions where lot_id=v_case.lot_id;

  if v_action='CLEAR' then
    delete from public.lot_fasecolda_candidate_source_dispositions where lot_id=v_case.lot_id;
  else
    insert into public.lot_fasecolda_candidate_source_dispositions(
      lot_id,external_lot_id,evidence_fingerprint,source_triage_class,disposition_action,note,updated_at
    ) values(
      v_case.lot_id,v_case.external_lot_id,v_case.evidence_fingerprint,v_case.source_triage_class,v_action,v_note,clock_timestamp()
    )
    on conflict(lot_id) do update set
      external_lot_id=excluded.external_lot_id,
      evidence_fingerprint=excluded.evidence_fingerprint,
      source_triage_class=excluded.source_triage_class,
      disposition_action=excluded.disposition_action,
      note=excluded.note,
      updated_at=clock_timestamp();
  end if;

  insert into public.lot_fasecolda_candidate_source_disposition_history(
    lot_id,external_lot_id,evidence_fingerprint,source_triage_class,action,note
  ) values(
    v_case.lot_id,v_case.external_lot_id,v_case.evidence_fingerprint,v_case.source_triage_class,v_action,v_note
  );

  return jsonb_build_object(
    'ok',true,
    'external_lot_id',v_case.external_lot_id,
    'action',v_action,
    'source_triage_class',v_case.source_triage_class,
    'evidence_fingerprint',v_case.evidence_fingerprint,
    'buy_signal',false,
    'match_fields_modified',false,
    'valuation_fields_modified',false,
    'evidence_fields_modified',false,
    'interpretation','CANDIDATE_SOURCE_DISPOSITION_NOT_EVIDENCE_MATCH_OR_VALUATION'
  );
end
$$;

revoke all on function public.dashboard_set_fasecolda_candidate_source_disposition_v56(text,text,text) from public,anon,authenticated;
grant execute on function public.dashboard_set_fasecolda_candidate_source_disposition_v56(text,text,text) to service_role;

-- Re-route valuation work without changing readiness or any effective valuation state.
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
  coalesce(ef.status,ud.effective_status,'NO_MATCH_ROW'::text) as effective_status,
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
  coalesce(rq.manual_resolution_status,'UNRESOLVED'::text) as manual_resolution_status,
  ud.diagnostic_reason,
  ud.current_search_term,
  ud.suggested_search_term,
  ud.suggestion_differs,
  case
    when er.readiness_status='CLOSED' then 'NO_ACTION_CLOSED'
    when coalesce(ef.status,ud.effective_status) in ('AMBIGUOUS','MEDIUM') and cst.operational_route='EVIDENCE_REVIEW' then 'CANDIDATE_RESOLUTION'
    when coalesce(ef.status,ud.effective_status) in ('AMBIGUOUS','MEDIUM') and cst.operational_route='SOURCE_INSUFFICIENT_ACKNOWLEDGED' then 'CANDIDATE_SOURCE_INSUFFICIENT'
    when coalesce(ef.status,ud.effective_status) in ('AMBIGUOUS','MEDIUM') and cst.operational_route='SOURCE_RESEARCH_REQUESTED' then 'CANDIDATE_SOURCE_RESEARCH'
    when coalesce(ef.status,ud.effective_status) in ('AMBIGUOUS','MEDIUM') and cst.operational_route='IDENTITY_REVIEW_REQUESTED' then 'CANDIDATE_IDENTITY_REVIEW'
    when coalesce(ef.status,ud.effective_status) in ('AMBIGUOUS','MEDIUM') and cst.operational_route='MATCHER_RECHECK_REQUESTED' then 'CANDIDATE_MATCHER_RECHECK'
    when coalesce(ef.status,ud.effective_status) in ('AMBIGUOUS','MEDIUM') then 'CANDIDATE_SOURCE_TRIAGE'
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
    when coalesce(ef.status,ud.effective_status) in ('AMBIGUOUS','MEDIUM') and cst.operational_route='EVIDENCE_REVIEW' then 10
    when coalesce(ef.status,ud.effective_status) in ('AMBIGUOUS','MEDIUM') and cst.operational_route='SOURCE_TRIAGE' then 15
    when coalesce(ef.status,ud.effective_status) in ('AMBIGUOUS','MEDIUM') and cst.operational_route in ('SOURCE_RESEARCH_REQUESTED','IDENTITY_REVIEW_REQUESTED','MATCHER_RECHECK_REQUESTED') then 18
    when coalesce(ef.status,ud.effective_status) in ('AMBIGUOUS','MEDIUM') and cst.operational_route='SOURCE_INSUFFICIENT_ACKNOWLEDGED' then 85
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
    when coalesce(ef.status,ud.effective_status) in ('AMBIGUOUS','MEDIUM') and cst.operational_route='EVIDENCE_REVIEW' then cst.source_triage_reason
    when coalesce(ef.status,ud.effective_status) in ('AMBIGUOUS','MEDIUM') and cst.operational_route is not null then cst.source_triage_reason
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
    when coalesce(ef.status,ud.effective_status) in ('AMBIGUOUS','MEDIUM') and cst.operational_route='EVIDENCE_REVIEW' then 'superbid-fasecolda-candidate-cockpit'
    when coalesce(ef.status,ud.effective_status) in ('AMBIGUOUS','MEDIUM') then 'superbid-fasecolda-source-dashboard'
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
left join public.dashboard_fasecolda_candidate_source_triage_v56 cst using(lot_id)
where er.next_action='REVIEW_VALUATION';

comment on view public.dashboard_fasecolda_candidate_source_triage_v56 is
  'Read-only candidate source sufficiency triage. Automated title/candidate comparisons only route work; they are not evidence, a match, or a recommendation.';
comment on function public.dashboard_set_fasecolda_candidate_source_disposition_v56(text,text,text) is
  'Records a human operational disposition for current candidate-source fingerprint. It never confirms a candidate or writes valuation/economic fields.';
