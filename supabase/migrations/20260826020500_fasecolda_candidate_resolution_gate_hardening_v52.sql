-- SUPERBID v0.52 · defense-in-depth for candidate evidence gate
-- The primary v0.52 RPC validates evidence before REVIEWED. This replacement
-- trigger independently revalidates the reviewed snapshot before any manual
-- resolution INSERT/UPDATE, so a malformed direct service-role evidence write
-- cannot be used as a shortcut to MANUAL_CONFIRMED/HIGH.

create or replace function public.enforce_fasecolda_candidate_evidence_gate_v52()
returns trigger
language plpgsql
security definer
set search_path=public,pg_catalog
as $$
declare
  e public.lot_fasecolda_candidate_resolution_evidence%rowtype;
  l public.auction_lots%rowtype;
  c public.lot_fasecolda_candidates%rowtype;
  a public.lot_fasecolda_matches%rowtype;
  v_required text[]:=array['line_identity','engine_cc','transmission','fuel','drivetrain','trim_body_use'];
  v_dim text;
  v_status text;
  v_note text;
  v_observed text;
  v_source text;
  v_match_count smallint:=0;
  v_not_stated_count smallint:=0;
  v_discriminating_count smallint:=0;
begin
  select * into e
  from public.lot_fasecolda_candidate_resolution_evidence
  where lot_id=new.lot_id and reviewed_at is not null;

  if e.id is null then
    raise exception 'v0.52 reviewed candidate evidence is required before manual Fasecolda confirmation';
  end if;

  select * into l from public.auction_lots where id=new.lot_id;
  if l.id is null then raise exception 'v0.52 evidence gate lot not found'; end if;

  if e.external_lot_id is distinct from l.external_lot_id then
    raise exception 'v0.52 reviewed evidence external lot identity is stale';
  end if;

  if jsonb_typeof(e.dimensions)<>'object' then
    raise exception 'v0.52 reviewed evidence dimensions must be an object';
  end if;

  foreach v_dim in array v_required loop
    if not (e.dimensions ? v_dim) or jsonb_typeof(e.dimensions->v_dim)<>'object' then
      raise exception 'v0.52 reviewed evidence missing or invalid dimension %',v_dim;
    end if;

    v_status:=upper(trim(coalesce(e.dimensions->v_dim->>'status','')));
    v_note:=nullif(trim(coalesce(e.dimensions->v_dim->>'evidence_note','')),'');
    v_observed:=nullif(trim(coalesce(e.dimensions->v_dim->>'observed_value','')),'');
    v_source:=nullif(trim(coalesce(e.dimensions->v_dim->>'source_url','')),'');

    if v_status not in ('MATCH','NOT_STATED') then
      raise exception 'v0.52 reviewed evidence contains unresolved status for dimension %',v_dim;
    end if;
    if v_note is null or char_length(v_note)<10 then
      raise exception 'v0.52 reviewed evidence note is incomplete for dimension %',v_dim;
    end if;
    if v_status='MATCH' and v_observed is null then
      raise exception 'v0.52 reviewed MATCH requires observed value for dimension %',v_dim;
    end if;
    if v_source is null or v_source !~* '^https?://' then
      raise exception 'v0.52 reviewed evidence requires trusted http(s) source for dimension %',v_dim;
    end if;
    if v_source is distinct from l.url
       and not exists(
         select 1 from public.lot_attachments x
         where x.lot_id=l.id and x.url=v_source
       ) then
      raise exception 'v0.52 reviewed evidence source is not registered for lot dimension %',v_dim;
    end if;

    if v_dim='line_identity' and v_status<>'MATCH' then
      raise exception 'v0.52 reviewed evidence requires line identity MATCH';
    end if;

    if v_status='MATCH' then
      v_match_count:=v_match_count+1;
      if v_dim<>'line_identity'
         and lower(coalesce(e.dimensions->v_dim->>'discriminating','false'))='true' then
        if char_length(v_note)<20 then
          raise exception 'v0.52 discriminating MATCH note is incomplete for dimension %',v_dim;
        end if;
        v_discriminating_count:=v_discriminating_count+1;
      end if;
    else
      if lower(coalesce(e.dimensions->v_dim->>'discriminating','false'))='true' then
        raise exception 'v0.52 only MATCH dimensions may be discriminating';
      end if;
      v_not_stated_count:=v_not_stated_count+1;
    end if;
  end loop;

  if lower(coalesce(e.dimensions->'line_identity'->>'discriminating','false'))='true' then
    raise exception 'v0.52 line identity cannot be the discriminating dimension';
  end if;

  if v_discriminating_count<1 then
    raise exception 'v0.52 reviewed evidence requires an explicit non-line discriminating MATCH';
  end if;
  if e.summary_note is null or char_length(trim(e.summary_note))<20 then
    raise exception 'v0.52 reviewed evidence summary is incomplete';
  end if;

  if e.evidence_complete_count<>6
     or e.conflict_count<>0
     or e.match_count<>v_match_count
     or e.not_stated_count<>v_not_stated_count
     or e.discriminating_match_count<>v_discriminating_count then
    raise exception 'v0.52 reviewed evidence counters do not match dimensions';
  end if;

  select * into c
  from public.lot_fasecolda_candidates
  where lot_id=l.id and code=e.chosen_code
  limit 1;

  if c.lot_id is null then
    raise exception 'v0.52 reviewed evidence candidate is no longer current';
  end if;
  if c.model_year is distinct from l.model_year then
    raise exception 'v0.52 reviewed evidence candidate year no longer matches lot';
  end if;
  if c.description is null or trim(c.description)='' then
    raise exception 'v0.52 reviewed evidence candidate has no usable description';
  end if;
  if c.current_value_cop is null or c.current_value_cop<=0 then
    raise exception 'v0.52 reviewed evidence candidate has no usable value';
  end if;
  if not exists(select 1 from public.fasecolda_references r where r.code=c.code) then
    raise exception 'v0.52 reviewed evidence candidate reference no longer exists';
  end if;
  if not public.fasecolda_line_compatible(l.title,l.brand,c.description) then
    raise exception 'v0.52 reviewed evidence candidate fails identity guard';
  end if;
  if exists(
    select 1 from public.lot_fasecolda_candidates other
    where other.lot_id=l.id
      and other.code<>c.code
      and other.model_year is not distinct from c.model_year
      and regexp_replace(upper(trim(other.description)),'[[:space:]]+',' ','g')=
          regexp_replace(upper(trim(c.description)),'[[:space:]]+',' ','g')
  ) then
    raise exception 'v0.52 reviewed evidence candidate is not uniquely distinguishable';
  end if;

  select * into a from public.lot_fasecolda_matches where lot_id=l.id;
  if a.lot_id is null then raise exception 'v0.52 automatic Fasecolda match not found'; end if;
  if tg_op='INSERT' and a.status not in ('AMBIGUOUS','MEDIUM') then
    raise exception 'v0.52 new manual resolution requires AMBIGUOUS or MEDIUM automatic status';
  end if;

  if new.external_lot_id is distinct from e.external_lot_id
     or new.chosen_code is distinct from e.chosen_code
     or new.model_year is distinct from c.model_year
     or new.chosen_description is distinct from c.description
     or new.chosen_description is distinct from e.chosen_description
     or new.chosen_value_cop is distinct from c.current_value_cop
     or new.chosen_value_cop is distinct from e.chosen_value_cop
     or new.candidate_score is distinct from c.score
     or new.candidate_score is distinct from e.candidate_score
     or new.candidate_rank is distinct from c.rank_no
     or new.candidate_rank is distinct from e.candidate_rank
     or new.source_evaluated_at is distinct from c.evaluated_at
     or new.source_evaluated_at is distinct from e.source_evaluated_at then
    raise exception 'manual Fasecolda resolution must match current v0.52 reviewed evidence and candidate snapshot';
  end if;

  return new;
end;
$$;

revoke all on function public.enforce_fasecolda_candidate_evidence_gate_v52() from public,anon,authenticated;
