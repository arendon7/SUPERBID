create extension if not exists pg_trgm with schema extensions;
create extension if not exists unaccent with schema extensions;

create table if not exists public.fasecolda_references (
  code text primary key,
  homologous_code text,
  brand text,
  vehicle_class text,
  reference1 text,
  reference2 text,
  reference3 text,
  service text,
  fuel text,
  transmission text,
  engine_cc integer,
  current_description text,
  fetched_at timestamptz not null default now()
);

create table if not exists public.fasecolda_value_history (
  code text not null references public.fasecolda_references(code) on delete cascade,
  history_code text not null,
  model_year integer not null,
  value_date date not null,
  value_cop bigint not null,
  fetched_at timestamptz not null default now(),
  primary key(code,model_year,value_date)
);

create table if not exists public.lot_fasecolda_candidates (
  lot_id bigint not null references public.auction_lots(id) on delete cascade,
  code text not null references public.fasecolda_references(code) on delete cascade,
  model_year integer not null,
  score numeric not null,
  current_value_cop bigint not null,
  description text,
  rank_no integer,
  evaluated_at timestamptz not null default now(),
  primary key(lot_id,code)
);

create table if not exists public.lot_fasecolda_matches (
  lot_id bigint primary key references public.auction_lots(id) on delete cascade,
  status text not null check(status in ('HIGH','MEDIUM','AMBIGUOUS','UNMATCHED','ERROR')),
  search_term text,
  best_code text references public.fasecolda_references(code),
  best_description text,
  best_score numeric,
  second_score numeric,
  candidate_count integer not null default 0,
  current_value_cop bigint,
  candidate_min_cop bigint,
  candidate_median_cop bigint,
  candidate_max_cop bigint,
  latest_history_date date,
  confidence numeric not null default 0,
  matched_at timestamptz not null default now(),
  note text
);

