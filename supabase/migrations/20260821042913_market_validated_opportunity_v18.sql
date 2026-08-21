create table if not exists public.lot_cost_overrides (
  lot_id bigint primary key references public.auction_lots(id) on delete cascade,
  transfer_cop bigint check (transfer_cop>=0),taxes_soat_cop bigint check (taxes_soat_cop>=0),transport_cop bigint check (transport_cop>=0),
  repair_cop bigint check (repair_cop>=0),detailing_cop bigint check (detailing_cop>=0),financing_cop bigint check (financing_cop>=0),
  admin_fee_cop bigint check (admin_fee_cop>=0),contingency_cop bigint check (contingency_cop>=0),source_note text,reviewed_at timestamptz,updated_at timestamptz not null default now()
);
alter table public.lot_cost_overrides enable row level security;
revoke all on public.lot_cost_overrides from anon,authenticated;
grant select,insert,update,delete on public.lot_cost_overrides to service_role;

create or replace view public.lot_opportunity_market_validated as
with p as (
  select transfer_cop profile_transfer_cop,taxes_soat_cop profile_taxes_soat_cop,transport_cop profile_transport_cop,repair_cop profile_repair_cop,
    detailing_cop profile_detailing_cop,financing_cop profile_financing_cop,admin_fee_cop profile_admin_fee_cop,contingency_cop profile_contingency_cop,
    vat_on_commission_pct market_vat_on_commission_pct,target_profit_pct_of_resale market_target_profit_pct,target_profit_floor_cop market_target_profit_floor_cop
  from public.deal_profiles where is_default order by profile_key limit 1
), x as (
  select m.*,
    coalesce(o.transfer_cop,p.profile_transfer_cop) transfer_cop_final,coalesce(o.taxes_soat_cop,p.profile_taxes_soat_cop) taxes_soat_cop_final,
    coalesce(o.transport_cop,p.profile_transport_cop) transport_cop_final,coalesce(o.repair_cop,p.profile_repair_cop) repair_cop_final,
    coalesce(o.detailing_cop,p.profile_detailing_cop) detailing_cop_final,coalesce(o.financing_cop,p.profile_financing_cop) financing_cop_final,
    coalesce(o.admin_fee_cop,p.profile_admin_fee_cop) admin_fee_cop_final,coalesce(o.contingency_cop,p.profile_contingency_cop) contingency_cop_final,
    p.market_vat_on_commission_pct,p.market_target_profit_pct,p.market_target_profit_floor_cop,o.reviewed_at cost_reviewed_at,
    (coalesce(o.transfer_cop,p.profile_transfer_cop) is not null and coalesce(o.taxes_soat_cop,p.profile_taxes_soat_cop) is not null and
     coalesce(o.transport_cop,p.profile_transport_cop) is not null and coalesce(o.repair_cop,p.profile_repair_cop) is not null and
     coalesce(o.detailing_cop,p.profile_detailing_cop) is not null and coalesce(o.financing_cop,p.profile_financing_cop) is not null and
     coalesce(o.admin_fee_cop,p.profile_admin_fee_cop) is not null and coalesce(o.contingency_cop,p.profile_contingency_cop) is not null) costs_complete
  from public.lot_market_intelligence_current m cross join p left join public.lot_cost_overrides o on o.lot_id=m.lot_id
), y as (
  select x.*,
    case when costs_complete then transfer_cop_final+taxes_soat_cop_final+transport_cop_final+repair_cop_final+detailing_cop_final+financing_cop_final+admin_fee_cop_final+contingency_cop_final end fixed_costs_market_cop,
    case when conservative_resale_market_validated_cop is not null then greatest(market_target_profit_floor_cop,round(conservative_resale_market_validated_cop*market_target_profit_pct)::bigint) end target_profit_market_cop,
    case when commission_percent_public is not null then 1+(commission_percent_public/100.0)*(1+market_vat_on_commission_pct) end bid_multiplier_market
  from x
), z as (
  select y.*,
    case when market_validation_available and costs_complete and conservative_resale_market_validated_cop is not null and bid_multiplier_market is not null
      then greatest(0,floor((conservative_resale_market_validated_cop-fixed_costs_market_cop-target_profit_market_cop)/bid_multiplier_market)::bigint) end max_bid_market_validated_cop,
    case when current_bid_cop is not null and costs_complete and bid_multiplier_market is not null then round(current_bid_cop*bid_multiplier_market)::bigint+fixed_costs_market_cop end expected_total_cost_current_cop
  from y
), w as (
  select z.*,
    case when max_bid_market_validated_cop is not null and current_bid_cop is not null then max_bid_market_validated_cop-current_bid_cop end market_headroom_cop,
    case when expected_total_cost_current_cop is not null and conservative_resale_market_validated_cop is not null then conservative_resale_market_validated_cop-expected_total_cost_current_cop end expected_profit_current_cop,
    case when expected_total_cost_current_cop>0 and conservative_resale_market_validated_cop is not null then round(((conservative_resale_market_validated_cop-expected_total_cost_current_cop)::numeric/expected_total_cost_current_cop)*100,2) end expected_roi_current_pct,
    (market_validation_available and costs_complete and commission_percent_public is not null and current_bid_cop is not null and cost_reviewed_at is not null) market_final_buy_recommendation_available
  from z
)
select w.*,
  case when fasecolda_status<>'HIGH' then 'REVIEW_VALUATION' when commission_percent_public is null then 'REVIEW_COMMISSION'
    when not market_validation_available then 'MARKET_VALIDATION_PENDING' when not costs_complete or cost_reviewed_at is null then 'CONFIGURE_COSTS'
    when current_bid_cop is null then 'NO_CURRENT_BID' when current_bid_cop>max_bid_market_validated_cop then 'NO_PUJAR'
    when expected_roi_current_pct>=20 and peritaje_count>0 then 'COMPRAR' when expected_roi_current_pct>=12 then 'VIGILAR' else 'RIESGO' end final_decision
from w;
revoke all on public.lot_opportunity_market_validated from public,anon,authenticated;
grant select on public.lot_opportunity_market_validated to service_role;
