create table if not exists public.cost_assumption_profile_versions(
  id bigint generated always as identity primary key,
  status text not null default 'DRAFT' check(status in ('DRAFT','REVIEWED')),
  transfer_cop bigint check(transfer_cop is null or transfer_cop between 0 and 50000000000),
  taxes_soat_cop bigint check(taxes_soat_cop is null or taxes_soat_cop between 0 and 50000000000),
  transport_cop bigint check(transport_cop is null or transport_cop between 0 and 50000000000),
  repair_cop bigint check(repair_cop is null or repair_cop between 0 and 50000000000),
  detailing_cop bigint check(detailing_cop is null or detailing_cop between 0 and 50000000000),
  financing_cop bigint check(financing_cop is null or financing_cop between 0 and 50000000000),
  admin_fee_cop bigint check(admin_fee_cop is null or admin_fee_cop between 0 and 50000000000),
  contingency_cop bigint check(contingency_cop is null or contingency_cop between 0 and 50000000000),
  source_note text check(source_note is null or char_length(source_note)<=4000),
  profile_fingerprint text not null check(profile_fingerprint ~ '^[0-9a-f]{32}$'),
  reviewed_at timestamptz,
  created_at timestamptz not null default clock_timestamp(),
  interpretation text not null default 'COST_PROFILE_ASSUMPTION_NOT_LOT_COST'
    check(interpretation='COST_PROFILE_ASSUMPTION_NOT_LOT_COST'),
  check(
    status='DRAFT' or (
      reviewed_at is not null and
      transfer_cop is not null and taxes_soat_cop is not null and transport_cop is not null and repair_cop is not null and
      detailing_cop is not null and financing_cop is not null and admin_fee_cop is not null and contingency_cop is not null
    )
  ),
  check(status='REVIEWED' or reviewed_at is null)
);

create table if not exists public.lot_cost_profile_application_history(
  id bigint generated always as identity primary key,
  lot_id bigint not null references public.auction_lots(id) on delete cascade,
  external_lot_id text not null,
  profile_version_id bigint not null references public.cost_assumption_profile_versions(id) on delete restrict,
  profile_fingerprint text not null check(profile_fingerprint ~ '^[0-9a-f]{32}$'),
  repair_mode text not null check(repair_mode in ('PROFILE','PRESERVE_LOT')),
  previous_costs jsonb not null default '{}'::jsonb,
  applied_costs jsonb not null,
  marked_reviewed boolean not null default false,
  note text check(note is null or char_length(note)<=2000),
  applied_at timestamptz not null default clock_timestamp(),
  interpretation text not null default 'COST_PROFILE_APPLICATION_REQUIRES_LOT_CONFIRMATION'
    check(interpretation='COST_PROFILE_APPLICATION_REQUIRES_LOT_CONFIRMATION')
);

alter table public.cost_assumption_profile_versions enable row level security;
alter table public.lot_cost_profile_application_history enable row level security;
revoke all on public.cost_assumption_profile_versions,public.lot_cost_profile_application_history from public,anon,authenticated;
grant select,insert on public.cost_assumption_profile_versions to service_role;
grant select,insert on public.lot_cost_profile_application_history to service_role;
create index if not exists ix_cost_assumption_profile_reviewed on public.cost_assumption_profile_versions(status,reviewed_at desc,id desc);
create index if not exists ix_lot_cost_profile_application_lot on public.lot_cost_profile_application_history(lot_id,applied_at desc,id desc);

create or replace function public.dashboard_save_cost_assumption_profile(
  p_transfer_cop bigint,
  p_taxes_soat_cop bigint,
  p_transport_cop bigint,
  p_repair_cop bigint,
  p_detailing_cop bigint,
  p_financing_cop bigint,
  p_admin_fee_cop bigint,
  p_contingency_cop bigint,
  p_source_note text default null,
  p_mark_reviewed boolean default false
) returns jsonb
language plpgsql
security definer
set search_path=public,pg_catalog
as $$
declare
  v_id bigint;
  v_fingerprint text;
  v_note text:=nullif(left(trim(coalesce(p_source_note,'')),4000),'');
  v_reviewed_at timestamptz;
  v_max constant bigint:=50000000000;
