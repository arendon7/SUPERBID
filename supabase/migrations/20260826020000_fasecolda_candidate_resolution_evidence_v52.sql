-- SUPERBID v0.52 · Fasecolda Candidate Resolution Evidence Gate
-- Manual confirmation may elevate the effective Fasecolda provenance to HIGH,
-- therefore exact-code confirmation requires structured, source-bound human evidence.
-- This migration does not create an automatic match or a buy signal.

create table if not exists public.lot_fasecolda_candidate_resolution_evidence(
  id bigint generated always as identity primary key,
  lot_id bigint not null unique references public.auction_lots(id) on delete cascade,
  external_lot_id text not null,
  chosen_code text not null references public.fasecolda_references(code),
  chosen_description text not null,
  chosen_value_cop bigint not null check(chosen_value_cop>0),
  candidate_score numeric,
  candidate_rank integer,
  source_evaluated_at timestamptz,
  dimensions jsonb not null default '{}'::jsonb,
  source_urls jsonb not null default '[]'::jsonb,
  evidence_complete_count smallint not null default 0,
  match_count smallint not null default 0,
  conflict_count smallint not null default 0,
  not_stated_count smallint not null default 0,
  discriminating_match_count smallint not null default 0,
  summary_note text,
  reviewed_at timestamptz,
  created_at timestamptz not null default clock_timestamp(),
  updated_at timestamptz not null default clock_timestamp(),
  interpretation text not null default 'MANUAL_FASECOLDA_CANDIDATE_EVIDENCE_NOT_AUTOMATIC_MATCH_OR_BUY_SIGNAL',
  constraint fasecolda_candidate_evidence_dimensions_object check(jsonb_typeof(dimensions)='object'),
  constraint fasecolda_candidate_evidence_sources_array check(jsonb_typeof(source_urls)='array'),
  constraint fasecolda_candidate_evidence_complete_range check(evidence_complete_count between 0 and 6),
  constraint fasecolda_candidate_evidence_match_range check(match_count between 0 and 6),
  constraint fasecolda_candidate_evidence_conflict_range check(conflict_count between 0 and 6),
  constraint fasecolda_candidate_evidence_not_stated_range check(not_stated_count between 0 and 6),
  constraint fasecolda_candidate_evidence_discriminating_range check(discriminating_match_count between 0 and 5),
  constraint fasecolda_candidate_evidence_summary_len check(summary_note is null or char_length(summary_note)<=2000),
  constraint fasecolda_candidate_evidence_interpretation_guard check(interpretation='MANUAL_FASECOLDA_CANDIDATE_EVIDENCE_NOT_AUTOMATIC_MATCH_OR_BUY_SIGNAL')
);

create table if not exists public.lot_fasecolda_candidate_resolution_evidence_history(
  id bigint generated always as identity primary key,
  lot_id bigint not null references public.auction_lots(id) on delete cascade,
  external_lot_id text not null,
  action text not null check(action in ('DRAFT','CONFIRM','MANUAL_REMOVAL_INVALIDATED','IDENTITY_CHANGE_INVALIDATED')),
  chosen_code text,
  chosen_description text,
  chosen_value_cop bigint,
  candidate_score numeric,
  candidate_rank integer,
  source_evaluated_at timestamptz,
  dimensions jsonb not null default '{}'::jsonb,
  source_urls jsonb not null default '[]'::jsonb,
  evidence_complete_count smallint not null default 0,
  match_count smallint not null default 0,
  conflict_count smallint not null default 0,
  not_stated_count smallint not null default 0,
  discriminating_match_count smallint not null default 0,
  summary_note text,
  created_at timestamptz not null default clock_timestamp(),
  interpretation text not null default 'MANUAL_FASECOLDA_CANDIDATE_EVIDENCE_NOT_AUTOMATIC_MATCH_OR_BUY_SIGNAL',
  constraint fasecolda_candidate_evidence_history_dimensions_object check(jsonb_typeof(dimensions)='object'),
  constraint fasecolda_candidate_evidence_history_sources_array check(jsonb_typeof(source_urls)='array'),
  constraint fasecolda_candidate_evidence_history_complete_range check(evidence_complete_count between 0 and 6),
  constraint fasecolda_candidate_evidence_history_match_range check(match_count between 0 and 6),
  constraint fasecolda_candidate_evidence_history_conflict_range check(conflict_count between 0 and 6),
  constraint fasecolda_candidate_evidence_history_not_stated_range check(not_stated_count between 0 and 6),
  constraint fasecolda_candidate_evidence_history_discriminating_range check(discriminating_match_count between 0 and 5),
  constraint fasecolda_candidate_evidence_history_summary_len check(summary_note is null or char_length(summary_note)<=2000),
  constraint fasecolda_candidate_evidence_history_interpretation_guard check(interpretation='MANUAL_FASECOLDA_CANDIDATE_EVIDENCE_NOT_AUTOMATIC_MATCH_OR_BUY_SIGNAL')
);

