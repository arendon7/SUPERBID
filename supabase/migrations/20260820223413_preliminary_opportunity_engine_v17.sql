create table if not exists public.deal_profiles (
  profile_key text primary key,
  description text,
  is_default boolean not null default false,
  vat_on_commission_pct numeric(8,5) not null default 0.19 check(vat_on_commission_pct>=0 and vat_on_commission_pct<=1),
  target_profit_pct_of_resale numeric(8,5) not null default 0.12 check(target_profit_pct_of_resale>=0 and target_profit_pct_of_resale<1),
  target_profit_floor_cop bigint not null default 3000000 check(target_profit_floor_cop>=0),
  fasecolda_resale_factor numeric(8,5) not null default 0.90 check(fasecolda_resale_factor>0 and fasecolda_resale_factor<=1),
  transfer_cop bigint,
  taxes_soat_cop bigint,
  transport_cop bigint,
  repair_cop bigint,
  detailing_cop bigint,
  financing_cop bigint,
  admin_fee_cop bigint,
  contingency_cop bigint,
  source_note text,
  updated_at timestamptz not null default now(),
  check(transfer_cop is null or transfer_cop>=0),
  check(taxes_soat_cop is null or taxes_soat_cop>=0),
  check(transport_cop is null or transport_cop>=0),
  check(repair_cop is null or repair_cop>=0),
  check(detailing_cop is null or detailing_cop>=0),
  check(financing_cop is null or financing_cop>=0),
  check(admin_fee_cop is null or admin_fee_cop>=0),
  check(contingency_cop is null or contingency_cop>=0)
);

create unique index if not exists ux_deal_profiles_default on public.deal_profiles(is_default) where is_default;

insert into public.deal_profiles(
  profile_key,description,is_default,vat_on_commission_pct,target_profit_pct_of_resale,target_profit_floor_cop,fasecolda_resale_factor,
  transfer_cop,taxes_soat_cop,transport_cop,repair_cop,detailing_cop,financing_cop,admin_fee_cop,contingency_cop,source_note
) values(
  'PRELIMINARY_FASECOLDA',
  'Perfil preliminar: usa Fasecolda con haircut y comisión pública; costos fijos permanecen NULL hasta ser configurados.',
  true,0.19,0.12,3000000,0.90,
  null,null,null,null,null,null,null,null,
  'IVA general 19%; comisión tomada del lote. Factor Fasecolda 0.90 y utilidad 12% son supuestos de política, no hechos de mercado. No usar como decisión final sin costos y comparables.'
) on conflict(profile_key) do update set
  description=excluded.description,is_default=excluded.is_default,vat_on_commission_pct=excluded.vat_on_commission_pct,
  target_profit_pct_of_resale=excluded.target_profit_pct_of_resale,target_profit_floor_cop=excluded.target_profit_floor_cop,
  fasecolda_resale_factor=excluded.fasecolda_resale_factor,source_note=excluded.source_note,updated_at=now();

alter table public.deal_profiles enable row level security;
revoke all on public.deal_profiles from public,anon,authenticated;
grant select,insert,update,delete on public.deal_profiles to service_role;

