# Sakan AI

Agentic real-estate deal-intelligence platform for Dubai, built around a 5-node
LangGraph pipeline (Query → Comps → Valuation → Compliance RAG → Memo). Full
system design lives in [`ARCHITECTURE.md`](./ARCHITECTURE.md) — start there for
the product brief, design system, agent specs, and DB schema.

This repo is being built out phase-by-phase per `ARCHITECTURE.md` Section 11.
The current commit lands the **transactions data pipeline**: a Postgres schema
matching Section 8, and an adapter that loads real DLD transaction records into
it.

## Data sources

`ARCHITECTURE.md` Section 7 originally specified an entirely synthetic
`transactions.csv`. That has been superseded: the `transactions` table is now
populated from the **real** Dubai Land Department "Transactions" open dataset
(published on Dubai Pulse), via a Kaggle mirror:
[`alexefimik/dubai-real-estate-transactions-dataset`](https://www.kaggle.com/datasets/alexefimik/dubai-real-estate-transactions-dataset).

- `buildings`, `developers`, and `off_plan_projects` remain **synthetic**, as
  originally specified — the public DLD transaction extract doesn't carry
  developer track-record, payment-plan, or escrow fields at the row level.
- No claim is made that this project is affiliated with or endorsed by the
  Dubai Land Department. The Kaggle dataset is a third-party mirror of DLD's
  own public open-data release.

### Loading the real transactions

```bash
# 1. Get the raw CSV (requires a free Kaggle account + API token)
pip install kaggle --break-system-packages
# place your kaggle.json API token in ~/.kaggle/
kaggle datasets download -d alexefimik/dubai-real-estate-transactions-dataset -p ./data --unzip

# 2. Bring up Postgres
docker compose up -d postgres

# 3. Install backend deps
pip install -r backend/requirements.txt --break-system-packages

# 4. Run the adapter
export DATABASE_URL=postgresql+psycopg2://sakan:sakan@localhost:5432/sakan
python backend/scripts/map_dld_columns.py --input ./data/transactions.csv
```

Add `--dry-run` to only print row counts (nothing written to Postgres) — useful
for sanity-checking a new export before loading it. Add `--limit N` to process
just the first N rows while iterating.

### What the adapter does (`backend/scripts/map_dld_columns.py`)

1. Reads the raw DLD CSV in chunks (the real extract is 1M+ rows).
2. Renames DLD's native columns (`trans_group_en`, `actual_worth`,
   `procedure_area`, `property_sub_type_en`, `rooms_en`, `reg_type_en`,
   `area_name_en`, `building_name_en`, ...) onto the `transactions` table
   fields from `ARCHITECTURE.md` Section 8. Column resolution is
   candidate-based (see `COLUMN_CANDIDATES`), so it tolerates minor header
   differences between the Dubai Pulse export and the Kaggle mirror.
3. Filters to **residential sale transactions only**: drops mortgages and
   gifts (`trans_group_en`), drops non-residential usage/subtypes (commercial,
   land, offices), and keeps only rows that map cleanly to Apartment, Villa,
   or Townhouse.
4. Drops known **DLD data-entry artifacts**: placeholder considerations
   (`actual_worth <= 1` AED) and placeholder unit sizes
   (`procedure_area < 0.01` sqm), plus rows with unparseable dates.
5. Deduplicates on the source transaction id (both within a chunk and across
   chunks).
6. Upserts a lightweight `buildings` row per (building/project name,
   community) so `transactions.building_id` resolves, then upserts the
   cleaned transactions — both upserts are `ON CONFLICT DO NOTHING`, so
   re-running the script against the same data is idempotent.

Run the test suite (uses a small fixture CSV shaped like the real DLD export,
and an in-memory-style SQLite DB, so it needs no network access or running
Postgres):

```bash
cd backend
pip install -r requirements.txt --break-system-packages
python -m pytest tests/ -v
```

## Repo layout

```
ARCHITECTURE.md          # full master prompt / design doc (source of truth)
docker-compose.yml        # Postgres + Qdrant for local dev
backend/
  app/
    models.py             # SQLAlchemy models matching ARCHITECTURE.md Section 8
    db.py                 # engine/session helpers (DATABASE_URL env var)
  scripts/
    map_dld_columns.py    # real-DLD-data adapter (this phase's deliverable)
  tests/
    test_map_dld_columns.py
    fixtures/dld_transactions_sample.csv
data/                      # place the downloaded DLD/Kaggle CSV here (gitignored)
regulations/               # synthetic RERA/DLD-style regulatory corpus (Section 6, WIP)
```

## Status

This is a portfolio project built phase-by-phase against `ARCHITECTURE.md`.
See Section 11 for the full phase plan and Section 18 for the submission
checklist. Remaining phases (LangGraph pipeline, RAG ingestion, FastAPI, and
the Next.js frontend) are not yet built.

## Ethics & limitations

- Real transaction data is used for the `transactions` table (see "Data
  sources" above); `buildings`/`developers`/`off_plan_projects` are synthetic
  and should not be treated as factual once those tables are populated.
- Valuation ranges the pipeline will produce (once the Valuation Agent phase
  lands) are a demonstration of method, not a certified appraisal.
- Regulatory documents in `regulations/` are written in the style of RERA/DLD
  forms for demonstration purposes and are not a substitute for current
  official RERA text or legal advice.