begin
  if exists(
    select 1 from (values
      (p_transfer_cop),(p_taxes_soat_cop),(p_transport_cop),(p_repair_cop),
      (p_detailing_cop),(p_financing_cop),(p_admin_fee_cop),(p_contingency_cop)
    ) v(x) where x is not null and (x<0 or x>v_max)
  ) then raise exception 'cost assumption outside allowed range'; end if;

  if p_mark_reviewed and (
    p_transfer_cop is null or p_taxes_soat_cop is null or p_transport_cop is null or p_repair_cop is null or
    p_detailing_cop is null or p_financing_cop is null or p_admin_fee_cop is null or p_contingency_cop is null
  ) then raise exception 'all eight cost assumptions are required before review'; end if;
  if p_mark_reviewed and char_length(coalesce(v_note,''))<10 then
    raise exception 'reviewed cost profile requires a source note';
  end if;

  v_fingerprint:=md5(concat_ws('|',
    coalesce(p_transfer_cop::text,''),coalesce(p_taxes_soat_cop::text,''),coalesce(p_transport_cop::text,''),coalesce(p_repair_cop::text,''),
    coalesce(p_detailing_cop::text,''),coalesce(p_financing_cop::text,''),coalesce(p_admin_fee_cop::text,''),coalesce(p_contingency_cop::text,''),coalesce(v_note,'')
  ));
  v_reviewed_at:=case when p_mark_reviewed then clock_timestamp() else null end;

  insert into public.cost_assumption_profile_versions(
    status,transfer_cop,taxes_soat_cop,transport_cop,repair_cop,detailing_cop,financing_cop,admin_fee_cop,contingency_cop,
    source_note,profile_fingerprint,reviewed_at
  ) values(
    case when p_mark_reviewed then 'REVIEWED' else 'DRAFT' end,
    p_transfer_cop,p_taxes_soat_cop,p_transport_cop,p_repair_cop,p_detailing_cop,p_financing_cop,p_admin_fee_cop,p_contingency_cop,
    v_note,v_fingerprint,v_reviewed_at
  ) returning id into v_id;

  return jsonb_build_object(
    'ok',true,'profile_version_id',v_id,'status',case when p_mark_reviewed then 'REVIEWED' else 'DRAFT' end,
    'profile_fingerprint',v_fingerprint,'reviewed_at',v_reviewed_at,
    'lots_modified',0,'buy_signal',false,'interpretation','COST_PROFILE_ASSUMPTION_NOT_LOT_COST'
  );
end$$;

revoke all on function public.dashboard_save_cost_assumption_profile(bigint,bigint,bigint,bigint,bigint,bigint,bigint,bigint,text,boolean) from public,anon,authenticated;
grant execute on function public.dashboard_save_cost_assumption_profile(bigint,bigint,bigint,bigint,bigint,bigint,bigint,bigint,text,boolean) to service_role;

create or replace view public.cost_assumption_profile_current as
select id as profile_version_id,status,transfer_cop,taxes_soat_cop,transport_cop,repair_cop,detailing_cop,financing_cop,admin_fee_cop,contingency_cop,
  source_note,profile_fingerprint,reviewed_at,created_at,interpretation
from public.cost_assumption_profile_versions
where status='REVIEWED' and reviewed_at is not null
order by reviewed_at desc,id desc
limit 1;
revoke all on public.cost_assumption_profile_current from public,anon,authenticated;
grant select on public.cost_assumption_profile_current to service_role;

create or replace function public.dashboard_apply_cost_profile_to_lot(
  p_external_lot_id text,
  p_profile_version_id bigint,
  p_repair_mode text default 'PROFILE',
  p_mark_reviewed boolean default false,
  p_note text default null
) returns jsonb
language plpgsql
security definer
set search_path=public,pg_catalog
as $$
declare
  v_lot_id bigint;
  v_profile public.cost_assumption_profile_versions%rowtype;
  v_existing public.lot_cost_overrides%rowtype;
  v_mode text:=upper(trim(coalesce(p_repair_mode,'')));
  v_repair bigint;
  v_reviewed_at timestamptz;
  v_note text:=nullif(left(trim(coalesce(p_note,'')),2000),'');
  v_source_note text;
  v_previous jsonb;
  v_applied jsonb;
  v_readiness record;
