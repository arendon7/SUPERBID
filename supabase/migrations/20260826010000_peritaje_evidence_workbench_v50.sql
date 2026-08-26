-- SUPERBID v0.50 · Peritaje Evidence Workbench
-- A reviewed peritaje requires structured human evidence for all eight risk
-- dimensions plus an explicit repair-range basis. This is not automated diagnosis
-- and does not transfer any repair amount to lot costs.

create table if not exists public.lot_peritaje_evidence_reviews(
  id bigint generated always as identity primary key,
  lot_id bigint not null unique references public.auction_lots(id) on delete cascade,
  external_lot_id text not null,
  source_attachment_url text,
  dimensions jsonb not null default '{}'::jsonb,
  overall_risk text,
  evidence_completeness smallint not null default 0,
  not_evaluable_count smallint not null default 0,
  repair_low_cop numeric,
  repair_base_cop numeric,
  repair_high_cop numeric,
  repair_basis_note text,
  general_notes text,
  reviewed_at timestamptz,
  created_at timestamptz not null default clock_timestamp(),
  updated_at timestamptz not null default clock_timestamp(),
  interpretation text not null default 'MANUAL_PERITAJE_EVIDENCE_NOT_AUTOMATED_DIAGNOSIS_OR_BUY_SIGNAL',
  constraint lot_peritaje_evidence_dimensions_object check(jsonb_typeof(dimensions)='object'),
  constraint lot_peritaje_evidence_completeness_range check(evidence_completeness between 0 and 8),
  constraint lot_peritaje_evidence_not_evaluable_range check(not_evaluable_count between 0 and 8),
  constraint lot_peritaje_evidence_overall_allowed check(overall_risk is null or overall_risk in ('LOW','MEDIUM','HIGH','CRITICAL','NOT_EVALUABLE')),
  constraint lot_peritaje_evidence_repair_nonnegative check(coalesce(repair_low_cop,0)>=0 and coalesce(repair_base_cop,0)>=0 and coalesce(repair_high_cop,0)>=0),
  constraint lot_peritaje_evidence_repair_order check(repair_low_cop is null or repair_base_cop is null or repair_high_cop is null or (repair_low_cop<=repair_base_cop and repair_base_cop<=repair_high_cop)),
  constraint lot_peritaje_evidence_basis_len check(repair_basis_note is null or char_length(repair_basis_note)<=4000),
  constraint lot_peritaje_evidence_notes_len check(general_notes is null or char_length(general_notes)<=5000),
  constraint lot_peritaje_evidence_interpretation_guard check(interpretation='MANUAL_PERITAJE_EVIDENCE_NOT_AUTOMATED_DIAGNOSIS_OR_BUY_SIGNAL')
);

create table if not exists public.lot_peritaje_evidence_review_history(
  id bigint generated always as identity primary key,
  lot_id bigint not null references public.auction_lots(id) on delete cascade,
  external_lot_id text not null,
  source_attachment_url text,
  dimensions jsonb not null default '{}'::jsonb,
  overall_risk text,
  evidence_completeness smallint not null default 0,
  not_evaluable_count smallint not null default 0,
  repair_low_cop numeric,
  repair_base_cop numeric,
  repair_high_cop numeric,
  repair_basis_note text,
  general_notes text,
  marked_reviewed boolean not null default false,
  created_at timestamptz not null default clock_timestamp(),
  interpretation text not null default 'MANUAL_PERITAJE_EVIDENCE_NOT_AUTOMATED_DIAGNOSIS_OR_BUY_SIGNAL',
  constraint lot_peritaje_evidence_history_dimensions_object check(jsonb_typeof(dimensions)='object'),
  constraint lot_peritaje_evidence_history_completeness_range check(evidence_completeness between 0 and 8),
  constraint lot_peritaje_evidence_history_not_evaluable_range check(not_evaluable_count between 0 and 8),
  constraint lot_peritaje_evidence_history_overall_allowed check(overall_risk is null or overall_risk in ('LOW','MEDIUM','HIGH','CRITICAL','NOT_EVALUABLE')),
  constraint lot_peritaje_evidence_history_repair_nonnegative check(coalesce(repair_low_cop,0)>=0 and coalesce(repair_base_cop,0)>=0 and coalesce(repair_high_cop,0)>=0),
  constraint lot_peritaje_evidence_history_repair_order check(repair_low_cop is null or repair_base_cop is null or repair_high_cop is null or (repair_low_cop<=repair_base_cop and repair_base_cop<=repair_high_cop)),
  constraint lot_peritaje_evidence_history_basis_len check(repair_basis_note is null or char_length(repair_basis_note)<=4000),
  constraint lot_peritaje_evidence_history_notes_len check(general_notes is null or char_length(general_notes)<=5000),
  constraint lot_peritaje_evidence_history_interpretation_guard check(interpretation='MANUAL_PERITAJE_EVIDENCE_NOT_AUTOMATED_DIAGNOSIS_OR_BUY_SIGNAL')
);

