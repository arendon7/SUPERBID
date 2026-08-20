create table if not exists public.lot_provenance (
  id bigint generated always as identity primary key,
  lot_id bigint not null references public.auction_lots(id) on delete cascade,
  source_type text not null,
  source_url text not null,
  observed_at timestamptz not null default now(),
  fields jsonb not null default '{}'::jsonb,
  confidence numeric(5,4) not null default 0,
  note text,
  unique(lot_id,source_type,source_url)
);

alter table public.lot_provenance enable row level security;
revoke all on table public.lot_provenance from anon, authenticated;
create index if not exists ix_lot_provenance_lot on public.lot_provenance(lot_id,observed_at desc);