alter table public.lot_fasecolda_candidate_resolution_evidence enable row level security;
alter table public.lot_fasecolda_candidate_resolution_evidence_history enable row level security;
revoke all on public.lot_fasecolda_candidate_resolution_evidence,public.lot_fasecolda_candidate_resolution_evidence_history from public,anon,authenticated;
grant select,insert,update,delete on public.lot_fasecolda_candidate_resolution_evidence to service_role;
grant select,insert on public.lot_fasecolda_candidate_resolution_evidence_history to service_role;

create index if not exists ix_fasecolda_candidate_evidence_history_lot_created
  on public.lot_fasecolda_candidate_resolution_evidence_history(lot_id,created_at desc);

create or replace function public.enforce_fasecolda_candidate_evidence_gate_v52()
returns trigger
language plpgsql
security definer
set search_path=public,pg_catalog
as $$
declare
  e public.lot_fasecolda_candidate_resolution_evidence%rowtype;
begin
  select * into e
  from public.lot_fasecolda_candidate_resolution_evidence
  where lot_id=new.lot_id and reviewed_at is not null;

  if e.id is null then
    raise exception 'v0.52 reviewed candidate evidence is required before manual Fasecolda confirmation';
  end if;

  if new.external_lot_id is distinct from e.external_lot_id
     or new.chosen_code is distinct from e.chosen_code
     or new.chosen_description is distinct from e.chosen_description
     or new.chosen_value_cop is distinct from e.chosen_value_cop
     or new.candidate_score is distinct from e.candidate_score
     or new.candidate_rank is distinct from e.candidate_rank
     or new.source_evaluated_at is distinct from e.source_evaluated_at then
    raise exception 'manual Fasecolda resolution must match current v0.52 reviewed evidence snapshot';
  end if;

  return new;
end;
$$;

revoke all on function public.enforce_fasecolda_candidate_evidence_gate_v52() from public,anon,authenticated;

drop trigger if exists trg_fasecolda_candidate_evidence_gate_v52 on public.lot_fasecolda_manual_resolutions;
create trigger trg_fasecolda_candidate_evidence_gate_v52
before insert or update on public.lot_fasecolda_manual_resolutions
for each row execute function public.enforce_fasecolda_candidate_evidence_gate_v52();

create or replace function public.invalidate_fasecolda_candidate_evidence_after_manual_delete_v52()
returns trigger
language plpgsql
security definer
set search_path=public,pg_catalog
as $$
declare
  e public.lot_fasecolda_candidate_resolution_evidence%rowtype;
begin
  select * into e from public.lot_fasecolda_candidate_resolution_evidence where lot_id=old.lot_id;
  if e.id is null then return old; end if;

  insert into public.lot_fasecolda_candidate_resolution_evidence_history(
    lot_id,external_lot_id,action,chosen_code,chosen_description,chosen_value_cop,candidate_score,candidate_rank,
    source_evaluated_at,dimensions,source_urls,evidence_complete_count,match_count,conflict_count,not_stated_count,
    discriminating_match_count,summary_note
  ) values(
    e.lot_id,e.external_lot_id,'MANUAL_REMOVAL_INVALIDATED',e.chosen_code,e.chosen_description,e.chosen_value_cop,
    e.candidate_score,e.candidate_rank,e.source_evaluated_at,e.dimensions,e.source_urls,e.evidence_complete_count,
    e.match_count,e.conflict_count,e.not_stated_count,e.discriminating_match_count,e.summary_note
  );
  delete from public.lot_fasecolda_candidate_resolution_evidence where lot_id=old.lot_id;
  return old;
end;
$$;

revoke all on function public.invalidate_fasecolda_candidate_evidence_after_manual_delete_v52() from public,anon,authenticated;