alter table public.lot_peritaje_evidence_reviews enable row level security;
alter table public.lot_peritaje_evidence_review_history enable row level security;
revoke all on public.lot_peritaje_evidence_reviews,public.lot_peritaje_evidence_review_history from public,anon,authenticated;
grant select,insert,update on public.lot_peritaje_evidence_reviews to service_role;
grant select,insert on public.lot_peritaje_evidence_review_history to service_role;

create index if not exists ix_lot_peritaje_evidence_review_history_lot_created
  on public.lot_peritaje_evidence_review_history(lot_id,created_at desc);

create or replace function public.enforce_peritaje_evidence_review_gate_v50()
returns trigger
language plpgsql
security definer
set search_path=public,pg_catalog
as $$
declare
  e public.lot_peritaje_evidence_reviews%rowtype;
  mechanical text;
  transmission text;
  body text;
  safety text;
  electrical text;
  tires text;
  documentation text;
  missing_parts text;
begin
  if new.reviewed_at is null then return new; end if;

  select * into e
  from public.lot_peritaje_evidence_reviews
  where lot_id=new.lot_id and reviewed_at is not null;

  if e.id is null then
    raise exception 'v0.50 evidence workbench is required before peritaje REVIEWED';
  end if;

  mechanical:=nullif(upper(trim(coalesce(e.dimensions->'mechanical'->>'risk',''))),'');
  transmission:=nullif(upper(trim(coalesce(e.dimensions->'transmission'->>'risk',''))),'');
  body:=nullif(upper(trim(coalesce(e.dimensions->'body'->>'risk',''))),'');
  safety:=nullif(upper(trim(coalesce(e.dimensions->'safety'->>'risk',''))),'');
  electrical:=nullif(upper(trim(coalesce(e.dimensions->'electrical'->>'risk',''))),'');
  tires:=nullif(upper(trim(coalesce(e.dimensions->'tires'->>'risk',''))),'');
  documentation:=nullif(upper(trim(coalesce(e.dimensions->'documentation'->>'risk',''))),'');
  missing_parts:=nullif(upper(trim(coalesce(e.dimensions->'missing_parts'->>'risk',''))),'');

  if new.external_lot_id is distinct from e.external_lot_id
     or new.source_attachment_url is distinct from e.source_attachment_url
     or new.mechanical_risk is distinct from mechanical
     or new.transmission_risk is distinct from transmission
     or new.body_risk is distinct from body
     or new.safety_risk is distinct from safety
     or new.electrical_risk is distinct from electrical
     or new.tires_risk is distinct from tires
     or new.documentation_risk is distinct from documentation
     or new.missing_parts_risk is distinct from missing_parts
     or new.overall_risk is distinct from e.overall_risk
     or new.repair_low_cop is distinct from e.repair_low_cop
     or new.repair_base_cop is distinct from e.repair_base_cop
     or new.repair_high_cop is distinct from e.repair_high_cop then
    raise exception 'reviewed peritaje must match current v0.50 evidence record';
  end if;

  return new;
end;
$$;

revoke all on function public.enforce_peritaje_evidence_review_gate_v50() from public,anon,authenticated;

drop trigger if exists trg_peritaje_evidence_review_gate_v50 on public.lot_peritaje_reviews;
create trigger trg_peritaje_evidence_review_gate_v50
before insert or update on public.lot_peritaje_reviews
for each row execute function public.enforce_peritaje_evidence_review_gate_v50();

