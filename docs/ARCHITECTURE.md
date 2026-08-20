# Architecture

```text
Superbid public pages
        |
        v
Playwright + public XHR/JSON observation
        |
        v
SQLite durable capture buffer
        |                 \
        |                  -> peritajes / bid history / provenance
        v
Supabase central replica
        |
        +--> historical valuation
        +--> Fasecolda
        +--> Mercado Libre comparables
        +--> max-bid / ROI / score
        v
FastAPI + dashboard + CSV/XLSX
```

## Data integrity

The system keeps these values distinct:
- opening bid;
- current/last observed bid;
- observed closing price;
- confirmed adjudication price.

`SOLD_CONFIRMED` is reserved for explicit sale/adjudication evidence.

## Resilience

SQLite remains the write-first capture buffer. Supabase is a central analytical replica. A transient upstream or Supabase outage therefore does not need to lose an auction snapshot.
