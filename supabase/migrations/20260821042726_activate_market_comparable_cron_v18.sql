do $$
declare j bigint;
begin
  select jobid into j from cron.job where jobname='market-comparables-v18';
  if j is not null then perform cron.unschedule(j); end if;
  perform cron.schedule('market-comparables-v18','*/10 * * * *','select public.market_match_due(4);');
end
$$;
