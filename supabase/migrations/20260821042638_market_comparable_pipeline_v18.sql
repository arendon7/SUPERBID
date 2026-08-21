create table if not exists public.market_comparable_queue (
  lot_id bigint primary key references public.auction_lots(id) on delete cascade,
  status text not null default 'PENDING' check (status in ('PENDING','RETRY','DONE','AUTH_REQUIRED','NO_MATCH','PAUSED')),
  next_run_at timestamptz not null default now(),last_run_at timestamptz,last_success_at timestamptz,
  consecutive_errors integer not null default 0,last_error text,created_at timestamptz not null default now(),updated_at timestamptz not null default now()
);
create table if not exists public.market_valuations (
  lot_id bigint primary key references public.auction_lots(id) on delete cascade,
  source text not null default 'MERCADOLIBRE_MCO',status text not null check(status in ('READY','LOW_EVIDENCE','NO_MATCH','AUTH_REQUIRED','ERROR')),
  search_term text,comparable_count integer not null default 0,median_asking_cop bigint,p25_asking_cop bigint,p75_asking_cop bigint,
  quick_sale_cop bigint,dispersion_pct numeric,confidence numeric not null default 0,observed_at timestamptz not null default now(),note text
);
alter table public.market_comparable_queue enable row level security;
alter table public.market_valuations enable row level security;
revoke all on public.market_comparable_queue,public.market_valuations from anon,authenticated;
grant select,insert,update,delete on public.market_comparable_queue,public.market_valuations to service_role;
create index if not exists ix_market_comparable_queue_due on public.market_comparable_queue(status,next_run_at);
create index if not exists ix_market_comparables_lot_match on public.market_comparables(lot_id,match_score desc,observed_at desc);

create or replace function public.enqueue_market_comparable() returns trigger language plpgsql security definer set search_path=public,pg_catalog as $$
begin
  if new.model_year is not null and new.title is not null then
    insert into public.market_comparable_queue(lot_id,status,next_run_at,updated_at) values(new.id,'PENDING',clock_timestamp(),clock_timestamp())
    on conflict(lot_id) do update set status=case when public.market_comparable_queue.status='PAUSED' then 'PAUSED' else 'PENDING' end,
      next_run_at=case when public.market_comparable_queue.status='PAUSED' then public.market_comparable_queue.next_run_at else clock_timestamp() end,updated_at=clock_timestamp();
  end if; return new;
end $$;
revoke all on function public.enqueue_market_comparable() from public,anon,authenticated; grant execute on function public.enqueue_market_comparable() to service_role;
drop trigger if exists trg_enqueue_market_comparable on public.auction_lots;
create trigger trg_enqueue_market_comparable after insert or update of title,model_year on public.auction_lots for each row execute function public.enqueue_market_comparable();
insert into public.market_comparable_queue(lot_id,status,next_run_at) select l.id,'PENDING',clock_timestamp() from public.auction_lots l where l.model_year is not null and l.title is not null on conflict(lot_id) do nothing;

create or replace function public.market_search_term(p_lot_id bigint) returns text language sql stable set search_path=public,pg_catalog as $$
  select trim(concat_ws(' ',nullif(public.fasecolda_search_term(l.title),''),l.model_year::text)) from public.auction_lots l where l.id=p_lot_id
$$;
revoke all on function public.market_search_term(bigint) from public,anon,authenticated; grant execute on function public.market_search_term(bigint) to service_role;

create or replace function public.market_match_lot(p_lot_id bigint) returns jsonb language plpgsql security definer set search_path=public,vault,extensions,pg_catalog as $$
declare
  l record; c record; v_token text; v_term text; v_uri text; v_resp extensions.http_response; v_json jsonb; v_item jsonb; v_attrs jsonb;
  v_brand text; v_model text; v_trim text; v_year integer; v_km integer; v_city text; v_price bigint; v_score numeric;
  v_count integer:=0; v_med bigint; v_p25 bigint; v_p75 bigint; v_quick bigint; v_disp numeric; v_conf numeric; v_status text;
