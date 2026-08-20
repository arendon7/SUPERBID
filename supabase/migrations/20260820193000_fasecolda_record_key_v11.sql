alter table public.fasecolda_values
  add column if not exists record_key text;

create unique index if not exists ux_fasecolda_record_key
  on public.fasecolda_values(record_key);

comment on column public.fasecolda_values.record_key is
  'Deterministic key for idempotent Fasecolda guide synchronization.';