begin
  if p_external_lot_id is null or p_external_lot_id !~ '^\d{5,12}$' then raise exception 'invalid external lot id'; end if;
  if p_profile_version_id is null or p_profile_version_id<=0 then raise exception 'invalid profile version id'; end if;
  if v_mode not in ('PROFILE','PRESERVE_LOT') then raise exception 'invalid repair mode'; end if;
  if p_mark_reviewed and char_length(coalesce(v_note,''))<5 then raise exception 'reviewed lot application requires a lot note'; end if;

  select id into v_lot_id from public.auction_lots where external_lot_id=p_external_lot_id order by id desc limit 1;
  if v_lot_id is null then raise exception 'lot not found'; end if;
  if exists(select 1 from public.dashboard_economic_readiness_current where lot_id=v_lot_id and readiness_status='CLOSED') then
    raise exception 'closed lot cannot receive a new cost profile application';
  end if;

  select * into v_profile from public.cost_assumption_profile_versions where id=p_profile_version_id;
  if v_profile.id is null then raise exception 'cost profile version not found'; end if;
  if v_profile.status<>'REVIEWED' or v_profile.reviewed_at is null then raise exception 'only REVIEWED cost profiles may be applied'; end if;

  select * into v_existing from public.lot_cost_overrides where lot_id=v_lot_id for update;
  if v_mode='PRESERVE_LOT' and (v_existing.lot_id is null or v_existing.repair_cop is null) then
    raise exception 'PRESERVE_LOT requires an existing lot repair cost';
  end if;
  v_repair:=case when v_mode='PRESERVE_LOT' then v_existing.repair_cop else v_profile.repair_cop end;
  v_reviewed_at:=case when p_mark_reviewed then clock_timestamp() else null end;
  v_source_note:=left('PROFILE_V'||v_profile.id::text||' ['||v_profile.profile_fingerprint||']'
    ||case when v_note is not null then ' · '||v_note else '' end,2000);

  v_previous:=jsonb_build_object(
    'transfer_cop',v_existing.transfer_cop,'taxes_soat_cop',v_existing.taxes_soat_cop,'transport_cop',v_existing.transport_cop,
    'repair_cop',v_existing.repair_cop,'detailing_cop',v_existing.detailing_cop,'financing_cop',v_existing.financing_cop,
    'admin_fee_cop',v_existing.admin_fee_cop,'contingency_cop',v_existing.contingency_cop,'reviewed_at',v_existing.reviewed_at
  );
  v_applied:=jsonb_build_object(
    'transfer_cop',v_profile.transfer_cop,'taxes_soat_cop',v_profile.taxes_soat_cop,'transport_cop',v_profile.transport_cop,
    'repair_cop',v_repair,'detailing_cop',v_profile.detailing_cop,'financing_cop',v_profile.financing_cop,
    'admin_fee_cop',v_profile.admin_fee_cop,'contingency_cop',v_profile.contingency_cop
  );

  insert into public.lot_cost_overrides(
    lot_id,transfer_cop,taxes_soat_cop,transport_cop,repair_cop,detailing_cop,financing_cop,admin_fee_cop,contingency_cop,source_note,reviewed_at,updated_at
  ) values(
    v_lot_id,v_profile.transfer_cop,v_profile.taxes_soat_cop,v_profile.transport_cop,v_repair,v_profile.detailing_cop,v_profile.financing_cop,
    v_profile.admin_fee_cop,v_profile.contingency_cop,v_source_note,v_reviewed_at,clock_timestamp()
  ) on conflict(lot_id) do update set
    transfer_cop=excluded.transfer_cop,taxes_soat_cop=excluded.taxes_soat_cop,transport_cop=excluded.transport_cop,repair_cop=excluded.repair_cop,
    detailing_cop=excluded.detailing_cop,financing_cop=excluded.financing_cop,admin_fee_cop=excluded.admin_fee_cop,contingency_cop=excluded.contingency_cop,
    source_note=excluded.source_note,reviewed_at=excluded.reviewed_at,updated_at=excluded.updated_at;

  insert into public.lot_cost_review_history(
    lot_id,transfer_cop,taxes_soat_cop,transport_cop,repair_cop,detailing_cop,financing_cop,admin_fee_cop,contingency_cop,source_note,marked_reviewed,reviewed_at
  ) values(
    v_lot_id,v_profile.transfer_cop,v_profile.taxes_soat_cop,v_profile.transport_cop,v_repair,v_profile.detailing_cop,v_profile.financing_cop,
    v_profile.admin_fee_cop,v_profile.contingency_cop,v_source_note,p_mark_reviewed,v_reviewed_at
  );

  insert into public.lot_cost_profile_application_history(
    lot_id,external_lot_id,profile_version_id,profile_fingerprint,repair_mode,previous_costs,applied_costs,marked_reviewed,note
  ) values(
    v_lot_id,p_external_lot_id,v_profile.id,v_profile.profile_fingerprint,v_mode,v_previous,v_applied,p_mark_reviewed,v_note
  );

  select readiness_status,next_action,blocker_count,cost_review_status,completed_cost_fields,final_decision
  into v_readiness
  from public.dashboard_economic_readiness_current where lot_id=v_lot_id;

  return jsonb_build_object(
    'ok',true,'external_lot_id',p_external_lot_id,'profile_version_id',v_profile.id,'profile_fingerprint',v_profile.profile_fingerprint,
    'repair_mode',v_mode,'cost_review_status',v_readiness.cost_review_status,'completed_cost_fields',v_readiness.completed_cost_fields,
    'readiness_status',v_readiness.readiness_status,'next_action',v_readiness.next_action,'blocker_count',v_readiness.blocker_count,
    'final_decision',v_readiness.final_decision,'buy_signal',false,
    'interpretation','COST_PROFILE_APPLICATION_REQUIRES_LOT_CONFIRMATION'
  );