create or replace function public.dashboard_save_peritaje_evidence_review(
  p_external_lot_id text,
  p_source_attachment_url text default null,
  p_dimensions jsonb default '{}'::jsonb,
  p_repair_low_cop numeric default null,
  p_repair_base_cop numeric default null,
  p_repair_high_cop numeric default null,
  p_repair_basis_note text default null,
  p_general_notes text default null,
  p_mark_reviewed boolean default false
) returns jsonb
language plpgsql
security definer
set search_path=public,pg_catalog
as $$
declare
  v_lot_id bigint;
  v_dimensions jsonb:=coalesce(p_dimensions,'{}'::jsonb);
  v_required text[]:=array['mechanical','transmission','body','safety','electrical','tires','documentation','missing_parts'];
  v_allowed text[]:=array['LOW','MEDIUM','HIGH','CRITICAL','NOT_EVALUABLE'];
  v_dim text;
  v_risk text;
  v_note text;
  v_page text;
  v_score integer:=0;
  v_overall text;
  v_complete smallint:=0;
  v_not_evaluable smallint:=0;
  v_reviewed_at timestamptz;
  v_basis text:=nullif(trim(coalesce(p_repair_basis_note,'')),'');
  v_general text:=nullif(trim(coalesce(p_general_notes,'')),'');
  v_mechanical text;
  v_transmission text;
  v_body text;
  v_safety text;
  v_electrical text;
  v_tires text;
  v_documentation text;
  v_missing_parts text;
