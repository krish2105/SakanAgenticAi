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

Open http://localhost:3000. Without `ANTHROPIC_API_KEY` set, the pipeline
still runs end-to-end — the Query Agent falls back to a default
`comps_search` classification and the Valuation/Memo agents fall back to
deterministic comp-median/state-assembled results (see "Status" below) — so
you can exercise the full data path with zero API cost before wiring in a key.

## Deploy to production (Render + Vercel + Qdrant Cloud)

Per `ARCHITECTURE.md` Section 3: frontend → Vercel, backend + Postgres →
Render. Qdrant runs on **Qdrant Cloud's free tier** rather than self-hosted
on Render — Render's free tier has no Private Services (needed for a
non-public vector DB), and a public Docker-image web service for Qdrant has
port-binding behavior this session had no way to verify. Do these in order —
each step needs a value produced by the one before it.

### 1. Qdrant Cloud (~3 min)

1. Sign up at https://cloud.qdrant.io (free tier: 1 GB cluster, no card
   required as of this writing — confirm current terms on their pricing page).
2. Create a cluster. Note its **Cluster URL** (`https://xxxxx.cloud.qdrant.io`,
   port `6333` included or appended).
3. Create an **API key** for that cluster. Copy it now — Qdrant Cloud shows
   it once.

### 2. Backend + Postgres on Render (~5 min)

1. Push/merge this branch to whichever branch your Render deploy will track
   (Render Blueprints deploy from a specific branch — pick one and make sure
   it has `render.yaml` at the repo root).
2. Render dashboard → **New** → **Blueprint** → connect this GitHub repo →
   select that branch. Render parses [`render.yaml`](./render.yaml) and shows
   a plan: one **Web Service** (`sakan-backend`) and one **Postgres**
   database (`sakan-postgres`).
3. Click **Apply**. Render provisions Postgres first, then builds
   `sakan-backend` from `backend/Dockerfile` (build context is the repo
   root, so it can also `COPY regulations/` in — don't rename or move that
   directory without updating the Dockerfile).
4. The blueprint declares three env vars as `sync: false`, so Render will
   prompt you to fill them in on the `sakan-backend` service page:
   - `QDRANT_URL` → the Cluster URL from step 1
   - `QDRANT_API_KEY` → the API key from step 1
   - `ANTHROPIC_API_KEY` → optional (see the question below); leave blank to
     run entirely on fallbacks
5. `DATABASE_URL` is wired automatically (`fromDatabase` in the blueprint) —
   don't set it manually.
6. Watch the deploy log. On first boot, `backend/docker-entrypoint.sh` runs
   `seed_db.py` (loads the synthetic demo dataset into Postgres) and
   `ingest_regulations.py` (embeds the 12 regulatory docs into your Qdrant
   Cloud cluster) before starting `uvicorn`. Both are best-effort — a failure
   in either logs a warning and the API still starts — but check the log for
   `Upserted 57 clauses into Qdrant` to confirm the RAG corpus actually
   loaded; if that line is missing, the Compliance Agent will run in
   "unable to verify" fallback mode until you re-trigger a deploy.
7. Once live, hit `https://<your-service>.onrender.com/health` — expect
   `{"status":"ok"}`. Then `https://<your-service>.onrender.com/market/ticker`
   should return real seeded transactions.
8. **Copy this backend URL.** You need it for step 3.

Free-tier notes that are easy to mistake for bugs: the free Postgres instance
expires after 90 days (Render emails you before that — upgrade or recreate);
the free web service spins down after ~15 min idle and takes 30-60s to wake
on the next request (the first Vercel-to-Render call after a quiet period
will look "hung" — it isn't); free-tier RAM (512 MB) may be tight for
`sentence-transformers`/`torch` during the regulations-ingest step on first
boot — if step 6's log shows the ingest failing with an OOM-style error,
re-run it manually against a bigger instance, or temporarily bump the plan
for that one deploy.

### 3. Frontend on Vercel (~3 min)

1. Vercel dashboard → **Add New** → **Project** → import this GitHub repo.
2. In the import screen's **Root Directory** field, set it to `frontend`
   (Vercel won't find `package.json` at the repo root otherwise — this is
   the single most common failure mode for monorepo imports like this one).
   Framework preset should auto-detect as Next.js; leave build/install
   commands as default ([`frontend/vercel.json`](./frontend/vercel.json)
   already pins them explicitly).
3. Add an environment variable: `NEXT_PUBLIC_API_URL` = the Render backend
   URL from step 2.8 (e.g. `https://sakan-backend.onrender.com`, **no
   trailing slash**).
4. Deploy. Vercel builds and gives you a `https://<project>.vercel.app` URL.
5. Open it, submit a query on the Command Deck, and confirm the Agent Trace
   drawer updates live — this exercises the WebSocket connection end-to-end
   (browser → Vercel → your Render backend's `wss://` upgrade), which is the
   part most likely to need a second look if something's off.

### If something doesn't connect

- **Blank market snapshot / comps table, no errors in the browser console**:
  `NEXT_PUBLIC_API_URL` is likely wrong or missing a scheme (`https://`).
  `lib/api.ts`'s `safeGet` silently falls back to bundled demo data on any
  fetch failure by design, so a misconfigured API URL doesn't crash the
  page — it just quietly shows fake numbers. Check the Network tab for
  failed requests to confirm.
- **WebSocket never connects (trace drawer stuck on "connecting…")**: confirm
  the Render service is awake (free tier cold start, see above) and that
  `NEXT_PUBLIC_API_URL` doesn't have a trailing slash — `lib/api.ts` derives
  the `wss://` URL by string-replacing `http` with `ws` on that exact value.
- **CORS errors in the browser console**: shouldn't happen — `app/main.py`
  sets `allow_origins=["*"]` for this demo's scope — but if you've tightened
  that for your own deployment, make sure your Vercel domain is on the list.
- **Compliance Agent always returns "unable to verify"**: the regulations
  ingest either failed on boot (check the Render deploy log for the
  `Upserted 57 clauses` line) or `QDRANT_URL`/`QDRANT_API_KEY` are wrong.
  Re-run manually via a Render shell: `python scripts/ingest_regulations.py
  --regulations-dir /regulations`.

**Honesty check on this guide:** every step above matches Render/Vercel/Qdrant
Cloud's documented flows and was reasoned through carefully, but couldn't be
executed end-to-end from this session — its egress proxy is allowlist-based
(npm, PyPI, GitHub, `api.anthropic.com` only) and returns 403 on `vercel.com`,
`render.com`, `cloud.qdrant.io`, and even a plain `docker build` of
`backend/Dockerfile` against Docker Hub. What *was* verified locally: the
Dockerfile/entrypoint are syntactically valid, `render.yaml`/`vercel.json`
parse as valid YAML/JSON, and the `QDRANT_API_KEY` plumbing through
`build_qdrant_client`/`retrieve_clauses` is covered by the existing test
suite (25 passing). If you hit an error not covered above, it's genuinely
new information about a step this session couldn't verify — worth reporting
back so the guide can be corrected.

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