drop trigger if exists trg_fasecolda_candidate_evidence_manual_delete_v52 on public.lot_fasecolda_manual_resolutions;
create trigger trg_fasecolda_candidate_evidence_manual_delete_v52
after delete on public.lot_fasecolda_manual_resolutions
for each row execute function public.invalidate_fasecolda_candidate_evidence_after_manual_delete_v52();

create or replace function public.invalidate_fasecolda_candidate_evidence_on_identity_change_v52()
returns trigger
language plpgsql
security definer
set search_path=public,pg_catalog
as $$
declare
  e public.lot_fasecolda_candidate_resolution_evidence%rowtype;
begin
  if old.title is not distinct from new.title
     and old.brand is not distinct from new.brand
     and old.line is not distinct from new.line
     and old.model_year is not distinct from new.model_year then
    return new;
  end if;

  select * into e from public.lot_fasecolda_candidate_resolution_evidence where lot_id=new.id;
  if e.id is null then return new; end if;

  insert into public.lot_fasecolda_candidate_resolution_evidence_history(
    lot_id,external_lot_id,action,chosen_code,chosen_description,chosen_value_cop,candidate_score,candidate_rank,
    source_evaluated_at,dimensions,source_urls,evidence_complete_count,match_count,conflict_count,not_stated_count,
    discriminating_match_count,summary_note
  ) values(
    e.lot_id,e.external_lot_id,'IDENTITY_CHANGE_INVALIDATED',e.chosen_code,e.chosen_description,e.chosen_value_cop,
    e.candidate_score,e.candidate_rank,e.source_evaluated_at,e.dimensions,e.source_urls,e.evidence_complete_count,
    e.match_count,e.conflict_count,e.not_stated_count,e.discriminating_match_count,e.summary_note
  );
  delete from public.lot_fasecolda_candidate_resolution_evidence where lot_id=new.id;
  return new;
end;
$$;

revoke all on function public.invalidate_fasecolda_candidate_evidence_on_identity_change_v52() from public,anon,authenticated;

drop trigger if exists trg_fasecolda_candidate_evidence_identity_change_v52 on public.auction_lots;
create trigger trg_fasecolda_candidate_evidence_identity_change_v52
after update of title,brand,line,model_year on public.auction_lots
for each row execute function public.invalidate_fasecolda_candidate_evidence_on_identity_change_v52();

create or replace function public.dashboard_save_fasecolda_candidate_resolution(
  p_external_lot_id text,
  p_code text,
  p_dimensions jsonb default '{}'::jsonb,
  p_summary_note text default null,
  p_mark_reviewed boolean default false
) returns jsonb
language plpgsql
security definer
set search_path=public,pg_catalog
as $$
declare
  v_lot public.auction_lots%rowtype;
  v_auto public.lot_fasecolda_matches%rowtype;
  v_candidate public.lot_fasecolda_candidates%rowtype;
  v_manual public.lot_fasecolda_manual_resolutions%rowtype;
  v_dimensions jsonb:=coalesce(p_dimensions,'{}'::jsonb);
  v_required text[]:=array['line_identity','engine_cc','transmission','fuel','drivetrain','trim_body_use'];
  v_allowed text[]:=array['MATCH','CONFLICT','NOT_STATED'];
  v_dim text;
  v_status text;
  v_note text;
  v_observed text;
  v_source text;
  v_complete smallint:=0;
  v_matches smallint:=0;
  v_conflicts smallint:=0;
  v_not_stated smallint:=0;
  v_discriminating smallint:=0;
  v_line_status text;
  v_source_urls jsonb:='[]'::jsonb;
  v_summary text:=nullif(trim(coalesce(p_summary_note,'')),'');
  v_reviewed_at timestamptz;
  v_resolution jsonb;