end$$;

revoke all on function public.dashboard_apply_cost_profile_to_lot(text,bigint,text,boolean,text) from public,anon,authenticated;
grant execute on function public.dashboard_apply_cost_profile_to_lot(text,bigint,text,boolean,text) to service_role;

-- v0.45 fixes coverage: cost readiness must not depend on a public peritaje existing.
-- Preserve the pre-v0.45 column contract while changing the base relation to dashboard_lot_current.
create or replace view public.dashboard_cost_readiness_current as
select
  d.external_lot_id,
  d.lot_id,
  d.title,
  d.city,
  d.seller,
  d.current_bid_cop,
  d.closes_at,
  d.review_state,
  d.review_score,
  case
    when coalesce(d.peritaje_count,0)=0 then 'NOT_AVAILABLE'
    when p.lot_id is null then 'UNREVIEWED'
    when p.reviewed_at is null then 'DRAFT'
    else 'REVIEWED'
  end as peritaje_review_status,
  p.overall_risk,
  p.repair_low_cop,
  p.repair_base_cop,
  p.repair_high_cop,
  p.reviewed_at as peritaje_reviewed_at,
  c.transfer_cop,
  c.taxes_soat_cop,
  c.transport_cop,
  c.repair_cop,
  c.detailing_cop,
  c.financing_cop,
  c.admin_fee_cop,
  c.contingency_cop,
  c.reviewed_at as costs_reviewed_at,
  case when c.lot_id is null then 'NO_COSTS' when c.reviewed_at is not null then 'REVIEWED' else 'DRAFT' end as cost_review_status,
  ((c.transfer_cop is not null)::int +(c.taxes_soat_cop is not null)::int +(c.transport_cop is not null)::int +(c.repair_cop is not null)::int +
   (c.detailing_cop is not null)::int +(c.financing_cop is not null)::int +(c.admin_fee_cop is not null)::int +(c.contingency_cop is not null)::int) as completed_cost_fields,
  case
    when c.repair_cop is null then 'NOT_TRANSFERRED'
    when p.repair_low_cop is not null and c.repair_cop=p.repair_low_cop then 'MATCH_LOW'
    when p.repair_base_cop is not null and c.repair_cop=p.repair_base_cop then 'MATCH_BASE'
    when p.repair_high_cop is not null and c.repair_cop=p.repair_high_cop then 'MATCH_HIGH'
    else 'CUSTOM'
  end as repair_cost_source_status,
  (p.reviewed_at is not null) as peritaje_ready_for_cost_transfer,
  'MANUAL_PERITAJE_COST_TRANSFER_NOT_AUTOMATIC'::text as interpretation
