create table if not exists public.market_manual_evidence_sets(
  id bigint generated always as identity primary key,
  lot_id bigint not null references public.auction_lots(id) on delete cascade,
  status text not null default 'DRAFT' check(status in ('DRAFT','REVIEWED')),
  source_note text,
  comparable_count integer not null default 0 check(comparable_count between 0 and 20),
  median_asking_cop bigint,
  p25_asking_cop bigint,
  p75_asking_cop bigint,
  quick_sale_cop bigint,
  dispersion_pct numeric,
  confidence numeric not null default 0 check(confidence between 0 and 1),
  evidence_fingerprint text check(evidence_fingerprint is null or evidence_fingerprint ~ '^[0-9a-f]{32}$'),
  reviewed_at timestamptz,
  created_at timestamptz not null default clock_timestamp(),
  interpretation text not null default 'MANUAL_MARKET_EVIDENCE_NOT_AUTOMATIC_VALUATION'
    check(interpretation='MANUAL_MARKET_EVIDENCE_NOT_AUTOMATIC_VALUATION')
);

create table if not exists public.market_manual_evidence_items(
  id bigint generated always as identity primary key,
  evidence_set_id bigint not null references public.market_manual_evidence_sets(id) on delete cascade,
  ordinal integer not null check(ordinal between 1 and 20),
  source_url text not null check(source_url ~ '^https://'),
  title text not null,
  asking_price_cop bigint not null check(asking_price_cop between 100000 and 5000000000),
  model_year integer not null check(model_year between 1950 and 2100),
  city text,
  observed_at timestamptz not null default clock_timestamp(),
  note text,
  unique(evidence_set_id,ordinal),
  unique(evidence_set_id,source_url)
);

alter table public.market_manual_evidence_sets enable row level security;
alter table public.market_manual_evidence_items enable row level security;
revoke all on public.market_manual_evidence_sets,public.market_manual_evidence_items from public,anon,authenticated;
grant select,insert,update on public.market_manual_evidence_sets to service_role;
grant select,insert on public.market_manual_evidence_items to service_role;
create index if not exists ix_market_manual_evidence_sets_lot on public.market_manual_evidence_sets(lot_id,created_at desc);
create index if not exists ix_market_manual_evidence_items_set on public.market_manual_evidence_items(evidence_set_id,ordinal);

create or replace function public.dashboard_save_manual_market_evidence(
  p_external_lot_id text,
  p_comparables jsonb,
  p_source_note text default null,
  p_mark_reviewed boolean default false
) returns jsonb
language plpgsql
security definer
set search_path=public,pg_catalog
as $$
declare
  v_lot_id bigint;
  v_model_year integer;
  v_set_id bigint;
  v_count integer;
  v_row jsonb;
  v_i integer:=0;
  v_url text;
  v_title text;
  v_city text;
  v_price bigint;
  v_year integer;
  v_observed timestamptz;
  v_median bigint;
  v_p25 bigint;
  v_p75 bigint;
  v_quick bigint;
  v_disp numeric;
  v_conf numeric;
  v_fingerprint text;
