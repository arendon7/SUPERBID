create or replace view public.dashboard_lot_current as
select
  r.lot_id,
  r.external_lot_id,
  r.title,
  r.brand,
  r.line,
  r.model_year,
  r.city,
  r.seller,
  r.url,
  r.initial_bid_cop,
  r.current_bid_cop,
  r.bid_count,
  r.bid_observed_at,
  r.closes_at,
  r.outcome,
  r.commission_percent_public,
  r.auction_id,
  r.auction_desc,
  r.fasecolda_status,
  r.fasecolda_code,
  r.fasecolda_description,
  r.fasecolda_current_cop,
  r.fasecolda_12m_ago_cop,
  r.fasecolda_change_12m_pct,
  r.fasecolda_confidence,
  r.preliminary_resale_cop,
  r.ceiling_before_fixed_costs_cop,
  r.preliminary_headroom_before_fixed_costs_cop,
  r.opportunity_state,
  r.peritaje_count,
  r.peritajes,
  r.review_score,
  r.review_state,
  r.review_reasons,
  r.hours_to_close,
  m.market_status,
  m.market_comparable_count_live,
  m.median_asking_cop,
  m.p25_asking_cop,
  m.p75_asking_cop,
  m.market_quick_sale_cop,
  m.market_dispersion_pct,
  m.market_confidence,
  m.market_validation_available,
  m.costs_complete,
  m.cost_reviewed_at,
  m.fixed_costs_market_cop,
  m.conservative_resale_market_validated_cop,
  m.max_bid_market_validated_cop,
  m.market_headroom_cop,
  m.expected_profit_current_cop,
  m.expected_roi_current_pct,
  m.market_final_buy_recommendation_available,
  m.final_decision
from public.lot_review_queue_current r
left join public.lot_opportunity_market_validated m on m.lot_id=r.lot_id;

revoke all on public.dashboard_lot_current from public, anon, authenticated;
grant select on public.dashboard_lot_current to service_role;

create or replace function public.dashboard_token_valid(p_token text)
returns boolean
language sql
security definer
set search_path = public, vault, extensions, pg_catalog
as $$
  select case
    when p_token is null or length(p_token)<32 then false
    else coalesce(
      encode(extensions.digest(p_token,'sha256'),'hex') =
      encode(extensions.digest((select decrypted_secret from vault.decrypted_secrets where name='superbid_dashboard_read_token' order by updated_at desc limit 1),'sha256'),'hex'),
      false
    )
  end;
$$;

create or replace function public.dashboard_summary()
returns jsonb
language sql
security definer
set search_path = public, pg_catalog
as $$
  select jsonb_build_object(
    'generated_at',clock_timestamp(),
    'total_lots',(select count(*) from public.dashboard_lot_current),
    'review_now',(select count(*) from public.dashboard_lot_current where review_state='REVIEW_NOW'),
    'review_soon',(select count(*) from public.dashboard_lot_current where review_state='REVIEW_SOON'),
    'with_peritaje',(select count(*) from public.dashboard_lot_current where peritaje_count>0),
    'fasecolda_high',(select count(*) from public.dashboard_lot_current where fasecolda_status='HIGH'),
    'market_ready',(select count(*) from public.dashboard_lot_current where market_status='READY'),
    'final_recommendations',(select count(*) from public.dashboard_lot_current where market_final_buy_recommendation_available),
    'market_connection',(select jsonb_build_object('source',source,'status',status,'access_expires_at',access_expires_at,'last_refresh_at',last_refresh_at,'last_error',last_error) from public.market_connections where source='MERCADOLIBRE_MCO')
  );
$$;

revoke all on function public.dashboard_token_valid(text) from public, anon, authenticated;
grant execute on function public.dashboard_token_valid(text) to service_role;
revoke all on function public.dashboard_summary() from public, anon, authenticated;
grant execute on function public.dashboard_summary() to service_role;

-- The actual dashboard token is provisioned separately in Supabase Vault.
-- Never commit the secret value to migrations or Git.