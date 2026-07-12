# Sakan AI

Agentic real-estate deal-intelligence platform for Dubai: a 5-node LangGraph
pipeline (Query → Comps → Valuation → Compliance RAG → Memo) behind a FastAPI
backend, with a Next.js command-deck UI that streams the agent trace live over
WebSocket. Full system design lives in [`ARCHITECTURE.md`](./ARCHITECTURE.md)
— start there for the product brief, design system, agent specs, and DB schema.

All phases in `ARCHITECTURE.md` Section 11 are built: dataset generation, the
regulatory RAG corpus, the agent pipeline, the API, and all five frontend
pages. See "Status" below for exactly what's been run and verified versus
what needs a real `ANTHROPIC_API_KEY` / Docker / Kaggle credentials to
exercise fully.

## Quickstart

```bash
# 1. Postgres + Qdrant
docker compose up -d

# 2. Backend
cd backend
pip install -r requirements.txt
export DATABASE_URL=postgresql+psycopg2://sakan:sakan@localhost:5432/sakan
export ANTHROPIC_API_KEY=sk-ant-...        # required for live agent reasoning
python scripts/seed_db.py --seed-dir seed_data          # synthetic demo data
python scripts/ingest_regulations.py --regulations-dir ../regulations \
  --qdrant-url http://localhost:6333
uvicorn app.main:app --reload

# 3. Frontend (separate terminal)
cd frontend
npm install
echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > .env.local
npm run dev
```

## Deploy to production (Render + Vercel)

Per `ARCHITECTURE.md` Section 3: frontend → Vercel, backend + Postgres + Qdrant
→ Docker Compose on Render (or Railway). This repo ships one-command configs
for both:

**Backend + Postgres + Qdrant (Render Blueprint):**
1. Render dashboard → New → Blueprint → point at this repo. Render reads
   [`render.yaml`](./render.yaml) and provisions `sakan-postgres`,
   `sakan-backend`, and `sakan-qdrant` in one step.
2. Set `ANTHROPIC_API_KEY` on the `sakan-backend` service (it's declared
   `sync: false` in the blueprint, so Render prompts for it rather than
   needing a value committed anywhere) — optional; every agent has a
   deterministic fallback and runs fine without it.
3. On boot, `backend/docker-entrypoint.sh` seeds the synthetic demo dataset
   and ingests the regulatory corpus into Qdrant automatically (both
   idempotent/best-effort — a failed ingest attempt logs and continues
   rather than blocking the API from starting).
4. Note the resulting public URL (e.g. `https://sakan-backend.onrender.com`).

**Frontend (Vercel):**
1. Vercel dashboard → New Project → import this repo → set **Root Directory**
   to `frontend/` (or run `vercel` from inside `frontend/` with the Vercel
   CLI — [`frontend/vercel.json`](./frontend/vercel.json) is already there).
2. Set the `NEXT_PUBLIC_API_URL` project env var to the Render backend URL
   from the step above.
3. Deploy.

**Honesty check on these deploy configs specifically:** they were written
carefully and match Render/Vercel's documented Blueprint/CLI conventions, but
could not be run end-to-end from this session — the sandbox's egress proxy is
allowlist-based (npm, PyPI, GitHub, `api.anthropic.com` only) and returns 403
on `vercel.com`, `render.com`, and even a plain `docker build` of
`backend/Dockerfile` (Docker Hub blob pulls are blocked here the same way the
`qdrant/qdrant` image pull was earlier). What *was* verified: the Dockerfile
and entrypoint script are syntactically valid (`bash -n`) and reviewed by
hand against the already-tested `seed_db.py`/`ingest_regulations.py` CLIs,
and `render.yaml`/`vercel.json` both parse as valid YAML/JSON. Treat the
Render service-to-service URL convention (`QDRANT_URL=http://sakan-qdrant:6333`)
as the one detail worth double-checking against Render's current docs before
relying on it, since that's the part with no local way to verify at all.

Open http://localhost:3000. Without `ANTHROPIC_API_KEY` set, the pipeline
still runs end-to-end — the Query Agent falls back to a default
`comps_search` classification and the Valuation/Memo agents fall back to
deterministic comp-median/state-assembled results (see "Status" below) — so
you can exercise the full data path with zero API cost before wiring in a key.

## Data sources

`ARCHITECTURE.md` Section 7 originally specified an entirely synthetic
`transactions.csv`. Two paths now exist for the `transactions` table:

1. **Default / demo path** — `backend/scripts/generate_dataset.py` produces
   synthetic `developers.csv`, `buildings.csv`, `off_plan_projects.csv`, and
   `transactions.csv` (committed under `backend/seed_data/`, ~600/80/20/15
   rows) with realistic Dubai community/building names and price
   distributions. `backend/scripts/seed_db.py` loads them into Postgres.
