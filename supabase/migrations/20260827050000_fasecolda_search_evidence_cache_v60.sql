-- SUPERBID v0.60 — Fasecolda Search Evidence Cache
-- Automated public-search evidence only. This migration does not confirm search terms,
-- create Fasecolda matches/candidates, change valuation, or create a buy signal.

create table if not exists public.fasecolda_search_term_evidence_current (
  search_term text primary key,
  search_http_status integer not null check (search_http_status between 100 and 599),
  code_count integer not null check (code_count between 0 and 22),
  codes jsonb not null default '[]'::jsonb check (jsonb_typeof(codes)='array'),
  detail_http_status integer check (detail_http_status is null or detail_http_status between 100 and 599),
  detail_payload_valid boolean,
  details jsonb not null default '[]'::jsonb check (jsonb_typeof(details)='array'),
  source_search_url text not null,
  source_detail_url text,
  observed_for_external_lot_id text not null check (observed_for_external_lot_id ~ '^\d{5,12}$'),
  evidence_fingerprint text not null,
  observed_at timestamptz not null,
  interpretation text not null default 'FASECOLDA_SEARCH_EVIDENCE_NOT_OVERRIDE_MATCH_OR_VALUATION'
);

create table if not exists public.fasecolda_search_term_evidence_history (
  id bigint generated always as identity primary key,
  search_term text not null,
  search_http_status integer not null check (search_http_status between 100 and 599),
  code_count integer not null check (code_count between 0 and 22),
  codes jsonb not null check (jsonb_typeof(codes)='array'),
  detail_http_status integer check (detail_http_status is null or detail_http_status between 100 and 599),
  detail_payload_valid boolean,
  details jsonb not null check (jsonb_typeof(details)='array'),
  source_search_url text not null,
  source_detail_url text,
  observed_for_external_lot_id text not null check (observed_for_external_lot_id ~ '^\d{5,12}$'),
  evidence_fingerprint text not null,
  observed_at timestamptz not null,
  recorded_at timestamptz not null default clock_timestamp(),
  interpretation text not null default 'FASECOLDA_SEARCH_EVIDENCE_NOT_OVERRIDE_MATCH_OR_VALUATION'
);

create index if not exists ix_fasecolda_search_term_evidence_history_term_observed
  on public.fasecolda_search_term_evidence_history(search_term, observed_at desc);

alter table public.fasecolda_search_term_evidence_current enable row level security;
alter table public.fasecolda_search_term_evidence_history enable row level security;
revoke all on public.fasecolda_search_term_evidence_current from public, anon, authenticated;
revoke all on public.fasecolda_search_term_evidence_history from public, anon, authenticated;
grant select,insert,update on public.fasecolda_search_term_evidence_current to service_role;
grant select,insert on public.fasecolda_search_term_evidence_history to service_role;

comment on table public.fasecolda_search_term_evidence_current is
'Latest automated observation of Fasecolda public search/detail evidence by normalized search term. Not an override, match, valuation, bid, or buy signal.';
comment on table public.fasecolda_search_term_evidence_history is
'Append-only observations of Fasecolda public search/detail evidence. Automated provenance only; never human resolution.';

create or replace function public.fasecolda_search_input_disposition_v60(
  p_brand text,
  p_model_year integer,
  p_suggested_term text
) returns text
language plpgsql
immutable
set search_path=public,extensions,pg_catalog
as $$
declare
  v_brand text := trim(public.vehicle_norm(coalesce(p_brand,'')));
  v_suggested text := trim(left(public.vehicle_norm(coalesce(p_suggested_term,'')),80));
begin
  if p_model_year is null or p_model_year < 1900 or p_model_year > 2100 then
    return 'MISSING_YEAR';
  end if;
  if v_brand='' or v_brand = any(array[
    'COMBO','AUTOMOVIL','CAMION','CAMIONETA','VEHICULO','VOLQUETA',
    'TRACTOCAMION','TRACTOMULA','BUS','MICROBUS'
  ]) then
    return 'IDENTITY_INPUT_REVIEW';
  end if;
  if v_suggested<>'' and not (v_suggested=v_brand or v_suggested like v_brand||' %') then
    return 'IDENTITY_INPUT_REVIEW';
  end if;
  return 'EXPLORABLE';
end;
$$;

