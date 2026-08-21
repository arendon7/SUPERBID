create or replace function public.enqueue_market_comparable()
returns trigger
language plpgsql
security definer
set search_path=public,pg_catalog
as $$
declare v_conn text; v_status text;
begin
  if tg_op='UPDATE' and new.title is not distinct from old.title and new.model_year is not distinct from old.model_year then
    return new;
  end if;
  if new.model_year is null or new.title is null then return new; end if;
  select status into v_conn from public.market_connections where source='MERCADOLIBRE_MCO';
  v_status:=case when v_conn='READY' then 'PENDING' else 'AUTH_REQUIRED' end;
  insert into public.market_comparable_queue(lot_id,status,next_run_at,updated_at)
  values(new.id,v_status,clock_timestamp(),clock_timestamp())
  on conflict(lot_id) do update set
    status=case when public.market_comparable_queue.status='PAUSED' then 'PAUSED' else excluded.status end,
    next_run_at=case when public.market_comparable_queue.status='PAUSED' then public.market_comparable_queue.next_run_at else clock_timestamp() end,
    updated_at=clock_timestamp();
  return new;
end
$$;

update public.market_comparable_queue q
set status='AUTH_REQUIRED',updated_at=clock_timestamp()
where status='PENDING' and (select status from public.market_connections where source='MERCADOLIBRE_MCO')<>'READY';
