create table if not exists public.lot_cost_review_history (
  id bigint generated always as identity primary key,
  lot_id bigint not null references public.auction_lots(id) on delete cascade,
  transfer_cop bigint,
  taxes_soat_cop bigint,
  transport_cop bigint,
  repair_cop bigint,
  detailing_cop bigint,
  financing_cop bigint,
  admin_fee_cop bigint,
  contingency_cop bigint,
  source_note text,
  marked_reviewed boolean not null default false,
  reviewed_at timestamptz,
  created_at timestamptz not null default now(),
  check (coalesce(transfer_cop,0)>=0),
  check (coalesce(taxes_soat_cop,0)>=0),
  check (coalesce(transport_cop,0)>=0),
  check (coalesce(repair_cop,0)>=0),
  check (coalesce(detailing_cop,0)>=0),
  check (coalesce(financing_cop,0)>=0),
  check (coalesce(admin_fee_cop,0)>=0),
  check (coalesce(contingency_cop,0)>=0)
);

alter table public.lot_cost_review_history enable row level security;
revoke all on public.lot_cost_review_history from public, anon, authenticated;
grant select, insert on public.lot_cost_review_history to service_role;
create index if not exists ix_lot_cost_review_history_lot on public.lot_cost_review_history(lot_id,created_at desc);

create or replace function public.dashboard_save_lot_costs(
  p_external_lot_id text,
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
  v_lot_id bigint;
  v_complete boolean;
  v_reviewed_at timestamptz;
  v_max constant bigint := 50000000000;
  v_result jsonb;
begin
  if p_external_lot_id is null or p_external_lot_id !~ '^\d{5,12}$' then
    raise exception 'invalid external lot id';
  end if;

  select id into v_lot_id from public.auction_lots
  where external_lot_id=p_external_lot_id
  order by id desc limit 1;
  if v_lot_id is null then raise exception 'lot not found'; end if;

  if exists (
    select 1 from (values
      (p_transfer_cop),(p_taxes_soat_cop),(p_transport_cop),(p_repair_cop),
      (p_detailing_cop),(p_financing_cop),(p_admin_fee_cop),(p_contingency_cop)
    ) v(x) where x is not null and (x<0 or x>v_max)
  ) then raise exception 'cost outside allowed range'; end if;

  v_complete := p_transfer_cop is not null and p_taxes_soat_cop is not null and
    p_transport_cop is not null and p_repair_cop is not null and
    p_detailing_cop is not null and p_financing_cop is not null and
    p_admin_fee_cop is not null and p_contingency_cop is not null;

  if p_mark_reviewed and not v_complete then
    raise exception 'all eight costs are required before review';
  end if;
  v_reviewed_at := case when p_mark_reviewed and v_complete then clock_timestamp() else null end;

  insert into public.lot_cost_overrides(
    lot_id,transfer_cop,taxes_soat_cop,transport_cop,repair_cop,detailing_cop,
    financing_cop,admin_fee_cop,contingency_cop,source_note,reviewed_at,updated_at
  ) values (
    v_lot_id,p_transfer_cop,p_taxes_soat_cop,p_transport_cop,p_repair_cop,p_detailing_cop,
    p_financing_cop,p_admin_fee_cop,p_contingency_cop,nullif(left(coalesce(p_source_note,''),2000),''),v_reviewed_at,clock_timestamp()
  ) on conflict(lot_id) do update set
    transfer_cop=excluded.transfer_cop,
    taxes_soat_cop=excluded.taxes_soat_cop,
    transport_cop=excluded.transport_cop,
    repair_cop=excluded.repair_cop,
    detailing_cop=excluded.detailing_cop,
    financing_cop=excluded.financing_cop,
    admin_fee_cop=excluded.admin_fee_cop,
    contingency_cop=excluded.contingency_cop,
    source_note=excluded.source_note,
    reviewed_at=excluded.reviewed_at,
    updated_at=excluded.updated_at;

  insert into public.lot_cost_review_history(
    lot_id,transfer_cop,taxes_soat_cop,transport_cop,repair_cop,detailing_cop,
    financing_cop,admin_fee_cop,contingency_cop,source_note,marked_reviewed,reviewed_at
  ) values (
    v_lot_id,p_transfer_cop,p_taxes_soat_cop,p_transport_cop,p_repair_cop,p_detailing_cop,
    p_financing_cop,p_admin_fee_cop,p_contingency_cop,nullif(left(coalesce(p_source_note,''),2000),''),p_mark_reviewed,v_reviewed_at
  );

  select jsonb_build_object(
    'ok',true,
    'external_lot_id',p_external_lot_id,
    'costs_complete',v_complete,
    'reviewed_at',v_reviewed_at,
    'final_decision',m.final_decision,
    'market_validation_available',m.market_validation_available,
    'max_bid_market_validated_cop',m.max_bid_market_validated_cop,
    'expected_profit_current_cop',m.expected_profit_current_cop,
    'expected_roi_current_pct',m.expected_roi_current_pct
  ) into v_result
  from public.lot_opportunity_market_validated m where m.lot_id=v_lot_id;

  return coalesce(v_result,jsonb_build_object('ok',true,'external_lot_id',p_external_lot_id,'costs_complete',v_complete,'reviewed_at',v_reviewed_at));
end
$$;

revoke all on function public.dashboard_save_lot_costs(text,bigint,bigint,bigint,bigint,bigint,bigint,bigint,bigint,text,boolean) from public,anon,authenticated;
grant execute on function public.dashboard_save_lot_costs(text,bigint,bigint,bigint,bigint,bigint,bigint,bigint,bigint,text,boolean) to service_role;