begin
  select * into l from public.auction_lots where id=p_lot_id;
  if not found or l.model_year is null or l.title is null then return jsonb_build_object('ok',false,'status','NO_MATCH'); end if;
  select * into c from public.market_connections where source='MERCADOLIBRE_MCO';
  if not found or c.status<>'READY' then
    insert into public.market_valuations(lot_id,status,search_term,comparable_count,confidence,observed_at,note)
    values(p_lot_id,'AUTH_REQUIRED',public.market_search_term(p_lot_id),0,0,clock_timestamp(),'Mercado Libre OAuth connection is not READY.')
    on conflict(lot_id) do update set status='AUTH_REQUIRED',search_term=excluded.search_term,comparable_count=0,confidence=0,observed_at=clock_timestamp(),note=excluded.note;
    return jsonb_build_object('ok',false,'status','AUTH_REQUIRED');
  end if;
  if c.access_expires_at is null or c.access_expires_at<clock_timestamp()+interval '30 minutes' then
    perform public.meli_refresh_access_token(); select * into c from public.market_connections where source='MERCADOLIBRE_MCO';
    if c.status<>'READY' then return jsonb_build_object('ok',false,'status',c.status); end if;
  end if;
  v_token:=public.market_secret_get('meli_access_token'); if v_token is null then return jsonb_build_object('ok',false,'status','AUTH_REQUIRED'); end if;
  v_term:=public.market_search_term(p_lot_id); v_uri:='https://api.mercadolibre.com/sites/MCO/search?q='||extensions.urlencode(v_term)||'&limit=50';
  select * into v_resp from extensions.http(row('GET'::extensions.http_method,v_uri::varchar,
    array[extensions.http_header('authorization','Bearer '||v_token),extensions.http_header('accept','application/json')],null::varchar,null::varchar)::extensions.http_request);
  if v_resp.status<>200 then raise exception 'Mercado Libre search HTTP %',v_resp.status; end if; v_json:=v_resp.content::jsonb;
  delete from public.market_comparables where lot_id=p_lot_id and source='MERCADOLIBRE_MCO' and observed_at>=date_trunc('day',clock_timestamp());
  if jsonb_typeof(v_json->'results')='array' then
    for v_item in select value from jsonb_array_elements(v_json->'results') loop
      v_attrs:=coalesce(v_item->'attributes','[]'::jsonb);
      select max(x->>'value_name') filter(where x->>'id'='BRAND'),max(x->>'value_name') filter(where x->>'id' in ('MODEL','CAR_AND_VAN_MODEL')),
        max(x->>'value_name') filter(where x->>'id' in ('TRIM','SHORT_VERSION','CAR_AND_VAN_SUBMODEL')),
        max(nullif(regexp_replace(coalesce(x->>'value_name',''),'[^0-9]','','g'),'')::integer) filter(where x->>'id'='VEHICLE_YEAR'),
        max(coalesce((x->'value_struct'->>'number')::numeric::integer,nullif(regexp_replace(coalesce(x->>'value_name',''),'[^0-9]','','g'),'')::integer)) filter(where x->>'id'='KILOMETERS')
      into v_brand,v_model,v_trim,v_year,v_km from jsonb_array_elements(v_attrs) x;
      v_price:=nullif(v_item->>'price','')::numeric::bigint; v_city:=coalesce(v_item#>>'{location,city,name}',v_item#>>'{address,city_name}');
      if v_price is null or v_price<=0 or coalesce(v_item->>'currency_id','COP')<>'COP' then continue; end if;
      if v_year is distinct from l.model_year then continue; end if;
      if not public.fasecolda_line_compatible(l.title,concat_ws(' ',v_brand,v_model,v_trim)) then continue; end if;
      v_score:=greatest(extensions.similarity(public.vehicle_norm(split_part(l.title,' MOD',1)),public.vehicle_norm(concat_ws(' ',v_brand,v_model,v_trim))),
        extensions.word_similarity(public.vehicle_norm(split_part(l.title,' MOD',1)),public.vehicle_norm(concat_ws(' ',v_brand,v_model,v_trim))));
      if v_score<0.30 then continue; end if;
      insert into public.market_comparables(lot_id,source,external_id,url,observed_at,asking_price_cop,brand,line,version,model_year,mileage_km,city,seller_type,match_score,raw_json)
      values(p_lot_id,'MERCADOLIBRE_MCO',v_item->>'id',v_item->>'permalink',date_trunc('day',clock_timestamp()),v_price,v_brand,v_model,v_trim,v_year,v_km,v_city,
        case when coalesce(v_item#>>'{seller,car_dealer}','false')='true' then 'DEALER' else null end,v_score,
        jsonb_strip_nulls(jsonb_build_object('title',v_item->>'title','category_id',v_item->>'category_id','listing_type_id',v_item->>'listing_type_id')))
      on conflict(source,external_id,observed_at) do update set lot_id=excluded.lot_id,asking_price_cop=excluded.asking_price_cop,url=excluded.url,brand=excluded.brand,line=excluded.line,
        version=excluded.version,model_year=excluded.model_year,mileage_km=excluded.mileage_km,city=excluded.city,seller_type=excluded.seller_type,match_score=excluded.match_score,raw_json=excluded.raw_json;
    end loop;
  end if;
  with vals as (select asking_price_cop from public.market_comparables where lot_id=p_lot_id and source='MERCADOLIBRE_MCO' and observed_at>=date_trunc('day',clock_timestamp()) and match_score>=0.30)
  select count(*)::integer,percentile_cont(0.5) within group(order by asking_price_cop)::bigint,percentile_cont(0.25) within group(order by asking_price_cop)::bigint,
    percentile_cont(0.75) within group(order by asking_price_cop)::bigint into v_count,v_med,v_p25,v_p75 from vals;
  if v_count=0 then v_status:='NO_MATCH';v_conf:=0;v_quick:=null;v_disp:=null;
  else
    v_quick:=round(v_p25*0.95)::bigint; v_disp:=case when v_med>0 then round(((v_p75-v_p25)::numeric/v_med)*100,2) else null end;
    v_conf:=case when v_count>=8 then .90 when v_count>=5 then .80 when v_count>=3 then .65 else .45 end;
    if coalesce(v_disp,100)<=25 then v_conf:=least(1,v_conf+.05); end if; v_status:=case when v_count>=3 then 'READY' else 'LOW_EVIDENCE' end;
  end if;
  insert into public.market_valuations(lot_id,source,status,search_term,comparable_count,median_asking_cop,p25_asking_cop,p75_asking_cop,quick_sale_cop,dispersion_pct,confidence,observed_at,note)
  values(p_lot_id,'MERCADOLIBRE_MCO',v_status,v_term,v_count,v_med,v_p25,v_p75,v_quick,v_disp,v_conf,clock_timestamp(),
    case when v_status='READY' then 'Authenticated Mercado Libre Colombia asking-price comparables; quick-sale is P25 less 5%.' when v_status='LOW_EVIDENCE' then 'Fewer than 3 compatible listings; do not use as final market validation.' else 'No compatible active listings found.' end)
  on conflict(lot_id) do update set source=excluded.source,status=excluded.status,search_term=excluded.search_term,comparable_count=excluded.comparable_count,median_asking_cop=excluded.median_asking_cop,
    p25_asking_cop=excluded.p25_asking_cop,p75_asking_cop=excluded.p75_asking_cop,quick_sale_cop=excluded.quick_sale_cop,dispersion_pct=excluded.dispersion_pct,confidence=excluded.confidence,observed_at=clock_timestamp(),note=excluded.note;
  return jsonb_build_object('ok',true,'status',v_status,'comparable_count',v_count,'median_asking_cop',v_med,'p25_asking_cop',v_p25,'quick_sale_cop',v_quick,'dispersion_pct',v_disp,'confidence',v_conf);
end $$;
revoke all on function public.market_match_lot(bigint) from public,anon,authenticated; grant execute on function public.market_match_lot(bigint) to service_role;

create or replace function public.market_match_due(p_limit integer default 4) returns jsonb language plpgsql security definer set search_path=public,pg_catalog as $$
declare q record;r jsonb;n integer:=0;okn integer:=0;errs integer:=0;e integer;conn_status text;
begin
  p_limit:=greatest(1,least(coalesce(p_limit,4),10)); select status into conn_status from public.market_connections where source='MERCADOLIBRE_MCO';
  if conn_status is distinct from 'READY' then update public.market_comparable_queue set status='AUTH_REQUIRED',updated_at=clock_timestamp() where status in ('PENDING','RETRY') and next_run_at<=clock_timestamp();
    return jsonb_build_object('ok',false,'status',coalesce(conn_status,'APP_REQUIRED'),'processed',0); end if;
  update public.market_comparable_queue set status='PENDING',next_run_at=clock_timestamp(),updated_at=clock_timestamp() where status='AUTH_REQUIRED';
  for q in select * from public.market_comparable_queue where status in ('PENDING','RETRY') and next_run_at<=clock_timestamp() order by next_run_at limit p_limit for update skip locked loop
    n:=n+1; begin r:=public.market_match_lot(q.lot_id);
      update public.market_comparable_queue set status=case when r->>'status' in ('READY','LOW_EVIDENCE') then 'DONE' when r->>'status'='NO_MATCH' then 'NO_MATCH' else 'AUTH_REQUIRED' end,
        last_run_at=clock_timestamp(),last_success_at=clock_timestamp(),consecutive_errors=0,last_error=null,next_run_at=clock_timestamp()+interval '24 hours',updated_at=clock_timestamp() where lot_id=q.lot_id; okn:=okn+1;
    exception when others then errs:=errs+1;e:=coalesce(q.consecutive_errors,0)+1;
      update public.market_comparable_queue set status=case when e>=6 then 'PAUSED' else 'RETRY' end,last_run_at=clock_timestamp(),consecutive_errors=e,last_error=left(sqlerrm,1000),
        next_run_at=clock_timestamp()+make_interval(mins=>least(360,5*(2^least(e,6))::integer)),updated_at=clock_timestamp() where lot_id=q.lot_id;
    end;
  end loop; return jsonb_build_object('ok',errs=0,'status','READY','processed',n,'success',okn,'errors',errs);
end $$;
revoke all on function public.market_match_due(integer) from public,anon,authenticated; grant execute on function public.market_match_due(integer) to service_role;

create or replace view public.lot_market_intelligence_current as
select o.*,mv.status market_status,mv.comparable_count market_comparable_count_live,mv.median_asking_cop,mv.p25_asking_cop,mv.p75_asking_cop,mv.quick_sale_cop market_quick_sale_cop,
  mv.dispersion_pct market_dispersion_pct,mv.confidence market_confidence,
  case when mv.status='READY' and mv.quick_sale_cop is not null and o.fasecolda_current_cop is not null then least(mv.quick_sale_cop,round(o.fasecolda_current_cop*0.95)::bigint) end conservative_resale_market_validated_cop,
  case when mv.status='READY' and mv.comparable_count>=3 then true else false end market_validation_available
from public.lot_opportunity_preliminary o left join public.market_valuations mv on mv.lot_id=o.lot_id;
revoke all on public.lot_market_intelligence_current from public,anon,authenticated; grant select on public.lot_market_intelligence_current to service_role;
