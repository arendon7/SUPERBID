create or replace view public.dashboard_history_export as
select
  l.id as lot_id,
  l.external_lot_id,
  l.title,
  l.brand,
  l.line,
  l.version,
  l.model_year,
  l.city,
  l.seller,
  l.url,
  l.initial_bid_cop,
  l.first_seen_at,
  l.last_seen_at,
  o.outcome,
  o.closing_price_observed_cop,
  o.sale_price_confirmed_cop,
  o.confidence,
  o.confirmation_source,
  case
    when o.sale_price_confirmed_cop is not null then o.sale_price_confirmed_cop
    when o.closing_price_observed_cop is not null then o.closing_price_observed_cop
    else null
  end as historical_value_cop,
  case
    when o.sale_price_confirmed_cop is not null then 'SALE_CONFIRMED'
    when o.closing_price_observed_cop is not null then 'CLOSING_OBSERVED'
    else 'NO_FINAL_VALUE'
  end as historical_value_type,
  (select count(*) from public.auction_snapshots s where s.lot_id=l.id) as snapshot_count,
  (select count(*) from public.lot_attachments a where a.lot_id=l.id and a.kind='PERITAJE') as peritaje_count,
  fm.status as fasecolda_status,
  fm.best_code as fasecolda_code,
  fm.best_description as fasecolda_description,
  fm.current_value_cop as fasecolda_current_cop,
  fm.confidence as fasecolda_confidence
from public.auction_lots l
left join public.auction_outcomes o on o.lot_id=l.id
left join public.lot_fasecolda_matches fm on fm.lot_id=l.id;

revoke all on public.dashboard_history_export from public,anon,authenticated;
grant select on public.dashboard_history_export to service_role;

create or replace function public.dashboard_lot_timeline(p_external_lot_id text)
returns jsonb
language plpgsql
security definer
set search_path=public,pg_catalog
as $$
declare
  v_lot_id bigint;
  v_code text;
  v_result jsonb;
begin
  if p_external_lot_id is null or p_external_lot_id !~ '^\d{5,12}$' then
    raise exception 'invalid external lot id';
  end if;
  select id into v_lot_id from public.auction_lots where external_lot_id=p_external_lot_id order by id desc limit 1;
  if v_lot_id is null then raise exception 'lot not found'; end if;
  select best_code into v_code from public.lot_fasecolda_matches where lot_id=v_lot_id;

  select jsonb_build_object(
    'outcome',(
      select jsonb_build_object(
        'outcome',o.outcome,
        'closing_price_observed_cop',o.closing_price_observed_cop,
        'sale_price_confirmed_cop',o.sale_price_confirmed_cop,
        'confidence',o.confidence,
        'confirmation_source',o.confirmation_source,
        'notes',o.notes,
        'updated_at',o.updated_at,
        'value_type',case when o.sale_price_confirmed_cop is not null then 'SALE_CONFIRMED' when o.closing_price_observed_cop is not null then 'CLOSING_OBSERVED' else 'NO_FINAL_VALUE' end
      ) from public.auction_outcomes o where o.lot_id=v_lot_id
    ),
    'snapshots',coalesce((
      select jsonb_agg(jsonb_build_object(
        'observed_at',s.observed_at,
        'displayed_price_cop',s.displayed_price_cop,
        'bid_count',s.bid_count,
        'status_text',s.status_text,
        'outcome',s.outcome,
        'closes_at',s.closes_at
      ) order by s.observed_at)
      from public.auction_snapshots s where s.lot_id=v_lot_id
    ),'[]'::jsonb),
    'public_bid_history',coalesce((
      select jsonb_agg(jsonb_build_object(
        'sequence_no',b.sequence_no,
        'amount_cop',b.amount_cop,
        'bid_at',b.bid_at,
        'bid_at_text',b.bid_at_text,
        'observed_at',b.observed_at
      ) order by coalesce(b.bid_at,b.observed_at),b.sequence_no)
      from public.lot_bid_history b where b.lot_id=v_lot_id
    ),'[]'::jsonb),
    'fasecolda_history',coalesce((
      select jsonb_agg(jsonb_build_object(
        'value_date',h.value_date,
        'value_cop',h.value_cop,
        'code',h.code,
        'history_code',h.history_code,
        'model_year',h.model_year
      ) order by h.value_date)
      from public.fasecolda_value_history h
      where v_code is not null and h.code=v_code
        and h.model_year=(select model_year from public.auction_lots where id=v_lot_id)
    ),'[]'::jsonb),
    'provenance',coalesce((
      select jsonb_agg(jsonb_build_object(
        'source_type',p.source_type,
        'source_url',p.source_url,
        'observed_at',p.observed_at,
        'fields',p.fields,
        'confidence',p.confidence,
        'note',p.note
      ) order by p.observed_at desc)
      from public.lot_provenance p where p.lot_id=v_lot_id
    ),'[]'::jsonb),
    'cost_reviews',coalesce((
      select jsonb_agg(jsonb_build_object(
        'created_at',c.created_at,
        'marked_reviewed',c.marked_reviewed,
        'reviewed_at',c.reviewed_at,
        'transfer_cop',c.transfer_cop,
        'taxes_soat_cop',c.taxes_soat_cop,
        'transport_cop',c.transport_cop,
        'repair_cop',c.repair_cop,
        'detailing_cop',c.detailing_cop,
        'financing_cop',c.financing_cop,
        'admin_fee_cop',c.admin_fee_cop,
        'contingency_cop',c.contingency_cop,
        'source_note',c.source_note
      ) order by c.created_at desc)
      from public.lot_cost_review_history c where c.lot_id=v_lot_id
    ),'[]'::jsonb)
  ) into v_result;
  return v_result;
end
$$;

revoke all on function public.dashboard_lot_timeline(text) from public,anon,authenticated;
grant execute on function public.dashboard_lot_timeline(text) to service_role;