begin
  if p_external_lot_id is null or p_external_lot_id !~ '^[0-9]{5,12}$' then
    raise exception 'invalid external lot id';
  end if;
  if p_code is null or trim(p_code)='' then raise exception 'candidate code required'; end if;
  if jsonb_typeof(v_dimensions)<>'object' then raise exception 'dimensions must be a json object'; end if;
  if exists(select 1 from jsonb_object_keys(v_dimensions) as keys(k) where not (k=any(v_required))) then
    raise exception 'unknown candidate evidence dimension';
  end if;
  if v_summary is not null and char_length(v_summary)>2000 then raise exception 'summary note too long'; end if;

  select * into v_lot from public.auction_lots
  where external_lot_id=p_external_lot_id order by id desc limit 1;
  if v_lot.id is null then raise exception 'lot not found'; end if;

  select * into v_auto from public.lot_fasecolda_matches where lot_id=v_lot.id;
  if v_auto.lot_id is null then raise exception 'automatic Fasecolda match not found'; end if;

  select * into v_manual from public.lot_fasecolda_manual_resolutions where lot_id=v_lot.id;
  if v_manual.lot_id is not null and not p_mark_reviewed then
    raise exception 'clear current manual Fasecolda resolution before saving draft evidence';
  end if;
  if v_auto.status not in ('AMBIGUOUS','MEDIUM') and v_manual.lot_id is null then
    raise exception 'candidate evidence confirmation is allowed only for AMBIGUOUS or MEDIUM automatic matches';
  end if;

  select * into v_candidate from public.lot_fasecolda_candidates
  where lot_id=v_lot.id and code=trim(p_code) limit 1;
  if v_candidate.lot_id is null then raise exception 'selected code is not a current candidate for this lot'; end if;
  if v_candidate.model_year is distinct from v_lot.model_year then raise exception 'candidate model year does not match lot'; end if;
  if v_candidate.current_value_cop is null or v_candidate.current_value_cop<=0 then raise exception 'candidate has no usable current value'; end if;
  if not exists(select 1 from public.fasecolda_references r where r.code=v_candidate.code) then raise exception 'candidate reference not found'; end if;
  if not public.fasecolda_line_compatible(v_lot.title,v_lot.brand,v_candidate.description) then raise exception 'candidate fails Fasecolda identity guard'; end if;

  foreach v_dim in array v_required loop
    if v_dimensions ? v_dim then
      if jsonb_typeof(v_dimensions->v_dim)<>'object' then raise exception 'dimension % must be an object',v_dim; end if;
      v_status:=nullif(upper(trim(coalesce(v_dimensions->v_dim->>'status',''))),'');
      v_note:=nullif(trim(coalesce(v_dimensions->v_dim->>'evidence_note','')),'');
      v_observed:=nullif(trim(coalesce(v_dimensions->v_dim->>'observed_value','')),'');
      v_source:=nullif(trim(coalesce(v_dimensions->v_dim->>'source_url','')),'');

      if v_status is not null and not(v_status=any(v_allowed)) then raise exception 'invalid evidence status for dimension %',v_dim; end if;
      if v_note is not null and char_length(v_note)>1000 then raise exception 'evidence note too long for dimension %',v_dim; end if;
      if v_observed is not null and char_length(v_observed)>500 then raise exception 'observed value too long for dimension %',v_dim; end if;
      if v_source is not null and char_length(v_source)>2000 then raise exception 'source url too long for dimension %',v_dim; end if;
      if v_source is not null and v_source is distinct from v_lot.url and not exists(
        select 1 from public.lot_attachments a where a.lot_id=v_lot.id and a.url=v_source
      ) then raise exception 'evidence source does not belong to lot for dimension %',v_dim; end if;

      if v_status is not null and v_note is not null and char_length(v_note)>=10 and v_source is not null
         and (v_status='NOT_STATED' or v_observed is not null) then
        v_complete:=v_complete+1;
      end if;
      if v_status='MATCH' then
        v_matches:=v_matches+1;
        if v_dim<>'line_identity' then v_discriminating:=v_discriminating+1; end if;
      elsif v_status='CONFLICT' then v_conflicts:=v_conflicts+1;
      elsif v_status='NOT_STATED' then v_not_stated:=v_not_stated+1;
      end if;
      if v_dim='line_identity' then v_line_status:=v_status; end if;

      if p_mark_reviewed then
        if v_status is null or v_note is null or char_length(v_note)<10 or v_source is null then
          raise exception 'reviewed candidate evidence requires status, source and note >=10 chars for dimension %',v_dim;
        end if;
        if v_status in ('MATCH','CONFLICT') and v_observed is null then
          raise exception 'reviewed candidate evidence requires observed value for assessed dimension %',v_dim;
        end if;
      end if;
    elsif p_mark_reviewed then
      raise exception 'reviewed candidate evidence missing dimension %',v_dim;
    end if;
  end loop;

  select coalesce(jsonb_agg(s order by s),'[]'::jsonb) into v_source_urls
  from (
    select distinct nullif(trim(value->>'source_url'),'') as s
    from jsonb_each(v_dimensions)
    where nullif(trim(value->>'source_url'),'') is not null
  ) q;

  if p_mark_reviewed then
    if v_complete<>6 then raise exception 'reviewed candidate evidence requires all six dimensions complete'; end if;
    if v_line_status is distinct from 'MATCH' then raise exception 'reviewed candidate evidence requires line identity MATCH'; end if;
    if v_conflicts>0 then raise exception 'reviewed candidate evidence cannot contain CONFLICT'; end if;
    if v_discriminating<1 then raise exception 'reviewed candidate evidence requires at least one discriminating MATCH beyond line identity'; end if;
    if v_summary is null or char_length(v_summary)<20 then raise exception 'reviewed candidate evidence requires summary note of at least 20 characters'; end if;
    if exists(
      select 1 from public.lot_fasecolda_candidates c
      where c.lot_id=v_lot.id
        and c.code<>v_candidate.code
        and c.model_year is not distinct from v_candidate.model_year
        and regexp_replace(upper(trim(c.description)),'\s+',' ','g')=regexp_replace(upper(trim(v_candidate.description)),'\s+',' ','g')
    ) then raise exception 'candidate is not uniquely distinguishable from another current candidate'; end if;
  end if;

  v_reviewed_at:=case when p_mark_reviewed then clock_timestamp() else null end;

  insert into public.lot_fasecolda_candidate_resolution_evidence(
    lot_id,external_lot_id,chosen_code,chosen_description,chosen_value_cop,candidate_score,candidate_rank,
    source_evaluated_at,dimensions,source_urls,evidence_complete_count,match_count,conflict_count,not_stated_count,
    discriminating_match_count,summary_note,reviewed_at,updated_at
  ) values(
    v_lot.id,v_lot.external_lot_id,v_candidate.code,v_candidate.description,v_candidate.current_value_cop,
    v_candidate.score,v_candidate.rank_no,v_candidate.evaluated_at,v_dimensions,v_source_urls,v_complete,v_matches,
    v_conflicts,v_not_stated,v_discriminating,v_summary,v_reviewed_at,clock_timestamp()
  ) on conflict(lot_id) do update set
    external_lot_id=excluded.external_lot_id,
    chosen_code=excluded.chosen_code,
    chosen_description=excluded.chosen_description,
    chosen_value_cop=excluded.chosen_value_cop,
    candidate_score=excluded.candidate_score,
    candidate_rank=excluded.candidate_rank,
    source_evaluated_at=excluded.source_evaluated_at,
    dimensions=excluded.dimensions,
    source_urls=excluded.source_urls,
    evidence_complete_count=excluded.evidence_complete_count,
    match_count=excluded.match_count,
    conflict_count=excluded.conflict_count,
    not_stated_count=excluded.not_stated_count,
    discriminating_match_count=excluded.discriminating_match_count,
    summary_note=excluded.summary_note,
    reviewed_at=excluded.reviewed_at,
    updated_at=clock_timestamp();

  insert into public.lot_fasecolda_candidate_resolution_evidence_history(
    lot_id,external_lot_id,action,chosen_code,chosen_description,chosen_value_cop,candidate_score,candidate_rank,
    source_evaluated_at,dimensions,source_urls,evidence_complete_count,match_count,conflict_count,not_stated_count,
    discriminating_match_count,summary_note
  ) values(
    v_lot.id,v_lot.external_lot_id,case when p_mark_reviewed then 'CONFIRM' else 'DRAFT' end,
    v_candidate.code,v_candidate.description,v_candidate.current_value_cop,v_candidate.score,v_candidate.rank_no,
    v_candidate.evaluated_at,v_dimensions,v_source_urls,v_complete,v_matches,v_conflicts,v_not_stated,v_discriminating,v_summary
  );

  if p_mark_reviewed then
    select public.dashboard_set_fasecolda_manual_resolution(
      v_lot.external_lot_id,'CONFIRM',v_candidate.code,v_summary
    ) into v_resolution;
    return v_resolution || jsonb_build_object(
      'candidate_evidence_reviewed',true,
      'evidence_complete_count',v_complete,
      'match_count',v_matches,
      'conflict_count',v_conflicts,
      'not_stated_count',v_not_stated,
      'discriminating_match_count',v_discriminating,
      'automatic_match_overwritten',false,
      'buy_signal',false,
      'economic_fields_modified',false,
      'interpretation','MANUAL_FASECOLDA_CANDIDATE_EVIDENCE_NOT_AUTOMATIC_MATCH_OR_BUY_SIGNAL'
    );
  end if;

  return jsonb_build_object(
    'ok',true,
    'external_lot_id',v_lot.external_lot_id,
    'action','DRAFT',
    'chosen_code',v_candidate.code,
    'candidate_evidence_reviewed',false,
    'evidence_complete_count',v_complete,
    'match_count',v_matches,
    'conflict_count',v_conflicts,
    'not_stated_count',v_not_stated,
    'discriminating_match_count',v_discriminating,
    'effective_status',v_auto.status,
    'match_origin','AUTOMATIC',
    'automatic_match_overwritten',false,
    'buy_signal',false,
    'economic_fields_modified',false,
    'interpretation','MANUAL_FASECOLDA_CANDIDATE_EVIDENCE_NOT_AUTOMATIC_MATCH_OR_BUY_SIGNAL'
  );