begin
  if p_external_lot_id is null or p_external_lot_id !~ '^\d{5,12}$' then raise exception 'invalid external lot id'; end if;
  if jsonb_typeof(p_comparables) is distinct from 'array' then raise exception 'comparables must be a JSON array'; end if;
  v_count:=jsonb_array_length(p_comparables);
  if v_count<1 or v_count>20 then raise exception 'between 1 and 20 comparables are required'; end if;
  if p_mark_reviewed and v_count<3 then raise exception 'at least three comparables are required before review'; end if;
  if p_mark_reviewed and length(trim(coalesce(p_source_note,'')))<10 then raise exception 'reviewed market evidence requires a source note'; end if;

  select id,model_year into v_lot_id,v_model_year from public.auction_lots
  where external_lot_id=p_external_lot_id order by id desc limit 1;
  if v_lot_id is null then raise exception 'lot not found'; end if;
  if v_model_year is null then raise exception 'lot model year is required for market review'; end if;

  insert into public.market_manual_evidence_sets(lot_id,status,source_note,comparable_count,confidence)
  values(v_lot_id,'DRAFT',nullif(left(trim(coalesce(p_source_note,'')),2000),''),v_count,0)
  returning id into v_set_id;

  for v_row in select value from jsonb_array_elements(p_comparables) loop
    v_i:=v_i+1;
    v_url:=trim(coalesce(v_row->>'url',''));
    v_title:=trim(coalesce(v_row->>'title',''));
    v_city:=nullif(left(trim(coalesce(v_row->>'city','')),120),'');
    if v_url !~ '^https://[^[:space:]]+$' or length(v_url)>2000 then raise exception 'comparable % requires a valid HTTPS URL',v_i; end if;
    if length(v_title)<3 or length(v_title)>500 then raise exception 'comparable % requires a title',v_i; end if;
    if coalesce(v_row->>'asking_price_cop','') !~ '^[0-9]{6,10}$' then raise exception 'comparable % has invalid price',v_i; end if;
    v_price:=(v_row->>'asking_price_cop')::bigint;
    if v_price<100000 or v_price>5000000000 then raise exception 'comparable % price outside allowed range',v_i; end if;
    if coalesce(v_row->>'model_year','') !~ '^[0-9]{4}$' then raise exception 'comparable % has invalid model year',v_i; end if;
    v_year:=(v_row->>'model_year')::integer;
    if v_year<>v_model_year then raise exception 'comparable % model year does not match lot year',v_i; end if;
    begin
      v_observed:=coalesce(nullif(v_row->>'observed_at','')::timestamptz,clock_timestamp());
    exception when others then
      raise exception 'comparable % has invalid observed_at',v_i;
    end;
    if v_observed>clock_timestamp()+interval '5 minutes' or v_observed<clock_timestamp()-interval '365 days' then raise exception 'comparable % observed_at outside allowed range',v_i; end if;

    insert into public.market_manual_evidence_items(
      evidence_set_id,ordinal,source_url,title,asking_price_cop,model_year,city,observed_at,note
    ) values(
      v_set_id,v_i,v_url,v_title,v_price,v_year,v_city,v_observed,nullif(left(trim(coalesce(v_row->>'note','')),1000),'')
    );
  end loop;

  select
    count(*)::integer,
    percentile_cont(0.5) within group(order by asking_price_cop)::bigint,
    percentile_cont(0.25) within group(order by asking_price_cop)::bigint,
    percentile_cont(0.75) within group(order by asking_price_cop)::bigint,
    md5(string_agg(source_url||'|'||asking_price_cop::text||'|'||model_year::text||'|'||title,'||' order by ordinal))
  into v_count,v_median,v_p25,v_p75,v_fingerprint
  from public.market_manual_evidence_items where evidence_set_id=v_set_id;

  if p_mark_reviewed then
    v_quick:=round(v_p25*0.95)::bigint;
    v_disp:=case when v_median>0 then round(((v_p75-v_p25)::numeric/v_median)*100,2) else null end;
    v_conf:=case when v_count>=8 then .90 when v_count>=5 then .80 else .65 end;
    if coalesce(v_disp,100)<=25 then v_conf:=least(1,v_conf+.05); end if;
    update public.market_manual_evidence_sets set
      status='REVIEWED',comparable_count=v_count,median_asking_cop=v_median,p25_asking_cop=v_p25,p75_asking_cop=v_p75,
      quick_sale_cop=v_quick,dispersion_pct=v_disp,confidence=v_conf,evidence_fingerprint=v_fingerprint,reviewed_at=clock_timestamp()
    where id=v_set_id;
  else
    update public.market_manual_evidence_sets set evidence_fingerprint=v_fingerprint where id=v_set_id;
  end if;

  return jsonb_build_object(
    'ok',true,'external_lot_id',p_external_lot_id,'evidence_set_id',v_set_id,
    'status',case when p_mark_reviewed then 'REVIEWED' else 'DRAFT' end,
    'comparable_count',v_count,'median_asking_cop',case when p_mark_reviewed then v_median else null end,
    'p25_asking_cop',case when p_mark_reviewed then v_p25 else null end,
    'quick_sale_cop',case when p_mark_reviewed then v_quick else null end,
    'confidence',case when p_mark_reviewed then v_conf else 0 end,
    'evidence_fingerprint',v_fingerprint,
    'interpretation','MANUAL_MARKET_EVIDENCE_NOT_AUTOMATIC_VALUATION',
    'buy_signal',false
  );
end$$;

revoke all on function public.dashboard_save_manual_market_evidence(text,jsonb,text,boolean) from public,anon,authenticated;
grant execute on function public.dashboard_save_manual_market_evidence(text,jsonb,text,boolean) to service_role;

create or replace view public.market_manual_valuation_current as
select distinct on(s.lot_id)
  s.lot_id,
  'MANUAL_REVIEWED'::text as source,
  'READY'::text as status,
  null::text as search_term,
  s.comparable_count,
  s.median_asking_cop,
  s.p25_asking_cop,
  s.p75_asking_cop,
  s.quick_sale_cop,
  s.dispersion_pct,
  s.confidence,
  s.reviewed_at as observed_at,
  s.source_note as note,
  s.id as evidence_set_id,
  s.evidence_fingerprint,
  'MANUAL_REVIEWED'::text as evidence_origin
from public.market_manual_evidence_sets s
where s.status='REVIEWED' and s.reviewed_at is not null and s.comparable_count>=3
order by s.lot_id,s.reviewed_at desc,s.id desc;
revoke all on public.market_manual_valuation_current from public,anon,authenticated;
grant select on public.market_manual_valuation_current to service_role;

