create table if not exists public.auction_lots (
  id bigint generated always as identity primary key,
  source text not null default 'superbid_co',
  external_lot_id text not null,
  url text not null,
  title text,
  brand text,
  line text,
  version text,
  model_year integer,
  plate text,
  plate_is_partial boolean not null default false,
  mileage_km integer,
  engine_cc integer,
  fuel text,
  transmission text,
  drivetrain text,
  city text,
  seller text,
  initial_bid_cop bigint,
  first_seen_at timestamptz not null default now(),
  last_seen_at timestamptz not null default now(),
  unique(source, external_lot_id)
);

create table if not exists public.auction_snapshots (
  id bigint generated always as identity primary key,
  lot_id bigint not null references public.auction_lots(id) on delete cascade,
  observed_at timestamptz not null,
  displayed_price_cop bigint,
  displayed_price_label text,
  bid_count integer,
  status_text text,
  outcome text not null,
  closes_at_text text,
  closes_at timestamptz,
  evidence jsonb not null default '{}'::jsonb,
  unique(lot_id, observed_at)
);

create table if not exists public.auction_outcomes (
  lot_id bigint primary key references public.auction_lots(id) on delete cascade,
  outcome text not null,
  closing_price_observed_cop bigint,
  sale_price_confirmed_cop bigint,
  confidence numeric not null default 0 check (confidence >= 0 and confidence <= 1),
  confirmation_source text,
  notes text,
  updated_at timestamptz not null default now()
);

create table if not exists public.lot_attachments (
  id bigint generated always as identity primary key,
  lot_id bigint not null references public.auction_lots(id) on delete cascade,
  name text,
  url text not null,
  kind text not null,
  source text,
  discovered_at timestamptz not null default now(),
  unique(lot_id, url)
);

create table if not exists public.lot_bid_history (
  id bigint generated always as identity primary key,
  lot_id bigint not null references public.auction_lots(id) on delete cascade,
  sequence_no integer,
  amount_cop bigint not null,
  bid_at_text text,
  bid_at timestamptz,
  observed_at timestamptz not null default now(),
  unique(lot_id, amount_cop, bid_at_text)
);

create table if not exists public.market_comparables (
  id bigint generated always as identity primary key,
  lot_id bigint references public.auction_lots(id) on delete cascade,
  source text not null,
  external_id text,
  url text,
  observed_at timestamptz not null default now(),
  asking_price_cop bigint not null,
  brand text,
  line text,
  version text,
  model_year integer,
  mileage_km integer,
  city text,
  seller_type text,
  match_score numeric,
  raw_json jsonb,
  unique(source, external_id, observed_at)
);

create table if not exists public.fasecolda_values (
  id bigint generated always as identity primary key,
  source_file text not null,
  imported_at timestamptz not null default now(),
  code text,
  homologous_code text,
  brand text,
  vehicle_class text,
  reference1 text,
  reference2 text,
  reference3 text,
  service text,
  model_year integer not null,
  value_cop bigint not null
);

create table if not exists public.app_settings (
  key text primary key,
  value_json jsonb not null,
  updated_at timestamptz not null default now()
);

create table if not exists public.discovery_sources (
  id bigint generated always as identity primary key,
  url text not null unique,
  enabled boolean not null default true,
  source_type text not null default 'listing',
  last_scan_at timestamptz,
  last_error text,
  created_at timestamptz not null default now()
);

create table if not exists public.collection_queue (
  id bigint generated always as identity primary key,
  external_lot_id text not null unique,
  url text not null,
  status text not null default 'WATCH' check(status in ('WATCH','DONE','PAUSED')),
  next_run_at timestamptz not null default now(),
  last_run_at timestamptz,
  last_success_at timestamptz,
  consecutive_errors integer not null default 0,
  last_error text,
  closes_at_text text,
  closes_at timestamptz,
  priority integer not null default 100,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.collection_runs (
  id bigint generated always as identity primary key,
  run_type text not null,
  target text,
  started_at timestamptz not null default now(),
  finished_at timestamptz,
  ok boolean,
  lots_found integer not null default 0,
  lots_saved integer not null default 0,
  attachments_saved integer not null default 0,
  bids_saved integer not null default 0,
  error text
);

create index if not exists ix_auction_lots_vehicle on public.auction_lots(brand,line,model_year);
create index if not exists ix_auction_snapshots_lot_observed on public.auction_snapshots(lot_id,observed_at desc);
create index if not exists ix_auction_outcomes_outcome on public.auction_outcomes(outcome);
create index if not exists ix_attachments_lot_kind on public.lot_attachments(lot_id,kind);
create index if not exists ix_bid_history_lot on public.lot_bid_history(lot_id,sequence_no,observed_at);
create index if not exists ix_market_comparables_lot_observed on public.market_comparables(lot_id,observed_at desc);
create index if not exists ix_fasecolda_vehicle on public.fasecolda_values(brand,reference1,model_year);
create index if not exists ix_queue_due on public.collection_queue(status,next_run_at,priority);
create index if not exists ix_runs_started on public.collection_runs(started_at desc);

alter table public.auction_lots enable row level security;
alter table public.auction_snapshots enable row level security;
alter table public.auction_outcomes enable row level security;
alter table public.lot_attachments enable row level security;
alter table public.lot_bid_history enable row level security;
alter table public.market_comparables enable row level security;
alter table public.fasecolda_values enable row level security;
alter table public.app_settings enable row level security;
alter table public.discovery_sources enable row level security;
alter table public.collection_queue enable row level security;
alter table public.collection_runs enable row level security;

comment on table public.auction_lots is 'SUPERBID vehicle lots. Backend-only via service role/direct database.';
comment on table public.auction_snapshots is 'Observed auction price/status snapshots. A snapshot is not proof of sale.';
comment on table public.auction_outcomes is 'Confirmed or observed auction outcomes, preserving confidence and provenance.';
comment on table public.lot_bid_history is 'Publicly observable bid amounts/timestamps only; bidder identity is intentionally not stored.';