create table if not exists public.fasecolda_match_queue (
  lot_id bigint primary key references public.auction_lots(id) on delete cascade,
  status text not null default 'PENDING' check(status in ('PENDING','RETRY','DONE','REVIEW','UNMATCHED','PAUSED')),
  next_run_at timestamptz not null default now(),
  last_run_at timestamptz,
  last_success_at timestamptz,
  consecutive_errors integer not null default 0,
  last_error text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists ix_fasecolda_history_lookup on public.fasecolda_value_history(code,model_year,value_date desc);
create index if not exists ix_lot_fasecolda_candidates_lot_score on public.lot_fasecolda_candidates(lot_id,score desc);
create index if not exists ix_fasecolda_match_queue_due on public.fasecolda_match_queue(status,next_run_at);

alter table public.fasecolda_references enable row level security;
alter table public.fasecolda_value_history enable row level security;
alter table public.lot_fasecolda_candidates enable row level security;
alter table public.lot_fasecolda_matches enable row level security;
alter table public.fasecolda_match_queue enable row level security;
revoke all on table public.fasecolda_references,public.fasecolda_value_history,public.lot_fasecolda_candidates,public.lot_fasecolda_matches,public.fasecolda_match_queue from anon,authenticated;

create or replace function public.vehicle_norm(p_text text)
returns text language sql immutable
set search_path=public,extensions,pg_catalog
as $$
  select trim(regexp_replace(upper(extensions.unaccent(coalesce(p_text,''))),'[^A-Z0-9]+',' ','g'));
$$;

create or replace function public.fasecolda_search_term(p_title text)
returns text language plpgsql immutable
set search_path=public,extensions,pg_catalog
as $$
declare
  v text; a text[]; out_words text[]:='{}'; w text;
begin
  v:=public.vehicle_norm(split_part(coalesce(p_title,''),' MOD',1));
  a:=regexp_split_to_array(v,'\s+');
  foreach w in array a loop
    if w=any(array['VOLQUETA','CAMION','CAMIONETA','TRACTOCAMION','TRACTOMULA','BUS','MICROBUS','VEHICULO']) and cardinality(out_words)=0 then continue; end if;
    if w=any(array['FL','MOD','MODELO','PLACA','RP','UBIC']) then continue; end if;
    out_words:=array_append(out_words,w);
    if cardinality(out_words)>=2 and out_words[2]<>'NEW' then exit; end if;
    if cardinality(out_words)>=3 then exit; end if;
  end loop;
  if cardinality(out_words)=0 then return null; end if;
  return array_to_string(out_words,' ');
end
$$;

create or replace function public.fasecolda_match_lot(p_lot_id bigint,p_fetch_history boolean default true)
returns jsonb language plpgsql security definer
set search_path=public,extensions,pg_catalog
as $$
declare
  v_lot record; v_term text; v_search_uri text; v_detail_uri text; v_hist_uri text;
  v_resp record; v_search jsonb; v_detail jsonb; v_hist jsonb; v_codes text;
  v_item jsonb; v_model jsonb; v_code text; v_homologous text; v_desc text;
  v_value bigint; v_score numeric; v_candidate_count integer:=0; v_best_code text;
  v_best_desc text; v_best_score numeric; v_second_score numeric; v_best_value bigint;
  v_min bigint; v_median bigint; v_max bigint; v_status text; v_conf numeric;
  v_history_code text; v_hist_point jsonb; v_latest_date date; v_latest_value bigint;
  v_search_title text;
begin
  select * into v_lot from public.auction_lots where id=p_lot_id;
  if not found then raise exception 'Lot % not found',p_lot_id; end if;
  if v_lot.model_year is null or v_lot.title is null then
    insert into public.lot_fasecolda_matches(lot_id,status,search_term,candidate_count,confidence,matched_at,note)
    values(p_lot_id,'UNMATCHED',null,0,0,clock_timestamp(),'Lot has no model year/title for Fasecolda matching.')
    on conflict(lot_id) do update set status='UNMATCHED',candidate_count=0,confidence=0,matched_at=clock_timestamp(),note=excluded.note;
    return jsonb_build_object('ok',true,'status','UNMATCHED','reason','missing_title_or_year');
  end if;

  v_term:=public.fasecolda_search_term(v_lot.title);
  if v_term is null or length(v_term)<2 then raise exception 'Could not derive Fasecolda search term'; end if;
  v_search_uri:='https://fasecoldaback.quantil.co/api/busqueda/'||extensions.urlencode(v_term);
  select * into v_resp from extensions.http_get(v_search_uri::varchar);
  if v_resp.status<>200 then raise exception 'Fasecolda search HTTP %',v_resp.status; end if;
  v_search:=v_resp.content::jsonb;
  if jsonb_typeof(v_search->'codigos')<>'array' or jsonb_array_length(v_search->'codigos')=0 then
    delete from public.lot_fasecolda_candidates where lot_id=p_lot_id;
    insert into public.lot_fasecolda_matches(lot_id,status,search_term,candidate_count,confidence,matched_at,note)
    values(p_lot_id,'UNMATCHED',v_term,0,0,clock_timestamp(),'Fasecolda public search returned no codes.')
    on conflict(lot_id) do update set status='UNMATCHED',search_term=excluded.search_term,candidate_count=0,confidence=0,matched_at=clock_timestamp(),note=excluded.note;
    return jsonb_build_object('ok',true,'status','UNMATCHED','search_term',v_term,'candidates',0);
  end if;

  select string_agg(value#>>'{}',',' order by ord) into v_codes
  from jsonb_array_elements(v_search->'codigos') with ordinality x(value,ord) where ord<=22;
  v_detail_uri:='https://fasecoldaback.quantil.co/api/listacodigosid/consultabycodigo/'||v_codes;
  select * into v_resp from extensions.http_get(v_detail_uri::varchar);
  if v_resp.status<>200 then raise exception 'Fasecolda detail HTTP %',v_resp.status; end if;
  v_detail:=v_resp.content::jsonb;
  if jsonb_typeof(v_detail)<>'array' then raise exception 'Fasecolda detail unavailable: %',left(v_resp.content,300); end if;

  delete from public.lot_fasecolda_candidates where lot_id=p_lot_id;
  v_search_title:=split_part(public.vehicle_norm(v_lot.title),' PLACA',1);

  for v_item in select value from jsonb_array_elements(v_detail) loop
    v_code:=nullif(v_item->>'codigo','');
    if v_code is null then continue; end if;
    v_homologous:=nullif(v_item->>'homoloCodigo','');
    v_desc:=concat_ws(' ',v_item->>'marca',v_item->>'referenciaUno',v_item->>'referenciaDos',v_item->>'referenciaTres');
    v_value:=null;
    if jsonb_typeof(v_item->'valorModelo')='array' then
      select round((m->>'valor')::numeric*1000)::bigint into v_value
      from jsonb_array_elements(v_item->'valorModelo') m
      where (m->>'modelo')::integer=v_lot.model_year and upper(coalesce(m->>'estado','USADO'))='USADO' limit 1;
    end if;
    if v_value is null then continue; end if;

    insert into public.fasecolda_references(code,homologous_code,brand,vehicle_class,reference1,reference2,reference3,service,fuel,transmission,engine_cc,current_description,fetched_at)
    values(v_code,v_homologous,v_item->>'marca',v_item->>'clase',v_item->>'referenciaUno',v_item->>'referenciaDos',v_item->>'referenciaTres',v_item->>'servicio',v_item->>'combustible',v_item->>'tipoCaja',nullif(v_item->>'cilindraje','')::numeric::integer,v_desc,clock_timestamp())
    on conflict(code) do update set homologous_code=excluded.homologous_code,brand=excluded.brand,vehicle_class=excluded.vehicle_class,reference1=excluded.reference1,reference2=excluded.reference2,reference3=excluded.reference3,service=excluded.service,fuel=excluded.fuel,transmission=excluded.transmission,engine_cc=excluded.engine_cc,current_description=excluded.current_description,fetched_at=clock_timestamp();

    insert into public.fasecolda_values(source_file,imported_at,code,homologous_code,brand,vehicle_class,reference1,reference2,reference3,service,model_year,value_cop,record_key)
    values('fasecolda_api_current',clock_timestamp(),v_code,v_homologous,v_item->>'marca',v_item->>'clase',v_item->>'referenciaUno',v_item->>'referenciaDos',v_item->>'referenciaTres',v_item->>'servicio',v_lot.model_year,v_value,'api-current|'||v_code||'|'||v_lot.model_year||'|'||current_date)
    on conflict(record_key) do update set value_cop=excluded.value_cop,imported_at=clock_timestamp();

    v_score:=greatest(extensions.similarity(public.vehicle_norm(v_search_title),public.vehicle_norm(v_desc)),extensions.word_similarity(public.vehicle_norm(v_search_title),public.vehicle_norm(v_desc)));
    if public.vehicle_norm(v_desc) like public.vehicle_norm(v_term)||'%' then v_score:=least(1,v_score+0.03); end if;
    insert into public.lot_fasecolda_candidates(lot_id,code,model_year,score,current_value_cop,description,evaluated_at)
    values(p_lot_id,v_code,v_lot.model_year,v_score,v_value,v_desc,clock_timestamp())
    on conflict(lot_id,code) do update set score=excluded.score,current_value_cop=excluded.current_value_cop,description=excluded.description,evaluated_at=clock_timestamp();
  end loop;

  with ranked as (
    select code,description,score,current_value_cop,row_number() over(order by score desc,code) rn from public.lot_fasecolda_candidates where lot_id=p_lot_id
  ),agg as (
    select count(*) cnt,min(current_value_cop) mn,percentile_cont(0.5) within group(order by current_value_cop)::bigint med,max(current_value_cop) mx from ranked
  )
  select a.cnt,a.mn,a.med,a.mx,max(r.code) filter(where r.rn=1),max(r.description) filter(where r.rn=1),max(r.score) filter(where r.rn=1),max(r.current_value_cop) filter(where r.rn=1),max(r.score) filter(where r.rn=2)
  into v_candidate_count,v_min,v_median,v_max,v_best_code,v_best_desc,v_best_score,v_best_value,v_second_score
  from agg a left join ranked r on true group by a.cnt,a.mn,a.med,a.mx;

  update public.lot_fasecolda_candidates c set rank_no=r.rn
  from (select code,row_number() over(order by score desc,code)::integer rn from public.lot_fasecolda_candidates where lot_id=p_lot_id) r
  where c.lot_id=p_lot_id and c.code=r.code;

  if v_candidate_count=0 then v_status:='UNMATCHED';v_conf:=0;
  elsif v_candidate_count=1 and v_best_score>=0.35 then v_status:='HIGH';v_conf:=least(0.95,0.70+v_best_score*0.25);
  elsif v_best_score>=0.70 then v_status:='HIGH';v_conf:=least(0.95,0.68+v_best_score*0.27);
  elsif v_best_score>=0.55 and (v_second_score is null or v_best_score-v_second_score>=0.07) then v_status:='HIGH';v_conf:=least(0.90,0.60+v_best_score*0.25);
  elsif v_best_score>=0.45 and (v_second_score is null or v_best_score-v_second_score>=0.10) then v_status:='MEDIUM';v_conf:=0.65;
  else v_status:='AMBIGUOUS';v_conf:=case when v_best_score>=0.40 then 0.45 else 0.30 end; end if;

  v_latest_date:=null;v_latest_value:=null;
  if p_fetch_history and v_status='HIGH' and v_best_code is not null then
    select coalesce(nullif(homologous_code,''),code) into v_history_code from public.fasecolda_references where code=v_best_code;
    v_hist_uri:='https://fasecoldaback.quantil.co/api/historic/'||v_history_code||'/'||v_lot.model_year;
    select * into v_resp from extensions.http_get(v_hist_uri::varchar);
    if v_resp.status=200 then
      v_hist:=v_resp.content::jsonb;
      if jsonb_typeof(v_hist->'codes')='array' then
        for v_hist_point in select value from jsonb_array_elements(v_hist->'codes') loop
          begin
            insert into public.fasecolda_value_history(code,history_code,model_year,value_date,value_cop,fetched_at)
            values(v_best_code,v_history_code,v_lot.model_year,(v_hist_point->>'date')::date,round((v_hist_point->>'value')::numeric*1000)::bigint,clock_timestamp())
            on conflict(code,model_year,value_date) do update set value_cop=excluded.value_cop,fetched_at=clock_timestamp();
          exception when others then null; end;
        end loop;
        select value_date,value_cop into v_latest_date,v_latest_value from public.fasecolda_value_history where code=v_best_code and model_year=v_lot.model_year order by value_date desc limit 1;
        if v_latest_value is not null then v_best_value:=v_latest_value; end if;
      end if;
    end if;
  end if;

  insert into public.lot_fasecolda_matches(lot_id,status,search_term,best_code,best_description,best_score,second_score,candidate_count,current_value_cop,candidate_min_cop,candidate_median_cop,candidate_max_cop,latest_history_date,confidence,matched_at,note)
  values(p_lot_id,v_status,v_term,v_best_code,v_best_desc,v_best_score,v_second_score,v_candidate_count,v_best_value,v_min,v_median,v_max,v_latest_date,v_conf,clock_timestamp(),case when v_status='AMBIGUOUS' then 'Multiple Fasecolda versions fit the public lot description; use candidate range until trim is confirmed.' when v_status='MEDIUM' then 'Probable reference; review version before using as exact valuation.' when v_status='HIGH' then 'Best public Fasecolda reference match for make/line/year/title.' else 'No compatible Fasecolda reference with this model year.' end)
  on conflict(lot_id) do update set status=excluded.status,search_term=excluded.search_term,best_code=excluded.best_code,best_description=excluded.best_description,best_score=excluded.best_score,second_score=excluded.second_score,candidate_count=excluded.candidate_count,current_value_cop=excluded.current_value_cop,candidate_min_cop=excluded.candidate_min_cop,candidate_median_cop=excluded.candidate_median_cop,candidate_max_cop=excluded.candidate_max_cop,latest_history_date=excluded.latest_history_date,confidence=excluded.confidence,matched_at=clock_timestamp(),note=excluded.note;

  return jsonb_build_object('ok',true,'status',v_status,'search_term',v_term,'candidate_count',v_candidate_count,'best_code',v_best_code,'best_score',v_best_score,'current_value_cop',v_best_value,'candidate_min_cop',v_min,'candidate_median_cop',v_median,'candidate_max_cop',v_max,'latest_history_date',v_latest_date,'confidence',v_conf);
end
$$;

create or replace function public.fasecolda_match_due(p_limit integer default 8)
returns jsonb language plpgsql security definer
set search_path=public,extensions,pg_catalog
as $$
declare q record;r jsonb;v_processed integer:=0;v_success integer:=0;v_errors integer:=0;v_status text;v_errs integer;
begin
  p_limit:=greatest(1,least(coalesce(p_limit,8),20));
  for q in select fq.* from public.fasecolda_match_queue fq join public.auction_lots l on l.id=fq.lot_id where fq.status in ('PENDING','RETRY') and fq.next_run_at<=clock_timestamp() order by fq.next_run_at,l.last_seen_at desc limit p_limit for update of fq skip locked loop
    v_processed:=v_processed+1;
    begin
      r:=public.fasecolda_match_lot(q.lot_id,true);v_status:=coalesce(r->>'status','UNMATCHED');
      update public.fasecolda_match_queue set status=case when v_status in ('HIGH','MEDIUM') then 'DONE' when v_status='AMBIGUOUS' then 'REVIEW' else 'UNMATCHED' end,last_run_at=clock_timestamp(),last_success_at=clock_timestamp(),consecutive_errors=0,last_error=null,next_run_at=clock_timestamp()+interval '30 days',updated_at=clock_timestamp() where lot_id=q.lot_id;
      v_success:=v_success+1;
    exception when others then
      v_errors:=v_errors+1;v_errs:=coalesce(q.consecutive_errors,0)+1;
      update public.fasecolda_match_queue set status=case when v_errs>=8 then 'PAUSED' else 'RETRY' end,last_run_at=clock_timestamp(),consecutive_errors=v_errs,last_error=left(sqlerrm,1000),next_run_at=clock_timestamp()+make_interval(mins=>least(360,greatest(5,(power(2,least(v_errs,7))*5)::integer))),updated_at=clock_timestamp() where lot_id=q.lot_id;
    end;
  end loop;
  return jsonb_build_object('ok',v_errors=0,'processed',v_processed,'success',v_success,'errors',v_errors);
end
$$;

revoke all on function public.vehicle_norm(text),public.fasecolda_search_term(text),public.fasecolda_match_lot(bigint,boolean),public.fasecolda_match_due(integer) from public,anon,authenticated;
grant execute on function public.fasecolda_match_lot(bigint,boolean),public.fasecolda_match_due(integer) to service_role;

insert into public.fasecolda_match_queue(lot_id,status,next_run_at)
select id,'PENDING',clock_timestamp() from public.auction_lots where title is not null and model_year is not null
on conflict(lot_id) do nothing;
