create or replace function public.enqueue_fasecolda_match()
returns trigger
language plpgsql
security definer
set search_path=public,extensions,pg_catalog
as $$
begin
  if new.title is null or new.model_year is null then return new; end if;
  if tg_op='INSERT' or old.title is distinct from new.title or old.model_year is distinct from new.model_year then
    insert into public.fasecolda_match_queue(lot_id,status,next_run_at,consecutive_errors,created_at,updated_at)
    values(new.id,'PENDING',clock_timestamp(),0,clock_timestamp(),clock_timestamp())
    on conflict(lot_id) do update set status='PENDING',next_run_at=clock_timestamp(),consecutive_errors=0,last_error=null,updated_at=clock_timestamp();
  end if;
  return new;
end
$$;

drop trigger if exists trg_enqueue_fasecolda_match on public.auction_lots;
create trigger trg_enqueue_fasecolda_match
after insert or update of title,model_year on public.auction_lots
for each row execute function public.enqueue_fasecolda_match();

revoke all on function public.enqueue_fasecolda_match() from public,anon,authenticated;

insert into public.fasecolda_match_queue(lot_id,status,next_run_at,consecutive_errors,created_at,updated_at)
select l.id,'PENDING',clock_timestamp(),0,clock_timestamp(),clock_timestamp()
from public.auction_lots l
left join public.fasecolda_match_queue q on q.lot_id=l.id
where l.title is not null and l.model_year is not null and q.lot_id is null
on conflict(lot_id) do nothing;

do $$
declare jid bigint;
begin
  select jobid into jid from cron.job where jobname='fasecolda-match-v16';
  if jid is not null then perform cron.unschedule(jid); end if;
  perform cron.schedule('fasecolda-match-v16','*/5 * * * *','select public.fasecolda_match_due(6);');
end $$;