from public.dashboard_lot_current d
left join public.lot_peritaje_reviews p on p.lot_id=d.lot_id
left join public.lot_cost_overrides c on c.lot_id=d.lot_id;

revoke all on public.dashboard_cost_readiness_current from public,anon,authenticated;
grant select on public.dashboard_cost_readiness_current to service_role;

create or replace view public.dashboard_cost_governance_queue_v45 as
select
  r.external_lot_id,r.lot_id,r.title,l.model_year,r.city,r.seller,r.current_bid_cop,r.closes_at,r.hours_to_close,r.review_state,r.review_score,
  r.readiness_status,r.next_action,r.blocker_count,r.blockers,
  c.peritaje_review_status,c.overall_risk,c.repair_low_cop,c.repair_base_cop,c.repair_high_cop,c.peritaje_reviewed_at,
  c.transfer_cop,c.taxes_soat_cop,c.transport_cop,c.repair_cop,c.detailing_cop,c.financing_cop,c.admin_fee_cop,c.contingency_cop,
  c.costs_reviewed_at,c.cost_review_status,c.completed_cost_fields,c.repair_cost_source_status,c.peritaje_ready_for_cost_transfer,
  cp.profile_version_id,cp.profile_fingerprint,cp.reviewed_at as profile_reviewed_at,
  case
    when c.cost_review_status='REVIEWED' and c.completed_cost_fields=8 then 'COSTS_REVIEWED'
    when c.completed_cost_fields=8 then 'REVIEW_EXISTING_COSTS'
    when cp.profile_version_id is null then 'CONFIGURE_REVIEWED_PROFILE'
    when c.repair_cop is not null then 'APPLY_PROFILE_PRESERVE_REPAIR'
    when c.peritaje_review_status='REVIEWED' and c.repair_base_cop is not null then 'TRANSFER_REPAIR_OR_APPLY_PROFILE'
    else 'APPLY_REVIEWED_PROFILE'
  end as cost_governance_next_action,
  'COST_GOVERNANCE_NOT_BUY_SIGNAL'::text as governance_interpretation
from public.dashboard_economic_readiness_current r
join public.auction_lots l on l.id=r.lot_id
join public.dashboard_cost_readiness_current c on c.lot_id=r.lot_id
left join public.cost_assumption_profile_current cp on true
where r.readiness_status='BLOCKED'
  and r.blockers && array['LOT_COSTS_MISSING','LOT_COSTS_INCOMPLETE','LOT_COSTS_NOT_REVIEWED']::text[];

revoke all on public.dashboard_cost_governance_queue_v45 from public,anon,authenticated;
grant select on public.dashboard_cost_governance_queue_v45 to service_role;

comment on table public.cost_assumption_profile_versions is 'Immutable reusable cost assumptions. REVIEWED means the profile itself was reviewed; it does not apply costs to any lot.';
comment on function public.dashboard_save_cost_assumption_profile(bigint,bigint,bigint,bigint,bigint,bigint,bigint,bigint,text,boolean) is 'Creates an immutable DRAFT or REVIEWED cost-assumption version. Never applies it to lots.';
comment on function public.dashboard_apply_cost_profile_to_lot(text,bigint,text,boolean,text) is 'Explicitly snapshots one REVIEWED cost profile into one lot. No bulk/global application. PRESERVE_LOT keeps an existing repair cost.';
comment on view public.dashboard_cost_readiness_current is 'Cost readiness for all lots, including vehicles with no public peritaje. Peritaje is optional evidence, not a prerequisite to cost workflow coverage.';
comment on view public.dashboard_cost_governance_queue_v45 is 'All active readiness-blocked lots carrying cost blockers, with explicit reviewed-profile availability and no buy signal.';