end;
$$;

revoke all on function public.dashboard_save_fasecolda_candidate_resolution(text,text,jsonb,text,boolean) from public,anon,authenticated;
grant execute on function public.dashboard_save_fasecolda_candidate_resolution(text,text,jsonb,text,boolean) to service_role;

create or replace view public.dashboard_fasecolda_candidate_resolution_cockpit_v52 as
select
  r.*,
  a.url as auction_url,
  coalesce(att.attachments,'[]'::jsonb) as attachments,
  w.workflow_target,
  w.triage_rank,
  w.triage_reason,
  w.readiness_status,
  w.readiness_next_action,
  w.hours_to_close,
  case when e.id is null then 'UNREVIEWED' when e.reviewed_at is null then 'DRAFT' else 'REVIEWED' end as evidence_status,
  e.chosen_code as evidence_chosen_code,
  e.chosen_description as evidence_chosen_description,
  e.chosen_value_cop as evidence_chosen_value_cop,
  e.candidate_score as evidence_candidate_score,
  e.candidate_rank as evidence_candidate_rank,
  e.source_evaluated_at as evidence_source_evaluated_at,
  e.dimensions as evidence_dimensions,
  e.source_urls as evidence_source_urls,
  coalesce(e.evidence_complete_count,0) as evidence_complete_count,
  coalesce(e.match_count,0) as evidence_match_count,
  coalesce(e.conflict_count,0) as evidence_conflict_count,
  coalesce(e.not_stated_count,0) as evidence_not_stated_count,
  coalesce(e.discriminating_match_count,0) as evidence_discriminating_match_count,
  e.summary_note as evidence_summary_note,
  e.reviewed_at as evidence_reviewed_at,
  e.updated_at as evidence_updated_at,
  'MANUAL_FASECOLDA_CANDIDATE_EVIDENCE_NOT_AUTOMATIC_MATCH_OR_BUY_SIGNAL'::text as evidence_interpretation
from public.dashboard_fasecolda_resolution_queue r
join public.auction_lots a using(lot_id)
left join public.dashboard_fasecolda_valuation_workbench w using(lot_id)
left join public.lot_fasecolda_candidate_resolution_evidence e using(lot_id)
left join lateral (
  select jsonb_agg(jsonb_build_object(
    'id',x.id,'name',x.name,'url',x.url,'kind',x.kind,'source',x.source,'discovered_at',x.discovered_at
  ) order by x.kind,x.id) as attachments
  from public.lot_attachments x where x.lot_id=r.lot_id
) att on true;

revoke all on public.dashboard_fasecolda_candidate_resolution_cockpit_v52 from public,anon,authenticated;
grant select on public.dashboard_fasecolda_candidate_resolution_cockpit_v52 to service_role;

comment on view public.dashboard_fasecolda_candidate_resolution_cockpit_v52 is
'v0.52 candidate-resolution cockpit. Exact-code manual HIGH requires six-dimension, trusted-source human evidence; DRAFT does not alter the effective Fasecolda match. Not a buy signal.';