begin
  if p_external_lot_id is null or p_external_lot_id !~ '^[0-9]{5,12}$' then
    raise exception 'invalid external lot id';
  end if;
  select id into v_lot_id from public.auction_lots where external_lot_id=p_external_lot_id limit 1;
  if v_lot_id is null then raise exception 'lot not found'; end if;

  if not exists(select 1 from public.lot_attachments where lot_id=v_lot_id and kind='PERITAJE') then
    raise exception 'public peritaje not available for lot';
  end if;
  if p_source_attachment_url is not null and not exists(
    select 1 from public.lot_attachments where lot_id=v_lot_id and kind='PERITAJE' and url=p_source_attachment_url
  ) then raise exception 'peritaje source url does not belong to lot'; end if;
  if p_mark_reviewed and p_source_attachment_url is null then raise exception 'reviewed evidence requires source peritaje url'; end if;

  if jsonb_typeof(v_dimensions)<>'object' then raise exception 'dimensions must be a json object'; end if;
  if exists(select 1 from jsonb_object_keys(v_dimensions) as keys(k) where not (k=any(v_required))) then
    raise exception 'unknown peritaje evidence dimension';
  end if;

  foreach v_dim in array v_required loop
    if v_dimensions ? v_dim then
      if jsonb_typeof(v_dimensions->v_dim)<>'object' then raise exception 'dimension % must be an object',v_dim; end if;
      v_risk:=nullif(upper(trim(coalesce(v_dimensions->v_dim->>'risk',''))),'');
      v_note:=nullif(trim(coalesce(v_dimensions->v_dim->>'evidence_note','')),'');
      v_page:=nullif(trim(coalesce(v_dimensions->v_dim->>'page_reference','')),'');
      if v_risk is not null and not(v_risk=any(v_allowed)) then raise exception 'invalid risk for dimension %',v_dim; end if;
      if v_note is not null and char_length(v_note)>1000 then raise exception 'evidence note too long for dimension %',v_dim; end if;
      if v_page is not null and char_length(v_page)>120 then raise exception 'page reference too long for dimension %',v_dim; end if;
      if v_risk is not null and v_note is not null and char_length(v_note)>=10 then v_complete:=v_complete+1; end if;
      if v_risk='NOT_EVALUABLE' then v_not_evaluable:=v_not_evaluable+1; end if;
      if p_mark_reviewed and (v_risk is null or v_note is null or char_length(v_note)<10) then
        raise exception 'reviewed evidence requires risk and note >=10 chars for dimension %',v_dim;
      end if;
      v_score:=greatest(v_score,case v_risk when 'CRITICAL' then 4 when 'HIGH' then 3 when 'MEDIUM' then 2 when 'LOW' then 1 else 0 end);
    elsif p_mark_reviewed then
      raise exception 'reviewed evidence missing dimension %',v_dim;
    end if;
  end loop;

  if v_basis is not null and char_length(v_basis)>4000 then raise exception 'repair basis note too long'; end if;
  if v_general is not null and char_length(v_general)>5000 then raise exception 'general notes too long'; end if;
  if coalesce(p_repair_low_cop,0)<0 or coalesce(p_repair_base_cop,0)<0 or coalesce(p_repair_high_cop,0)<0 then
    raise exception 'repair estimate cannot be negative';
  end if;
  if p_repair_low_cop is not null and p_repair_base_cop is not null and p_repair_high_cop is not null
     and not(p_repair_low_cop<=p_repair_base_cop and p_repair_base_cop<=p_repair_high_cop) then
    raise exception 'repair estimates must satisfy low <= base <= high';
  end if;
  if p_mark_reviewed then
    if v_complete<>8 then raise exception 'reviewed evidence requires all eight dimensions complete'; end if;
    if p_repair_low_cop is null or p_repair_base_cop is null or p_repair_high_cop is null then
      raise exception 'reviewed evidence requires low, base and high repair estimates';
    end if;
    if v_basis is null or char_length(v_basis)<20 then
      raise exception 'reviewed evidence requires repair basis note of at least 20 characters';
    end if;
  end if;

  v_overall:=case
    when v_score=4 then 'CRITICAL'
    when v_score=3 then 'HIGH'
    when v_score=2 then 'MEDIUM'
    when v_score=1 and v_not_evaluable=0 then 'LOW'
    else 'NOT_EVALUABLE'
  end;
  v_reviewed_at:=case when p_mark_reviewed then clock_timestamp() else null end;

  v_mechanical:=nullif(upper(trim(coalesce(v_dimensions->'mechanical'->>'risk',''))),'');
  v_transmission:=nullif(upper(trim(coalesce(v_dimensions->'transmission'->>'risk',''))),'');
  v_body:=nullif(upper(trim(coalesce(v_dimensions->'body'->>'risk',''))),'');
  v_safety:=nullif(upper(trim(coalesce(v_dimensions->'safety'->>'risk',''))),'');
  v_electrical:=nullif(upper(trim(coalesce(v_dimensions->'electrical'->>'risk',''))),'');
  v_tires:=nullif(upper(trim(coalesce(v_dimensions->'tires'->>'risk',''))),'');
  v_documentation:=nullif(upper(trim(coalesce(v_dimensions->'documentation'->>'risk',''))),'');
  v_missing_parts:=nullif(upper(trim(coalesce(v_dimensions->'missing_parts'->>'risk',''))),'');

  insert into public.lot_peritaje_evidence_reviews(
    lot_id,external_lot_id,source_attachment_url,dimensions,overall_risk,evidence_completeness,not_evaluable_count,
    repair_low_cop,repair_base_cop,repair_high_cop,repair_basis_note,general_notes,reviewed_at,updated_at
  ) values(
    v_lot_id,p_external_lot_id,p_source_attachment_url,v_dimensions,v_overall,v_complete,v_not_evaluable,
    p_repair_low_cop,p_repair_base_cop,p_repair_high_cop,v_basis,v_general,v_reviewed_at,clock_timestamp()
  ) on conflict(lot_id) do update set
    external_lot_id=excluded.external_lot_id,
    source_attachment_url=excluded.source_attachment_url,
    dimensions=excluded.dimensions,
    overall_risk=excluded.overall_risk,
    evidence_completeness=excluded.evidence_completeness,
    not_evaluable_count=excluded.not_evaluable_count,
    repair_low_cop=excluded.repair_low_cop,
    repair_base_cop=excluded.repair_base_cop,
    repair_high_cop=excluded.repair_high_cop,
    repair_basis_note=excluded.repair_basis_note,
    general_notes=excluded.general_notes,
    reviewed_at=excluded.reviewed_at,
    updated_at=clock_timestamp();

  insert into public.lot_peritaje_evidence_review_history(
    lot_id,external_lot_id,source_attachment_url,dimensions,overall_risk,evidence_completeness,not_evaluable_count,
    repair_low_cop,repair_base_cop,repair_high_cop,repair_basis_note,general_notes,marked_reviewed
  ) values(
    v_lot_id,p_external_lot_id,p_source_attachment_url,v_dimensions,v_overall,v_complete,v_not_evaluable,
    p_repair_low_cop,p_repair_base_cop,p_repair_high_cop,v_basis,v_general,p_mark_reviewed
  );

  insert into public.lot_peritaje_reviews(
    lot_id,external_lot_id,source_attachment_url,mechanical_risk,transmission_risk,body_risk,safety_risk,
    electrical_risk,tires_risk,documentation_risk,missing_parts_risk,overall_risk,
    repair_low_cop,repair_base_cop,repair_high_cop,notes,reviewed_at,updated_at
  ) values(
    v_lot_id,p_external_lot_id,p_source_attachment_url,v_mechanical,v_transmission,v_body,v_safety,
    v_electrical,v_tires,v_documentation,v_missing_parts,v_overall,
    p_repair_low_cop,p_repair_base_cop,p_repair_high_cop,v_general,v_reviewed_at,clock_timestamp()
  ) on conflict(lot_id) do update set
    external_lot_id=excluded.external_lot_id,
    source_attachment_url=excluded.source_attachment_url,
    mechanical_risk=excluded.mechanical_risk,
    transmission_risk=excluded.transmission_risk,
    body_risk=excluded.body_risk,
    safety_risk=excluded.safety_risk,
    electrical_risk=excluded.electrical_risk,
    tires_risk=excluded.tires_risk,
    documentation_risk=excluded.documentation_risk,
    missing_parts_risk=excluded.missing_parts_risk,
    overall_risk=excluded.overall_risk,
    repair_low_cop=excluded.repair_low_cop,
    repair_base_cop=excluded.repair_base_cop,
    repair_high_cop=excluded.repair_high_cop,
    notes=excluded.notes,
    reviewed_at=excluded.reviewed_at,
    updated_at=clock_timestamp();

  insert into public.lot_peritaje_review_history(
    lot_id,external_lot_id,source_attachment_url,mechanical_risk,transmission_risk,body_risk,safety_risk,
    electrical_risk,tires_risk,documentation_risk,missing_parts_risk,overall_risk,
    repair_low_cop,repair_base_cop,repair_high_cop,notes,marked_reviewed
  ) values(
    v_lot_id,p_external_lot_id,p_source_attachment_url,v_mechanical,v_transmission,v_body,v_safety,
    v_electrical,v_tires,v_documentation,v_missing_parts,v_overall,
    p_repair_low_cop,p_repair_base_cop,p_repair_high_cop,v_general,p_mark_reviewed
  );

  return jsonb_build_object(
    'ok',true,
    'external_lot_id',p_external_lot_id,
    'reviewed',p_mark_reviewed,
    'evidence_completeness',v_complete,
    'not_evaluable_count',v_not_evaluable,
    'overall_risk',v_overall,
    'diagnosis_generated',false,
    'buy_signal',false,
    'cost_fields_modified',false,
    'economic_fields_modified',false,
    'interpretation','MANUAL_PERITAJE_EVIDENCE_NOT_AUTOMATED_DIAGNOSIS_OR_BUY_SIGNAL'
  );
