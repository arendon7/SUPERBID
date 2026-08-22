create or replace function public.dashboard_probe_fasecolda_search_term(
  p_external_lot_id text,
  p_term text
) returns jsonb
language plpgsql
security definer
set search_path to 'public','extensions','pg_catalog'
as $function$
declare
  v_lot public.auction_lots%rowtype;
  v_term text;
  v_brand text;
  v_resp record;
  v_json jsonb;
  v_codes jsonb := '[]'::jsonb;
  v_count integer := 0;
  v_current text;
  v_suggested text;
begin
  if p_external_lot_id is null or p_external_lot_id !~ '^\d{5,12}$' then
    raise exception 'invalid external lot id';
  end if;

  select * into v_lot
  from public.auction_lots
  where external_lot_id=p_external_lot_id
  order by id desc limit 1;
  if not found then raise exception 'lot not found'; end if;

  v_term := trim(public.vehicle_norm(coalesce(p_term,'')));
  if char_length(v_term)<2 or char_length(v_term)>80 then
    raise exception 'invalid search term length';
  end if;

  v_brand := nullif(trim(public.vehicle_norm(coalesce(v_lot.brand,''))), '');
  if v_brand is not null and not (v_term=v_brand or v_term like v_brand||' %') then
    raise exception 'search term must preserve vehicle brand';
  end if;

  select fm.search_term into v_current
  from public.lot_fasecolda_matches fm
  where fm.lot_id=v_lot.id;
  v_suggested := public.fasecolda_suggest_search_term(v_lot.title);

  select * into v_resp
  from extensions.http_get(
    ('https://fasecoldaback.quantil.co/api/busqueda/'||extensions.urlencode(v_term))::varchar
  );

  if v_resp.status not in (200,404) then
    raise exception 'Fasecolda search HTTP %',v_resp.status;
  end if;

  begin
    v_json := v_resp.content::jsonb;
  exception when others then
    raise exception 'invalid Fasecolda search response';
  end;

  if jsonb_typeof(v_json->'codigos')='array' then
    select coalesce(jsonb_agg(value order by ord),'[]'::jsonb), count(*)::integer
    into v_codes,v_count
    from jsonb_array_elements(v_json->'codigos') with ordinality x(value,ord)
    where ord<=22;
  end if;

  return jsonb_build_object(
    'ok',true,
    'external_lot_id',v_lot.external_lot_id,
    'term',v_term,
    'current_search_term',v_current,
    'suggested_search_term',v_suggested,
    'http_status',v_resp.status,
    'code_count',v_count,
    'has_codes',v_count>0,
    'codes',v_codes,
    'interpretation','FASECOLDA_SEARCH_PROBE_NOT_MATCH'
  );
end;
$function$;

revoke all on function public.dashboard_probe_fasecolda_search_term(text,text) from public,anon,authenticated;
grant execute on function public.dashboard_probe_fasecolda_search_term(text,text) to service_role;
