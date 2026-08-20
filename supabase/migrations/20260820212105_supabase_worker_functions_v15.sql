-- SUPERBID Deal Intelligence v0.15
-- Database-native collector for Supabase/PostgreSQL.
-- Public read-only Superbid endpoints only. No auth, cookies, opaque filters,
-- reserve-price persistence, or bidder identity storage.

create extension if not exists http with schema extensions;
create extension if not exists pg_cron;

create or replace function public.superbid_offer_outcome(p_offer jsonb)
returns text
language sql
immutable
set search_path = pg_catalog
as $$
  select case
    when coalesce((p_offer #>> '{offerStatus,sold}')::boolean, false) then 'SOLD_CONFIRMED'
    when coalesce((p_offer #>> '{offerStatus,removed}')::boolean, false) then 'WITHDRAWN'
    when coalesce((p_offer #>> '{offerStatus,makeYourProposal}')::boolean, false)
      or coalesce((p_offer #>> '{offerStatus,wantToKnowThePrice}')::boolean, false)
      then 'AFTER_MARKET'
    when coalesce((p_offer #>> '{offerStatus,closed}')::boolean, false)
      or coalesce((p_offer #>> '{offerStatus,closedToBids}')::boolean, false)
      then 'CLOSED_OBSERVED'
    when coalesce((p_offer #>> '{offerStatus,giveYourBid}')::boolean, false)
      then 'ACTIVE'
    else 'UNKNOWN'
  end
$$;

create or replace function public.superbid_offer_close_at(p_offer jsonb)
returns timestamptz
language plpgsql
immutable
set search_path = pg_catalog
as $$
declare
  v_ms text;
begin
  v_ms := p_offer->>'endDateTime';
  if v_ms is null or v_ms !~ '^[0-9]+$' then
    return null;
  end if;
  return to_timestamp(v_ms::double precision / 1000.0);
exception when others then
  return null;
end
$$;

create or replace function public.superbid_next_run_at(
  p_closes_at timestamptz,
  p_outcome text,
  p_error_count integer default 0
)
returns timestamptz
language plpgsql
stable
set search_path = pg_catalog
as $$
declare
  v_now timestamptz := clock_timestamp();
  v_delta interval;
  v_minutes integer;
begin
  if coalesce(p_error_count,0) > 0 then
    v_minutes := least(60, greatest(2, (power(2, least(p_error_count, 6)))::integer));
    return v_now + make_interval(mins => v_minutes);
  end if;

  if p_outcome in ('SOLD_CONFIRMED','WITHDRAWN') then
    return v_now + interval '100 years';
  end if;

  if p_closes_at is null then
    return v_now + interval '4 hours';
  end if;

  if p_closes_at > v_now then
    v_delta := p_closes_at - v_now;
    if v_delta > interval '24 hours' then
      return v_now + interval '4 hours';
    elsif v_delta > interval '2 hours' then
      return v_now + interval '30 minutes';
    elsif v_delta > interval '15 minutes' then
      return v_now + interval '5 minutes';
    else
      return v_now + interval '1 minute';
    end if;
  end if;

  -- Post-close monitoring captures extensions, conditional/After Market changes
  -- and explicit sold status without assuming that a closed bid equals a sale.
  v_delta := v_now - p_closes_at;
  if v_delta <= interval '2 hours' then
    return v_now + interval '5 minutes';
  elsif v_delta <= interval '24 hours' then
    return v_now + interval '30 minutes';
  elsif v_delta <= interval '14 days' then
    return v_now + interval '6 hours';
  elsif v_delta <= interval '30 days' then
    return v_now + interval '24 hours';
  else
    return v_now + interval '30 days';
  end if;
end
$$;

create or replace function public.superbid_upsert_offer(
  p_offer jsonb,
  p_source_type text default 'superbid_public_http_cron',
  p_write_snapshot boolean default true
)
returns bigint
language plpgsql
security definer
set search_path = public, extensions, pg_catalog
as $$
declare
  v_external_id text;
  v_url text;
  v_title text;
  v_brand text;
  v_line text;
  v_model_year integer;
  v_plate text;
  v_city text;
  v_seller text;
  v_initial_bid bigint;
  v_price bigint;
  v_bid_count integer;
  v_close_text text;
  v_close_at timestamptz;
  v_outcome text;
  v_lot_id bigint;
  v_commission numeric;
  v_total_bidders integer;
  v_offer_type integer;
  v_att jsonb;
  v_att_url text;
  v_att_name text;
  v_att_kind text;
begin
  v_external_id := nullif(p_offer->>'id','');
  if v_external_id is null then
    raise exception 'Superbid offer is missing id';
  end if;

  v_url := 'https://www.superbid.com.co/oferta/x-' || v_external_id;
  v_title := coalesce(p_offer #>> '{product,shortDesc}', p_offer->>'offerDescription');
  v_brand := coalesce(
    nullif(p_offer #>> '{product,brand,description}',''),
    nullif(p_offer #>> '{product,brand,name}',''),
    nullif(split_part(coalesce(v_title,''),' ',1),'')
  );
  v_line := coalesce(
    nullif(p_offer #>> '{product,model,description}',''),
    nullif(p_offer #>> '{product,model,name}','')
  );

  begin
    v_model_year := nullif(substring(coalesce(v_title,'') from 'MOD[.]?[[:space:]]*([12][0-9]{3})'),'')::integer;
  exception when others then
    v_model_year := null;
  end;

  v_plate := nullif(substring(coalesce(v_title,'') from 'PLACA:[[:space:]]*([A-Z0-9]+)'),'');
  v_city := nullif(p_offer #>> '{product,location,city}','');
  v_seller := nullif(p_offer #>> '{seller,name}','');

  begin
    v_initial_bid := nullif(p_offer #>> '{offerDetail,initialBidValue}','')::numeric::bigint;
  exception when others then
    v_initial_bid := null;
  end;
  begin
    v_price := nullif(p_offer->>'price','')::numeric::bigint;
  exception when others then
    v_price := null;
  end;
  begin
    v_bid_count := nullif(p_offer->>'totalBids','')::integer;
  exception when others then
    v_bid_count := null;
  end;
  begin
    v_total_bidders := nullif(p_offer->>'totalBidders','')::integer;
  exception when others then
    v_total_bidders := null;
  end;
  begin
    v_commission := nullif(p_offer #>> '{groupOffer,commissionPercent}','')::numeric;
  exception when others then
    v_commission := null;
  end;
  begin
    v_offer_type := nullif(p_offer->>'offerTypeId','')::integer;
  exception when others then
    v_offer_type := null;
  end;

  v_close_text := nullif(p_offer->>'endDate','');
  v_close_at := public.superbid_offer_close_at(p_offer);
  v_outcome := public.superbid_offer_outcome(p_offer);

  insert into public.auction_lots(
    source, external_lot_id, url, title, brand, line, model_year, plate,
    plate_is_partial, city, seller, initial_bid_cop, first_seen_at, last_seen_at
  )
  values(
    'superbid_co', v_external_id, v_url, v_title, v_brand, v_line, v_model_year, v_plate,
    case when v_plate is null then false else length(v_plate) < 6 end,
    v_city, v_seller, v_initial_bid, clock_timestamp(), clock_timestamp()
  )
  on conflict(source, external_lot_id) do update set
    url = excluded.url,
    title = coalesce(excluded.title, public.auction_lots.title),
    brand = coalesce(excluded.brand, public.auction_lots.brand),
    line = coalesce(excluded.line, public.auction_lots.line),
    model_year = coalesce(excluded.model_year, public.auction_lots.model_year),
    plate = coalesce(excluded.plate, public.auction_lots.plate),
    plate_is_partial = case
      when excluded.plate is not null then excluded.plate_is_partial
      else public.auction_lots.plate_is_partial
    end,
    city = coalesce(excluded.city, public.auction_lots.city),
    seller = coalesce(excluded.seller, public.auction_lots.seller),
    initial_bid_cop = coalesce(public.auction_lots.initial_bid_cop, excluded.initial_bid_cop),
    last_seen_at = clock_timestamp()
  returning id into v_lot_id;

  if p_write_snapshot then
    insert into public.auction_snapshots(
      lot_id, observed_at, displayed_price_cop, displayed_price_label,
      bid_count, status_text, outcome, closes_at_text, closes_at, evidence
    )
    values(
      v_lot_id,
      clock_timestamp(),
      v_price,
      p_offer->>'priceFormatted',
      v_bid_count,
      p_offer #>> '{offerStatus,statusCode}',
      v_outcome,
      v_close_text,
      v_close_at,
      jsonb_strip_nulls(jsonb_build_object(
        'parser','supabase_cron_v15',
        'source','superbid_public_http',
        'auction_id',p_offer #>> '{auction,id}',
        'auction_desc',p_offer #>> '{auction,desc}',
        'currency_iso',p_offer #>> '{auction,currencyIso}',
        'lot_number',p_offer->>'lotNumber',
        'visits',p_offer->>'visits',
        'total_bidders',v_total_bidders,
        'commission_percent_public',v_commission,
        'offer_type_id',v_offer_type,
        'end_date_time_epoch_ms',p_offer->>'endDateTime'
      ))
    );
  end if;

  insert into public.auction_outcomes(
    lot_id, outcome, closing_price_observed_cop, sale_price_confirmed_cop,
    confidence, confirmation_source, notes, updated_at
  )
  values(
    v_lot_id,
    v_outcome,
    case when v_outcome='CLOSED_OBSERVED' then v_price else null end,
    case when v_outcome='SOLD_CONFIRMED' then v_price else null end,
    case
      when v_outcome='SOLD_CONFIRMED' then 0.99
      when v_outcome in ('WITHDRAWN','CLOSED_OBSERVED','AFTER_MARKET') then 0.93
      when v_outcome='ACTIVE' then 0.90
      else 0.50
    end,
    case when v_outcome='SOLD_CONFIRMED' then 'superbid_public_http:sold' else null end,
    case
      when v_outcome='CLOSED_OBSERVED' then 'Closing value observed; not promoted to confirmed sale.'
      when v_outcome='AFTER_MARKET' then 'After Market/proposal state observed; not a confirmed sale.'
      else null
    end,
    clock_timestamp()
  )
  on conflict(lot_id) do update set
    outcome = case
      when public.auction_outcomes.outcome='SOLD_CONFIRMED' then public.auction_outcomes.outcome
      else excluded.outcome
    end,
    closing_price_observed_cop = case
      when excluded.outcome='CLOSED_OBSERVED'
        then coalesce(excluded.closing_price_observed_cop, public.auction_outcomes.closing_price_observed_cop)
      else public.auction_outcomes.closing_price_observed_cop
    end,
    sale_price_confirmed_cop = case
      when excluded.outcome='SOLD_CONFIRMED'
        then coalesce(excluded.sale_price_confirmed_cop, public.auction_outcomes.sale_price_confirmed_cop)
      else public.auction_outcomes.sale_price_confirmed_cop
    end,
    confidence = case
      when excluded.outcome='SOLD_CONFIRMED' then greatest(public.auction_outcomes.confidence, excluded.confidence)
      else excluded.confidence
    end,
    confirmation_source = coalesce(excluded.confirmation_source, public.auction_outcomes.confirmation_source),
    notes = coalesce(excluded.notes, public.auction_outcomes.notes),
    updated_at = clock_timestamp();

  insert into public.lot_provenance(
    lot_id, source_type, source_url, observed_at, fields, confidence, note
  )
  values(
    v_lot_id,
    p_source_type,
    v_url,
    clock_timestamp(),
    jsonb_strip_nulls(jsonb_build_object(
      'title',v_title is not null,
      'initial_bid_cop',v_initial_bid is not null,
      'displayed_price_cop',v_price is not null,
      'bid_count',v_bid_count is not null,
      'closes_at',v_close_at is not null,
      'outcome',v_outcome,
      'category_id',p_offer #>> '{product,subCategory,category,id}',
      'offer_type_id',v_offer_type
    )),
    case when p_source_type='superbid_public_http_refresh' then 0.95 else 0.92 end,
    'Public Superbid HTTP response; no auth, cookies, opaque filters or reserve-price persistence.'
  )
  on conflict(lot_id, source_type, source_url) do update set
    observed_at = excluded.observed_at,
    fields = excluded.fields,
    confidence = greatest(public.lot_provenance.confidence, excluded.confidence),
    note = excluded.note;

  if jsonb_typeof(p_offer #> '{product,attachments}')='array' then
    for v_att in select value from jsonb_array_elements(p_offer #> '{product,attachments}')
    loop
      v_att_url := nullif(v_att->>'link','');
      v_att_name := coalesce(nullif(v_att->>'originalFileName',''), nullif(v_att->>'fileName',''));
      if v_att_url is null then continue; end if;
      v_att_kind := case
        when lower(coalesce(v_att_name,'')) ~ '(perit|inspecci|avalu)' then 'PERITAJE'
        when lower(coalesce(v_att->>'contentType',''))='application/pdf' then 'DOCUMENTO'
        else 'ANEXO'
      end;
      insert into public.lot_attachments(lot_id,name,url,kind,source,discovered_at)
      values(v_lot_id,v_att_name,v_att_url,v_att_kind,'superbid_product_attachments',clock_timestamp())
      on conflict(lot_id,url) do update set
        name=coalesce(excluded.name,public.lot_attachments.name),kind=excluded.kind,source=excluded.source;
    end loop;
  end if;

  return v_lot_id;
end
$$;

create or replace function public.superbid_discover_open_vehicles(p_max_pages integer default 10,p_page_size integer default 100)
returns jsonb
language plpgsql
security definer
set search_path = public, extensions, pg_catalog
as $$
declare
  v_page integer; v_uri text; v_resp record; v_payload jsonb; v_offer jsonb; v_offers jsonb;
  v_total integer := null; v_pages integer := 0; v_seen integer := 0; v_vehicle integer := 0;
  v_saved integer := 0; v_queued integer := 0; v_lot_id bigint; v_external_id text; v_url text;
  v_close_at timestamptz; v_close_text text; v_outcome text; v_priority integer; v_run_id bigint;
begin
  p_max_pages := greatest(1, least(coalesce(p_max_pages,10), 25));
  p_page_size := greatest(1, least(coalesce(p_page_size,100), 100));
  insert into public.collection_runs(run_type,target,started_at,lots_found,lots_saved,attachments_saved,bids_saved)
  values('CRON_DISCOVERY_HTTP','https://offer-query.superbid.net/offers/',clock_timestamp(),0,0,0,0)
  returning id into v_run_id;

  for v_page in 1..p_max_pages loop
    v_uri := 'https://offer-query.superbid.net/offers/?' || extensions.urlencode(jsonb_build_object(
      'portalId','[17]','requestOrigin','marketplace','locale','es_CO','timeZoneId','UTC','searchType','opened',
      'pageNumber',v_page::text,'pageSize',p_page_size::text,'preOrderBy','orderByFirstOpenedOffers'));
    select * into v_resp from extensions.http_get(v_uri::varchar);
    if v_resp.status <> 200 then raise exception 'Superbid discovery HTTP status % on page %', v_resp.status, v_page; end if;
    v_payload := v_resp.content::jsonb; v_offers := coalesce(v_payload->'offers','[]'::jsonb); v_pages := v_pages + 1;
    if v_total is null then begin v_total := nullif(v_payload->>'total','')::integer; exception when others then v_total := null; end; end if;
    exit when jsonb_array_length(v_offers)=0;

    for v_offer in select value from jsonb_array_elements(v_offers) loop
      v_seen := v_seen + 1;
      if coalesce((v_offer #>> '{product,subCategory,category,id}')::integer,0) not in (10000,10022) then continue; end if;
      if coalesce((v_offer->>'isShopping')::boolean,false) then continue; end if;
      if coalesce((v_offer->>'shoppingOfferType')::boolean,false) then continue; end if;
      if coalesce((v_offer->>'offerTypeId')::integer,0) <> 1 then continue; end if;

      v_vehicle := v_vehicle + 1; v_external_id := v_offer->>'id'; v_url := 'https://www.superbid.com.co/oferta/x-' || v_external_id;
      v_close_text := v_offer->>'endDate'; v_close_at := public.superbid_offer_close_at(v_offer); v_outcome := public.superbid_offer_outcome(v_offer);
      v_priority := case when v_close_at is null then 100 when v_close_at <= clock_timestamp()+interval '15 minutes' then 1000
        when v_close_at <= clock_timestamp()+interval '2 hours' then 500 when v_close_at <= clock_timestamp()+interval '24 hours' then 200 else 100 end;
      v_lot_id := public.superbid_upsert_offer(v_offer,'superbid_public_http_discovery',false); v_saved := v_saved + 1;

      insert into public.collection_queue(external_lot_id,url,status,next_run_at,last_run_at,last_success_at,consecutive_errors,last_error,closes_at_text,closes_at,priority,created_at,updated_at)
      values(v_external_id,v_url,case when v_outcome in ('SOLD_CONFIRMED','WITHDRAWN') then 'DONE' else 'WATCH' end,clock_timestamp(),null,null,0,null,v_close_text,v_close_at,v_priority,clock_timestamp(),clock_timestamp())
      on conflict(external_lot_id) do update set url=excluded.url,closes_at_text=coalesce(excluded.closes_at_text,public.collection_queue.closes_at_text),
        closes_at=coalesce(excluded.closes_at,public.collection_queue.closes_at),priority=excluded.priority,
        status=case when public.collection_queue.status='DONE' then 'DONE' when excluded.status='DONE' then 'DONE' else 'WATCH' end,updated_at=clock_timestamp();
      v_queued := v_queued + 1;
    end loop;
    exit when v_total is not null and v_page*p_page_size >= v_total;
  end loop;

  update public.collection_runs set finished_at=clock_timestamp(),ok=true,lots_found=v_vehicle,lots_saved=v_saved where id=v_run_id;
  return jsonb_build_object('ok',true,'pages_scanned',v_pages,'total_reported',v_total,'offers_seen',v_seen,'vehicle_lots_seen',v_vehicle,'saved',v_saved,'queued',v_queued,'categories',jsonb_build_array(10000,10022));
exception when others then
  if v_run_id is not null then update public.collection_runs set finished_at=clock_timestamp(),ok=false,error=sqlerrm where id=v_run_id; end if;
  raise;
end
$$;

create or replace function public.superbid_refresh_due(p_limit integer default 40)
returns jsonb
language plpgsql
security definer
set search_path = public, extensions, pg_catalog
as $$
declare
  v_q record; v_uri text; v_resp record; v_payload jsonb; v_offer jsonb; v_outcome text; v_close_at timestamptz;
  v_close_text text; v_processed integer := 0; v_ok integer := 0; v_errors integer := 0; v_run_id bigint; v_new_errors integer;
begin
  p_limit := greatest(1, least(coalesce(p_limit,40),100));
  insert into public.collection_runs(run_type,target,started_at,lots_found,lots_saved,attachments_saved,bids_saved)
  values('CRON_REFRESH_BATCH','https://offer-query.superbid.net/seo/offers/',clock_timestamp(),0,0,0,0) returning id into v_run_id;

  for v_q in select * from public.collection_queue where status='WATCH' and next_run_at <= clock_timestamp()
    order by priority desc,next_run_at asc limit p_limit for update skip locked loop
    v_processed := v_processed + 1;
    begin
      v_uri := 'https://offer-query.superbid.net/seo/offers/?' || extensions.urlencode(jsonb_build_object(
        'portalId','[17]','locale','es_CO','timeZoneId','UTC','requestOrigin','marketplace','urlSeo',v_q.url));
      select * into v_resp from extensions.http_get(v_uri::varchar);
      if v_resp.status <> 200 then raise exception 'Superbid refresh HTTP status % for lot %',v_resp.status,v_q.external_lot_id; end if;
      v_payload := v_resp.content::jsonb;
      if jsonb_array_length(coalesce(v_payload->'offers','[]'::jsonb)) < 1 then raise exception 'Superbid refresh returned no offer for lot %',v_q.external_lot_id; end if;
      v_offer := v_payload->'offers'->0;
      if coalesce(v_offer->>'id','') <> v_q.external_lot_id then raise exception 'Superbid refresh lot mismatch: expected %, got %',v_q.external_lot_id,coalesce(v_offer->>'id','NULL'); end if;
      perform public.superbid_upsert_offer(v_offer,'superbid_public_http_refresh',true);
      v_outcome := public.superbid_offer_outcome(v_offer); v_close_at := public.superbid_offer_close_at(v_offer); v_close_text := v_offer->>'endDate';
      update public.collection_queue set
        status=case when v_outcome in ('SOLD_CONFIRMED','WITHDRAWN') then 'DONE'
          when v_close_at is not null and clock_timestamp()>v_close_at+interval '30 days' and v_outcome not in ('ACTIVE') then 'PAUSED' else 'WATCH' end,
        next_run_at=public.superbid_next_run_at(v_close_at,v_outcome,0),last_run_at=clock_timestamp(),last_success_at=clock_timestamp(),
        consecutive_errors=0,last_error=null,closes_at_text=coalesce(v_close_text,closes_at_text),closes_at=coalesce(v_close_at,closes_at),
        priority=case when v_close_at is null then 100 when v_close_at<=clock_timestamp()+interval '15 minutes' then 1000
          when v_close_at<=clock_timestamp()+interval '2 hours' then 500 when v_close_at<=clock_timestamp()+interval '24 hours' then 200 else 100 end,
        updated_at=clock_timestamp() where id=v_q.id;
      v_ok := v_ok + 1;
    exception when others then
      v_errors := v_errors + 1; v_new_errors := coalesce(v_q.consecutive_errors,0)+1;
      update public.collection_queue set last_run_at=clock_timestamp(),consecutive_errors=v_new_errors,last_error=left(sqlerrm,1000),
        next_run_at=public.superbid_next_run_at(closes_at,'UNKNOWN',v_new_errors),status=case when v_new_errors>=12 then 'PAUSED' else status end,
        updated_at=clock_timestamp() where id=v_q.id;
    end;
  end loop;

  update public.collection_runs set finished_at=clock_timestamp(),ok=(v_errors=0),lots_found=v_processed,lots_saved=v_ok,
    error=case when v_errors>0 then v_errors::text||' lot refresh error(s)' else null end where id=v_run_id;
  return jsonb_build_object('ok',v_errors=0,'processed',v_processed,'success',v_ok,'errors',v_errors);
end
$$;

revoke all on function public.superbid_upsert_offer(jsonb,text,boolean) from public, anon, authenticated;
revoke all on function public.superbid_discover_open_vehicles(integer,integer) from public, anon, authenticated;
revoke all on function public.superbid_refresh_due(integer) from public, anon, authenticated;
grant execute on function public.superbid_upsert_offer(jsonb,text,boolean) to service_role;
grant execute on function public.superbid_discover_open_vehicles(integer,integer) to service_role;
grant execute on function public.superbid_refresh_due(integer) to service_role;