revoke all on function public.fasecolda_search_input_disposition_v60(text,integer,text) from public,anon,authenticated;
grant execute on function public.fasecolda_search_input_disposition_v60(text,integer,text) to service_role;

create or replace function public.dashboard_refresh_fasecolda_search_term_evidence_v60(
  p_external_lot_id text,
  p_term text
) returns jsonb
language plpgsql
security definer
set search_path=public,extensions,pg_catalog
as $$
declare
  v_lot public.auction_lots%rowtype;
  v_term text;
  v_brand text;
  v_probe jsonb;
  v_codes jsonb := '[]'::jsonb;
  v_code_count integer := 0;
  v_search_status integer;
  v_codes_csv text;
  v_resp record;
  v_detail_status integer;
  v_detail_payload_valid boolean;
  v_details jsonb := '[]'::jsonb;
  v_detail_count integer := 0;
  v_search_url text;
  v_detail_url text;
  v_observed_at timestamptz := clock_timestamp();
  v_fingerprint text;
begin
  if p_external_lot_id is null or p_external_lot_id !~ '^\d{5,12}$' then
    raise exception 'invalid external lot id';
  end if;

  select * into v_lot
  from public.auction_lots
  where external_lot_id=p_external_lot_id
  order by id desc limit 1;
  if not found then raise exception 'lot not found'; end if;

  if public.fasecolda_search_input_disposition_v60(v_lot.brand,v_lot.model_year,public.fasecolda_suggest_search_term(v_lot.title)) <> 'EXPLORABLE' then
    raise exception 'search evidence refresh blocked until identity/model year input is resolved';
  end if;

  v_term := trim(left(public.vehicle_norm(coalesce(p_term,'')),80));
  if char_length(v_term)<2 or char_length(v_term)>80 then
    raise exception 'invalid search term length';
  end if;
  v_brand := nullif(trim(public.vehicle_norm(coalesce(v_lot.brand,''))),'');
  if v_brand is null or not (v_term=v_brand or v_term like v_brand||' %') then
    raise exception 'search term must preserve vehicle brand';
  end if;

  -- Existing v0.54 probe is deliberately read-only with respect to SUPERBID business state.
  v_probe := public.dashboard_probe_fasecolda_search_term(v_lot.external_lot_id,v_term);
  v_search_status := coalesce((v_probe->>'http_status')::integer,500);
  v_code_count := least(22,greatest(0,coalesce((v_probe->>'code_count')::integer,0)));
  if jsonb_typeof(v_probe->'codes')='array' then v_codes := v_probe->'codes'; end if;

  v_search_url := 'https://fasecoldaback.quantil.co/api/busqueda/' || extensions.urlencode(v_term);

  if v_code_count>0 then
    select string_agg(value#>>'{}',',' order by ord)
    into v_codes_csv
    from jsonb_array_elements(v_codes) with ordinality x(value,ord)
    where ord<=22;

    if nullif(v_codes_csv,'') is not null then
      v_detail_url := 'https://fasecoldaback.quantil.co/api/listacodigosid/consultabycodigo/' || v_codes_csv;
      select * into v_resp from extensions.http_get(v_detail_url::varchar);
      v_detail_status := v_resp.status;
      v_detail_payload_valid := false;
      if v_resp.status=200 then
        begin
          v_details := v_resp.content::jsonb;
          if jsonb_typeof(v_details)='array' then
            v_detail_payload_valid := true;
          else
            v_details := '[]'::jsonb;
          end if;
        exception when others then
          v_details := '[]'::jsonb;
          v_detail_payload_valid := false;
        end;
      end if;
    end if;
  end if;

  if jsonb_typeof(v_details)='array' then v_detail_count := jsonb_array_length(v_details); end if;
  v_fingerprint := md5(
    v_term || '|' || v_search_status::text || '|' || v_code_count::text || '|' ||
    coalesce(v_detail_status::text,'') || '|' || coalesce(v_detail_payload_valid::text,'') || '|' ||
    v_codes::text || '|' || v_details::text
  );

  insert into public.fasecolda_search_term_evidence_current(
    search_term,search_http_status,code_count,codes,detail_http_status,detail_payload_valid,details,
    source_search_url,source_detail_url,observed_for_external_lot_id,
    evidence_fingerprint,observed_at,interpretation
  ) values(
    v_term,v_search_status,v_code_count,v_codes,v_detail_status,v_detail_payload_valid,v_details,
    v_search_url,v_detail_url,v_lot.external_lot_id,
    v_fingerprint,v_observed_at,'FASECOLDA_SEARCH_EVIDENCE_NOT_OVERRIDE_MATCH_OR_VALUATION'
  )
  on conflict(search_term) do update set
    search_http_status=excluded.search_http_status,
    code_count=excluded.code_count,
    codes=excluded.codes,
    detail_http_status=excluded.detail_http_status,
    detail_payload_valid=excluded.detail_payload_valid,
    details=excluded.details,
    source_search_url=excluded.source_search_url,
    source_detail_url=excluded.source_detail_url,
    observed_for_external_lot_id=excluded.observed_for_external_lot_id,
    evidence_fingerprint=excluded.evidence_fingerprint,
    observed_at=excluded.observed_at,
    interpretation=excluded.interpretation;

  insert into public.fasecolda_search_term_evidence_history(
    search_term,search_http_status,code_count,codes,detail_http_status,detail_payload_valid,details,
    source_search_url,source_detail_url,observed_for_external_lot_id,
    evidence_fingerprint,observed_at,interpretation
  ) values(
    v_term,v_search_status,v_code_count,v_codes,v_detail_status,v_detail_payload_valid,v_details,
    v_search_url,v_detail_url,v_lot.external_lot_id,
    v_fingerprint,v_observed_at,'FASECOLDA_SEARCH_EVIDENCE_NOT_OVERRIDE_MATCH_OR_VALUATION'
  );

  return jsonb_build_object(
    'ok',true,
    'external_lot_id',v_lot.external_lot_id,
    'search_term',v_term,
    'search_http_status',v_search_status,
    'code_count',v_code_count,
    'detail_http_status',v_detail_status,
    'detail_payload_valid',v_detail_payload_valid,
    'detail_count',v_detail_count,
    'evidence_fingerprint',v_fingerprint,
    'observed_at',v_observed_at,
    'evidence_cache_modified',true,
    'override_fields_modified',false,
    'match_fields_modified',false,
    'candidate_fields_modified',false,
    'valuation_fields_modified',false,
    'economic_fields_modified',false,
    'buy_signal',false,
    'interpretation','FASECOLDA_SEARCH_EVIDENCE_NOT_OVERRIDE_MATCH_OR_VALUATION'
  );
end;
$$;

revoke all on function public.dashboard_refresh_fasecolda_search_term_evidence_v60(text,text) from public,anon,authenticated;
grant execute on function public.dashboard_refresh_fasecolda_search_term_evidence_v60(text,text) to service_role;

create or replace view public.dashboard_fasecolda_search_evidence_queue_v60 as
with base as (
  select
    w.*,
    public.fasecolda_search_input_disposition_v60(w.brand,w.model_year,w.suggested_search_term) as input_disposition,
    trim(left(public.vehicle_norm(coalesce(w.suggested_search_term,'')),80)) as normalized_suggested_term
  from public.dashboard_fasecolda_resolution_workstreams_v59 w
  where w.workstream='SEARCH_REVIEW'
), joined as (
  select
    b.*,
    c.search_http_status as evidence_search_http_status,
    c.code_count as evidence_code_count,
    c.codes as evidence_codes,
    c.detail_http_status as evidence_detail_http_status,
    c.detail_payload_valid as evidence_detail_payload_valid,
    c.details as evidence_details,
    c.source_search_url as evidence_search_url,
    c.source_detail_url as evidence_detail_url,
    c.observed_for_external_lot_id as evidence_observed_for_external_lot_id,
    c.evidence_fingerprint,
    c.observed_at as evidence_observed_at,
    (c.observed_at is not null and c.observed_at >= clock_timestamp()-interval '24 hours') as evidence_fresh
  from base b
  left join public.fasecolda_search_term_evidence_current c
    on c.search_term=b.normalized_suggested_term
), assessed as (
  select
    j.*,
    coalesce(y.year_compatible_code_count,0)::integer as year_compatible_code_count
  from joined j
  left join lateral (
    select count(distinct item->>'codigo')::integer as year_compatible_code_count
    from jsonb_array_elements(
      case when j.evidence_detail_payload_valid is true and jsonb_typeof(j.evidence_details)='array' then j.evidence_details else '[]'::jsonb end
    ) item
    where exists (
      select 1
      from jsonb_array_elements(
        case when jsonb_typeof(item->'valorModelo')='array' then item->'valorModelo' else '[]'::jsonb end
      ) m
      where coalesce(m->>'modelo','') ~ '^\d{4}$'
        and (m->>'modelo')::integer=j.model_year
        and upper(coalesce(m->>'estado','USADO'))='USADO'
        and nullif(m->>'valor','') is not null
    )
  ) y on true
)
select
  a.*,
  case
    when a.input_disposition='IDENTITY_INPUT_REVIEW' then 'IDENTITY_INPUT_REVIEW'
    when a.input_disposition='MISSING_YEAR' then 'MISSING_YEAR'
    when a.evidence_observed_at is null then 'SUGGESTED_EVIDENCE_MISSING'
    when not a.evidence_fresh then 'SUGGESTED_EVIDENCE_STALE'
    when coalesce(a.evidence_code_count,0)=0 then 'SUGGESTED_NO_CODES'
    when coalesce(a.evidence_detail_http_status,0)<>200 or a.evidence_detail_payload_valid is distinct from true then 'SUGGESTED_DETAIL_UNAVAILABLE'
    when a.year_compatible_code_count=0 then 'SUGGESTED_NO_YEAR_COMPATIBLE_CODES'
    else 'SUGGESTED_YEAR_COMPATIBLE_CODES'
  end as evidence_state,
  case
    when a.input_disposition='IDENTITY_INPUT_REVIEW' then 'REVIEW_IDENTITY_INPUT'
    when a.input_disposition='MISSING_YEAR' then 'REVIEW_MODEL_YEAR_INPUT'
    when a.evidence_observed_at is null or not a.evidence_fresh then 'REFRESH_SUGGESTED_EVIDENCE'
    when coalesce(a.evidence_code_count,0)=0 then 'EXPLORE_ALTERNATE_VARIANTS'
    when coalesce(a.evidence_detail_http_status,0)<>200 or a.evidence_detail_payload_valid is distinct from true then 'REFRESH_SUGGESTED_EVIDENCE'
    when a.year_compatible_code_count=0 then 'REVIEW_YEAR_OR_ALTERNATE_TERM'
    else 'REVIEW_SUGGESTED_TERM'
  end as operator_next_action,
  case
    when a.input_disposition='EXPLORABLE'
      and a.evidence_fresh
      and coalesce(a.evidence_detail_http_status,0)=200
      and a.evidence_detail_payload_valid is true
      and a.year_compatible_code_count>0
      then true else false
  end as suggested_term_reviewable,
  case
    when a.evidence_observed_at is null then null::numeric
    else extract(epoch from (clock_timestamp()-a.evidence_observed_at))/3600.0
  end as evidence_age_hours,
  case
    when a.input_disposition='IDENTITY_INPUT_REVIEW' then 10
    when a.input_disposition='MISSING_YEAR' then 15
    when a.evidence_observed_at is null then 20
    when not a.evidence_fresh then 25
    when coalesce(a.evidence_code_count,0)>0 and coalesce(a.evidence_detail_http_status,0)=200 and a.evidence_detail_payload_valid is true and a.year_compatible_code_count>0 then 30
    when coalesce(a.evidence_code_count,0)>0 and coalesce(a.evidence_detail_http_status,0)=200 and a.evidence_detail_payload_valid is true and a.year_compatible_code_count=0 then 40
    when coalesce(a.evidence_code_count,0)=0 then 50
    else 60
  end as evidence_state_rank,
  'FASECOLDA_SEARCH_EVIDENCE_NOT_OVERRIDE_MATCH_OR_VALUATION'::text as evidence_interpretation
from assessed a;

revoke all on public.dashboard_fasecolda_search_evidence_queue_v60 from public,anon,authenticated;
grant select on public.dashboard_fasecolda_search_evidence_queue_v60 to service_role;

comment on view public.dashboard_fasecolda_search_evidence_queue_v60 is
'v0.60 operational search-evidence queue. Reuses public Fasecolda search/detail observations by term and checks model-year compatibility without selecting a term, creating a match, or valuing a vehicle.';