create or replace view public.lot_opportunity_preliminary
with (security_invoker=true)
as
with p as (
  select * from public.deal_profiles where is_default limit 1
), base as (
  select
    i.*,
    case when s.evidence->>'commission_percent_public' ~ '^[0-9]+([.][0-9]+)?$'
         then (s.evidence->>'commission_percent_public')::numeric else null end as commission_percent_public,
    s.evidence->>'auction_id' as auction_id,
    s.evidence->>'auction_desc' as auction_desc,
    (select count(*)::integer from public.market_comparables mc where mc.lot_id=i.lot_id) as market_comparable_count
  from public.lot_intelligence_current i
  left join lateral (
    select ss.* from public.auction_snapshots ss
    where ss.lot_id=i.lot_id order by ss.observed_at desc limit 1
  ) s on true
), calc as (
  select
    b.*,p.profile_key,p.vat_on_commission_pct,p.target_profit_pct_of_resale,p.target_profit_floor_cop,p.fasecolda_resale_factor,
    p.transfer_cop,p.taxes_soat_cop,p.transport_cop,p.repair_cop,p.detailing_cop,p.financing_cop,p.admin_fee_cop,p.contingency_cop,
    (p.transfer_cop is not null and p.taxes_soat_cop is not null and p.transport_cop is not null and p.repair_cop is not null and p.detailing_cop is not null and p.financing_cop is not null and p.admin_fee_cop is not null and p.contingency_cop is not null) as fixed_costs_complete,
    case when b.fasecolda_status='HIGH' and b.fasecolda_current_cop is not null then floor(b.fasecolda_current_cop*p.fasecolda_resale_factor)::bigint end as preliminary_resale_cop,
    case when b.commission_percent_public is not null then 1 + (b.commission_percent_public/100.0)*(1+p.vat_on_commission_pct) end as bid_multiplier,
    case when p.transfer_cop is not null and p.taxes_soat_cop is not null and p.transport_cop is not null and p.repair_cop is not null and p.detailing_cop is not null and p.financing_cop is not null and p.admin_fee_cop is not null and p.contingency_cop is not null
         then p.transfer_cop+p.taxes_soat_cop+p.transport_cop+p.repair_cop+p.detailing_cop+p.financing_cop+p.admin_fee_cop+p.contingency_cop end as fixed_costs_cop
  from base b cross join p
), profit as (
  select c.*,
    case when c.preliminary_resale_cop is not null then greatest(c.target_profit_floor_cop,round(c.preliminary_resale_cop*c.target_profit_pct_of_resale)::bigint) end as target_profit_cop
  from calc c
), ceilings as (
  select pr.*,
    case when pr.preliminary_resale_cop is not null and pr.bid_multiplier is not null
         then greatest(0,floor((pr.preliminary_resale_cop-pr.target_profit_cop)/pr.bid_multiplier))::bigint end as ceiling_before_fixed_costs_cop,
    case when pr.preliminary_resale_cop is not null and pr.bid_multiplier is not null and pr.fixed_costs_complete
         then greatest(0,floor((pr.preliminary_resale_cop-pr.fixed_costs_cop-pr.target_profit_cop)/pr.bid_multiplier))::bigint end as max_bid_preliminary_cop
  from profit pr
)
select
  c.*,
  case when c.fasecolda_status='HIGH' and c.current_bid_cop is not null and c.fasecolda_current_cop>0
       then round((1-c.current_bid_cop::numeric/c.fasecolda_current_cop)*100,2) end as discount_vs_fasecolda_pct,
  case when c.current_bid_cop is not null and c.ceiling_before_fixed_costs_cop is not null
       then c.ceiling_before_fixed_costs_cop-c.current_bid_cop end as preliminary_headroom_before_fixed_costs_cop,
  case when c.current_bid_cop is not null and c.max_bid_preliminary_cop is not null
       then c.max_bid_preliminary_cop-c.current_bid_cop end as preliminary_headroom_cop,
  case
    when c.fasecolda_status is distinct from 'HIGH' then 'REVIEW_VALUATION'
    when c.commission_percent_public is null then 'REVIEW_COMMISSION'
    when c.current_bid_cop is null then 'NO_CURRENT_BID'
    when not c.fixed_costs_complete then 'CONFIGURE_COSTS'
    when c.market_comparable_count=0 then 'MARKET_VALIDATION_PENDING'
    when c.current_bid_cop>c.max_bid_preliminary_cop then 'PRELIMINARY_OVER_CEILING'
    else 'PRELIMINARY_WITHIN_CEILING'
  end as opportunity_state,
  false as final_buy_recommendation_available
from ceilings c;

revoke all on public.lot_opportunity_preliminary from public,anon,authenticated;
grant select on public.lot_opportunity_preliminary to service_role;
