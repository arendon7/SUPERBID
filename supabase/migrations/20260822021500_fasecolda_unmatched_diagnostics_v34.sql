create or replace function public.fasecolda_suggest_search_term(p_title text)
returns text
language plpgsql
immutable
set search_path to 'public','extensions','pg_catalog'
as $function$
declare
  v text;
  a text[];
  out_words text[] := '{}';
  w text;
  model_words integer := 0;
  max_model_words integer := 2;
begin
  v := regexp_replace(coalesce(p_title,''),'\[[^\]]+\]','','g');
  v := public.vehicle_norm(split_part(v,' MOD',1));
  a := regexp_split_to_array(v,'\s+');

  foreach w in array a loop
    if w is null or w='' then continue; end if;
    if w = any(array['VOLQUETA','CAMION','CAMIONETA','TRACTOCAMION','TRACTOMULA','BUS','MICROBUS','VEHICULO']) and cardinality(out_words)=0 then
      continue;
    end if;
    if cardinality(out_words)>0 and w = any(array['CC','MT','AT','TP','TD','ABS','4X2','4X4','RWD','AWD','MEC','AUT','AUTOMATICO','MECANICO','PLACA','RP','UBIC']) then
      exit;
    end if;
    if cardinality(out_words)>0 and w ~ '^[0-9]{3,4}$' then
      exit;
    end if;

    out_words := array_append(out_words,w);
    if cardinality(out_words)=2 and w='NEW' then
      max_model_words := 3;
    end if;
    if cardinality(out_words)>=2 then
      model_words := cardinality(out_words)-1;
      if model_words>=max_model_words then exit; end if;
    end if;
  end loop;

  if cardinality(out_words)<2 then return null; end if;
  return array_to_string(out_words,' ');
end;
$function$;

revoke all on function public.fasecolda_suggest_search_term(text) from public,anon,authenticated;
grant execute on function public.fasecolda_suggest_search_term(text) to service_role;

create or replace view public.dashboard_fasecolda_unmatched_diagnostics as
select
  l.external_lot_id,
  l.id as lot_id,
  l.title,
  l.brand,
  l.line,
  l.model_year,
  l.city,
  l.seller,
  r.review_state,
  r.review_score,
  coalesce(e.status,'NO_MATCH_ROW') as effective_status,
  e.automatic_status,
  e.search_term as current_search_term,
  public.fasecolda_suggest_search_term(l.title) as suggested_search_term,
  (public.fasecolda_suggest_search_term(l.title) is not null
    and public.fasecolda_suggest_search_term(l.title) is distinct from e.search_term) as suggestion_differs,
  coalesce(e.candidate_count,0) as candidate_count,
  e.note as matcher_note,
  case
    when e.lot_id is null then 'NO_MATCH_ROW'
    when e.status='UNMATCHED'
      and public.fasecolda_suggest_search_term(l.title) is not null
      and public.fasecolda_suggest_search_term(l.title) is distinct from e.search_term
      then 'SEARCH_TERM_CAN_BE_EXPANDED'
    when e.status='UNMATCHED' and coalesce(e.note,'') ilike '%model year%'
      then 'NO_YEAR_COMPATIBLE_REFERENCE'
    when e.status='UNMATCHED' and coalesce(e.note,'') ilike '%no codes%'
      then 'PUBLIC_SEARCH_RETURNED_NO_CODES'
    else 'UNMATCHED_OTHER'
  end as diagnostic_reason,
  case
    when e.status='UNMATCHED'
      and public.fasecolda_suggest_search_term(l.title) is not null
      and public.fasecolda_suggest_search_term(l.title) is distinct from e.search_term then 10
    when e.lot_id is null then 20
    when e.status='UNMATCHED' and coalesce(e.note,'') ilike '%no codes%' then 30
    when e.status='UNMATCHED' and coalesce(e.note,'') ilike '%model year%' then 40
    else 50
  end as diagnostic_rank,
  'FASECOLDA_UNMATCHED_DIAGNOSTIC_NOT_MATCH'::text as interpretation
from public.auction_lots l
join public.dashboard_economic_readiness_current r on r.lot_id=l.id
left join public.lot_fasecolda_effective_current e on e.lot_id=l.id
where r.next_action='REVIEW_VALUATION'
  and coalesce(e.status,'NO_MATCH_ROW') in ('UNMATCHED','NO_MATCH_ROW');

revoke all on public.dashboard_fasecolda_unmatched_diagnostics from public,anon,authenticated;
grant select on public.dashboard_fasecolda_unmatched_diagnostics to service_role;
