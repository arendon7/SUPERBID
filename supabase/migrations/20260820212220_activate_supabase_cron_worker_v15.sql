-- Activate SUPERBID v0.15 database-native scheduling.
do $$
declare
  r record;
begin
  for r in select jobid from cron.job where jobname in ('superbid-discovery-v15','superbid-refresh-v15')
  loop
    perform cron.unschedule(r.jobid);
  end loop;
end
$$;

select cron.schedule(
  'superbid-discovery-v15',
  '*/15 * * * *',
  $cmd$select public.superbid_discover_open_vehicles(10,100);$cmd$
);

select cron.schedule(
  'superbid-refresh-v15',
  '* * * * *',
  $cmd$select public.superbid_refresh_due(40);$cmd$
);