end;
$$;

revoke all on function public.dashboard_save_peritaje_evidence_review(text,text,jsonb,numeric,numeric,numeric,text,text,boolean) from public,anon,authenticated;
grant execute on function public.dashboard_save_peritaje_evidence_review(text,text,jsonb,numeric,numeric,numeric,text,text,boolean) to service_role;

create or replace view public.dashboard_peritaje_evidence_workbench_v50 as
select
  d.external_lot_id,
  d.lot_id,
  d.title,
  d.city,
  d.seller,
  d.current_bid_cop,
  d.closes_at,
  d.hours_to_close,
  d.review_state,
  d.review_score,
  d.peritaje_count,
  d.peritajes,
  q.readiness_status,
  q.next_action,
  q.blockers,
  q.blocker_count,
  q.due_diligence_rank,
  q.due_diligence_stage,
  case when e.id is null then 'UNREVIEWED' when e.reviewed_at is null then 'DRAFT' else 'REVIEWED' end as evidence_review_status,
  e.source_attachment_url,
  e.dimensions,
  e.overall_risk,
  coalesce(e.evidence_completeness,0) as evidence_completeness,
  coalesce(e.not_evaluable_count,0) as not_evaluable_count,
  e.repair_low_cop,
  e.repair_base_cop,
  e.repair_high_cop,
  e.repair_basis_note,
  e.general_notes,
  e.reviewed_at,
  e.updated_at,
  'MANUAL_PERITAJE_EVIDENCE_NOT_AUTOMATED_DIAGNOSIS_OR_BUY_SIGNAL'::text as interpretation
from public.dashboard_lot_current d
left join public.dashboard_due_diligence_queue q using(lot_id)
left join public.lot_peritaje_evidence_reviews e using(lot_id)
where d.peritaje_count>0;

revoke all on public.dashboard_peritaje_evidence_workbench_v50 from public,anon,authenticated;
grant select on public.dashboard_peritaje_evidence_workbench_v50 to service_role;

comment on view public.dashboard_peritaje_evidence_workbench_v50 is
'v0.50 human evidence workbench for public peritaje PDFs. Eight structured dimensions and repair basis are required for REVIEWED. NOT_EVALUABLE uncertainty remains explicit. NOT automated diagnosis, buy signal, or automatic cost transfer.';
