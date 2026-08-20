create or replace function public.fasecolda_line_compatible(p_title text,p_brand text,p_candidate text)
returns boolean
language plpgsql
immutable
set search_path=public,extensions,pg_catalog
as $$
declare
  t text:=public.vehicle_norm(split_part(coalesce(p_title,''),' MOD',1));
  b text:=public.vehicle_norm(coalesce(p_brand,''));
  c text:=public.vehicle_norm(coalesce(p_candidate,''));
  rest text; a text[]; model1 text; model2 text; actual_brand text;
begin
  if t='' or c='' then return false; end if;
  if b<>'' and b not in ('VOLQUETA','CAMION','CAMIONETA','TRACTOCAMION','TRACTOMULA','BUS','MICROBUS','VEHICULO') and (t=b or t like b||' %') then
    actual_brand:=b; rest:=trim(substr(t,length(b)+1));
  else
    a:=regexp_split_to_array(t,'\s+');
    if cardinality(a)=0 then return false; end if;
    if a[1]=any(array['VOLQUETA','CAMION','CAMIONETA','TRACTOCAMION','TRACTOMULA','BUS','MICROBUS','VEHICULO']) then
      if cardinality(a)<3 then return false; end if;
      actual_brand:=a[2]; rest:=array_to_string(a[3:cardinality(a)],' ');
    else
      actual_brand:=a[1]; rest:=case when cardinality(a)>=2 then array_to_string(a[2:cardinality(a)],' ') else '' end;
    end if;
  end if;
  if actual_brand is null or actual_brand='' or rest='' then return false; end if;
  if c !~ ('(^| )'||actual_brand||'( |$)') then return false; end if;
  a:=regexp_split_to_array(rest,'\s+');
  if cardinality(a)=0 then return false; end if;
  if a[1]='NEW' and cardinality(a)>=2 then a:=a[2:cardinality(a)]; end if;
  model1:=a[1];
  if model1 is null or model1='' then return false; end if;
  if c !~ ('(^| )'||model1||'( |$)') then return false; end if;
  if model1~'^[A-Z]$' and cardinality(a)>=2 then
    model2:=a[2];
    if model2 is not null and model2<>'' and c !~ ('(^| )'||model2||'( |$)') then return false; end if;
  end if;
  return true;
end
$$;

create or replace function public.fasecolda_candidate_identity_guard()
returns trigger
language plpgsql
security definer
set search_path=public,extensions,pg_catalog
as $$
declare l record;
begin
  select title,brand into l from public.auction_lots where id=new.lot_id;
  if not found then return null; end if;
  if not public.fasecolda_line_compatible(l.title,l.brand,new.description) then return null; end if;
  return new;
end
$$;

drop trigger if exists trg_fasecolda_candidate_identity_guard on public.lot_fasecolda_candidates;
create trigger trg_fasecolda_candidate_identity_guard
before insert or update of description on public.lot_fasecolda_candidates
for each row execute function public.fasecolda_candidate_identity_guard();

revoke all on function public.fasecolda_line_compatible(text,text,text),public.fasecolda_candidate_identity_guard() from public,anon,authenticated;
grant execute on function public.fasecolda_line_compatible(text,text,text) to service_role;

delete from public.lot_fasecolda_candidates c
using public.auction_lots l
where l.id=c.lot_id and not public.fasecolda_line_compatible(l.title,l.brand,c.description);

update public.fasecolda_match_queue q
set status='PENDING',next_run_at=clock_timestamp(),updated_at=clock_timestamp(),last_error=null
where exists(select 1 from public.lot_fasecolda_matches m where m.lot_id=q.lot_id);