create or replace view public.market_valuation_effective_current as
with candidates as(
  select mv.lot_id,mv.source,mv.status,mv.search_term,mv.comparable_count,mv.median_asking_cop,mv.p25_asking_cop,mv.p75_asking_cop,
    mv.quick_sale_cop,mv.dispersion_pct,mv.confidence,mv.observed_at,mv.note,null::bigint as evidence_set_id,null::text as evidence_fingerprint,
    'MERCADOLIBRE_PIPELINE'::text as evidence_origin
  from public.market_valuations mv
  union all
  select lot_id,source,status,search_term,comparable_count,median_asking_cop,p25_asking_cop,p75_asking_cop,quick_sale_cop,
    dispersion_pct,confidence,observed_at,note,evidence_set_id,evidence_fingerprint,evidence_origin
  from public.market_manual_valuation_current
), ranked as(
  select c.*,row_number() over(partition by lot_id order by
    case status when 'READY' then 0 when 'LOW_EVIDENCE' then 1 when 'NO_MATCH' then 2 when 'AUTH_REQUIRED' then 3 else 4 end,
    observed_at desc nulls last,
    case evidence_origin when 'MANUAL_REVIEWED' then 0 else 1 end
  ) as rn from candidates c
)
select lot_id,source,status,search_term,comparable_count,median_asking_cop,p25_asking_cop,p75_asking_cop,quick_sale_cop,
  dispersion_pct,confidence,observed_at,note,evidence_set_id,evidence_fingerprint,evidence_origin
from ranked where rn=1;
revoke all on public.market_valuation_effective_current from public,anon,authenticated;
grant select on public.market_valuation_effective_current to service_role;

-- Preserve every pre-v0.44 column in the exact existing order so dependent views keep stable attnums.
-- New provenance columns are appended only after market_validation_available.
create or replace view public.lot_market_intelligence_current as
select o.*,
  mv.status market_status,
  mv.comparable_count market_comparable_count_live,
  mv.median_asking_cop,mv.p25_asking_cop,mv.p75_asking_cop,mv.quick_sale_cop market_quick_sale_cop,
  mv.dispersion_pct market_dispersion_pct,mv.confidence market_confidence,
  case when mv.status='READY' and mv.quick_sale_cop is not null and o.fasecolda_current_cop is not null
    then least(mv.quick_sale_cop,round(o.fasecolda_current_cop*0.95)::bigint) end conservative_resale_market_validated_cop,
  case when mv.status='READY' and mv.comparable_count>=3 then true else false end market_validation_available,
  mv.source as market_validation_source,
  mv.evidence_origin as market_evidence_origin,
  mv.evidence_set_id as market_evidence_set_id,
  mv.evidence_fingerprint as market_evidence_fingerprint,
  mv.observed_at as market_evidence_observed_at
from public.lot_opportunity_preliminary o
left join public.market_valuation_effective_current mv on mv.lot_id=o.lot_id;
revoke all on public.lot_market_intelligence_current from public,anon,authenticated;
grant select on public.lot_market_intelligence_current to service_role;

create or replace view public.dashboard_market_review_queue_v44 as
select
  r.external_lot_id,r.lot_id,r.title,l.model_year,r.city,r.seller,r.current_bid_cop,r.closes_at,r.hours_to_close,r.review_state,r.review_score,
  r.readiness_status,r.next_action,r.blocker_count,r.blockers,r.fasecolda_status,
  ev.status as effective_market_status,ev.evidence_origin as market_evidence_origin,ev.comparable_count as market_comparable_count,
  ev.p25_asking_cop,ev.quick_sale_cop,ev.confidence as market_confidence,ev.observed_at as market_observed_at,
  mm.evidence_set_id as manual_evidence_set_id,mm.comparable_count as manual_comparable_count,mm.evidence_fingerprint as manual_evidence_fingerprint,
  mm.observed_at as manual_reviewed_at,
  'MARKET_REVIEW_NOT_BUY_SIGNAL'::text as interpretation
from public.dashboard_economic_readiness_current r
join public.auction_lots l on l.id=r.lot_id
left join public.market_valuation_effective_current ev on ev.lot_id=r.lot_id
left join public.market_manual_valuation_current mm on mm.lot_id=r.lot_id
where r.readiness_status='BLOCKED' and r.blockers @> array['MARKET_NOT_VALIDATED']::text[];
revoke all on public.dashboard_market_review_queue_v44 from public,anon,authenticated;
grant select on public.dashboard_market_review_queue_v44 to service_role;

comment on table public.market_manual_evidence_sets is 'Immutable manual market-evidence submissions. REVIEWED requires >=3 same-year HTTPS comparables; evidence is not a buy signal.';
comment on function public.dashboard_save_manual_market_evidence(text,jsonb,text,boolean) is 'Stores auditable manual market evidence. Never writes Fasecolda, costs, bid, ROI or final decision directly.';
comment on view public.market_valuation_effective_current is 'Effective market evidence preserving origin. READY evidence may come from the Mercado Libre pipeline or explicitly MANUAL_REVIEWED evidence.';
comment on view public.dashboard_market_review_queue_v44 is 'Human market evidence queue. MARKET_REVIEW_NOT_BUY_SIGNAL.';