2. **Real-data path** — `backend/scripts/map_dld_columns.py` loads the
   **real** Dubai Land Department "Transactions" open dataset (published on
   Dubai Pulse), via a Kaggle mirror:
   [`alexefimik/dubai-real-estate-transactions-dataset`](https://www.kaggle.com/datasets/alexefimik/dubai-real-estate-transactions-dataset).
   `buildings`, `developers`, and `off_plan_projects` stay **synthetic** even
   on this path — the public DLD extract doesn't carry developer
   track-record, payment-plan, or escrow fields at the row level.

No claim is made that this project is affiliated with or endorsed by the
Dubai Land Department. The Kaggle dataset is a third-party mirror of DLD's
own public open-data release.

```bash
pip install kaggle
kaggle datasets download -d alexefimik/dubai-real-estate-transactions-dataset -p ./data --unzip
python backend/scripts/map_dld_columns.py --input ./data/transactions.csv
```

`map_dld_columns.py` renames DLD's native columns onto the `transactions`
schema, filters to residential sales only, drops known DLD placeholder-row
artifacts (1 AED considerations, sub-0.01 sqm sizes), dedupes, and
idempotently upserts buildings + transactions.

## Repo layout

```
ARCHITECTURE.md              # full master prompt / design doc (source of truth)
docker-compose.yml            # Postgres + Qdrant for local dev
backend/
  app/
    main.py                   # FastAPI app + router registration
    models.py                 # SQLAlchemy models matching Section 8
    deal_state.py              # DealState (Section 5.1)
    llm.py                     # Anthropic Messages API wrapper
    agents/                    # query / comps / valuation / compliance / memo nodes + graph.py
    rag/retrieval.py           # Qdrant retrieval for the Compliance Agent
    routers/                   # deals, comps, market, ws
    services/                  # comps_service, pipeline_runner, pdf, streaming
  scripts/
    generate_dataset.py        # synthetic demo dataset generator
    seed_db.py                 # loads seed_data/*.csv into Postgres
    map_dld_columns.py         # real-DLD-data adapter (alternative transactions path)
    ingest_regulations.py      # chunks + embeds regulations/*.md into Qdrant
  seed_data/                   # committed synthetic CSVs (demo-scale)
  tests/                       # 25 tests: agents, API, dataset, RAG ingestion, DLD adapter
data/                          # place a downloaded DLD/Kaggle CSV here (gitignored)
regulations/                   # 12 synthetic RERA/DLD-style regulatory docs (Section 6)
frontend/
  app/                         # Command Deck, Deal Result, Memo Viewer, Comps Explorer, Analytics
  components/                  # design system primitives, ticker, trace drawer, charts, map
  lib/                         # api.ts (backend client + demo-data fallback), types.ts
```

## Status — what's actually been verified

This was built and tested in a sandboxed environment with **outbound network
access restricted to an allowlist** (npm, PyPI, GitHub, api.anthropic.com —
not Hugging Face, Kaggle, Docker Hub, or arbitrary tile servers) and **no
`ANTHROPIC_API_KEY`**. That shaped what could be verified directly versus
what's implemented-but-unexercised:

**Verified for real, end-to-end, in this environment:**
- Backend: 25 tests pass (`cd backend && pytest tests/ -v`), covering every
  agent node, the full LangGraph pipeline (both the `comps_search`
  short-circuit and the `full_memo` path), the compliance citation-validation
  guardrail (including a hallucinated-citation rejection test), all 8 API
  endpoints, the WebSocket stream, and PDF export.
- A **real local Postgres 16** server (not just SQLite) was started, seeded,
  and queried through the live FastAPI app — confirmed with `curl` and via
  the browser.
- The **actual Next.js UI**, driven by a headless browser against the live
  FastAPI server: submitted a query through the real Command Deck, watched
  the Agent Trace drawer update live over the real WebSocket connection,
  and rendered real comps/valuation/compliance/memo data end-to-end. Both
  light and dark themes were screenshotted and checked.
- Qdrant ingestion's chunking/upsert/retrieval logic, verified against a
  **real in-memory Qdrant instance** (a genuine vector round-trip, not a
  mock) — but with a deterministic fake embedder standing in for
  `sentence-transformers`, since Hugging Face is not reachable from this
  sandbox to download model weights.

**Implemented but not exercised in this environment** (no credentials/network
here — these are standard, well-trodden integrations, not novel code, but
call this out rather than claim untested things work):
- Live Claude API calls (Query/Valuation/Compliance/Memo agent reasoning) —
  no `ANTHROPIC_API_KEY` was available. Every agent has a deterministic
  fallback so the pipeline still runs without one; set the key to get real
  LLM reasoning instead of the fallbacks.
- Real `sentence-transformers` embeddings — Hugging Face model download is
  blocked here; the ingestion/retrieval code path is correct and tested
  against a fake embedder, but hasn't downloaded and run the actual model.
- OpenStreetMap tile imagery on the Comps Explorer map — `tile.openstreetmap.org`
  is blocked by this sandbox's proxy. Markers render at correct positions;
  only the base map tiles are unverified visually.
- The real Kaggle DLD dataset — no Kaggle credentials here; `map_dld_columns.py`
  is tested against a fixture CSV built to match the real DLD/Dubai Pulse
  column schema (confirmed via public documentation), not the live 1M+-row file.
- `docker compose up` for Qdrant specifically — the image pull is blocked by
  this sandbox's Docker registry proxy; Postgres pulled and ran fine.
- Actual deployment to Vercel/Railway (Section 3's target) — this session has
  no hosting credentials, so nothing is deployed to a public URL. Everything
  above was verified locally in the sandbox instead.

**Known accessibility gap:** two of the exact hex values specified in
`ARCHITECTURE.md` Section 4.3 — `--accent-brass` on light-mode surfaces
(3.6:1) and `--negative` on dark-mode surfaces (3.9:1) — clear WCAG AA's 3:1
"large text/UI component" threshold but fall short of the 4.5:1 normal-text
threshold in a couple of small-text contexts (badges, ticker). Flagging
rather than silently deviating from the spec'd palette, since Section 0
explicitly says implement the token system as given.

## Ethics & limitations

See `ARCHITECTURE.md` Section 14 (updated) for the full list. In short: all
regulatory documents are synthetic (styled after real RERA/DLD structures,
not copied from them); the default transaction dataset is synthetic;
buildings/developers/off-plan enrichment data is synthetic even when real DLD
transactions are loaded; and any valuation the pipeline produces is a
demonstration of method, not a certified appraisal.
