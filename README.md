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
export JWT_SECRET_KEY=$(openssl rand -hex 32)   # required -- see Auth section below
export ANTHROPIC_API_KEY=sk-ant-...             # optional, required for live agent reasoning
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

Open http://localhost:3000, create an account, and ask a deal question.
Without `ANTHROPIC_API_KEY` set, the pipeline still runs end-to-end — the
Query Agent falls back to a default `comps_search` classification and the
Valuation/Memo agents fall back to deterministic comp-median/state-assembled
results (see "Status" below) — so you can exercise the full data path with
zero API cost before wiring in a key.

## Auth

Every deal-pipeline endpoint requires a signed-in account (see the MVP
roadmap's Phase A: a `deal_queries` row readable by guessable integer ID was
the first thing fixed once real users entered the picture). `/comps` and
`/market/*` stay open with no login, matching a free-trial comps-search tier.

- `POST /auth/register`, `POST /auth/login` return a JWT; send it as
  `Authorization: Bearer <token>` on every `/deals/*` request.
- The WS stream can't carry custom headers from a browser, so it takes the
  token as a query param instead: `/ws/deals/{id}/stream?token=...`.
- **`JWT_SECRET_KEY` is required in any environment real users touch.**
  Without it the app falls back to a hardcoded dev-only value and prints a
  warning on startup — every token it issues is forgeable by anyone who
  reads `backend/app/config.py`. Generate a real one with `openssl rand -hex 32`.
- `POST /deals/query` is rate-limited to 10 requests/minute per client (it's
  the endpoint that spends Anthropic budget per call).

## Deploy to production (Render + Neon + Qdrant Cloud + Vercel)

Per `ARCHITECTURE.md` Section 3: frontend → Vercel, backend → Render. Postgres
and Qdrant both run on external free tiers rather than Render-managed, to
stay at $0: **Neon** for Postgres (Render allows only one free-tier Postgres
per account, and that slot may already be spoken for by another project) and
**Qdrant Cloud** for the vector DB (Render's free tier has no Private
Services, which a non-public vector DB needs). Do these in order — each step
needs a value produced by the one before it.

### 1. Neon (Postgres) — ~2 min

1. Sign up at https://neon.tech (free tier: no card required as of this
   writing — confirm current terms on their pricing page).
2. Create a project. Neon gives you a **connection string** immediately,
   something like `postgresql://user:password@ep-xxxx.neon.tech/dbname?sslmode=require`.
3. Copy it. (The app normalizes `postgresql://` → `postgresql+psycopg2://`
   automatically — paste Neon's string exactly as given, don't edit it.)

### 2. Qdrant Cloud (vector DB) — ~3 min

1. Sign up at https://cloud.qdrant.io (free tier: 1 GB cluster, no card
   required as of this writing — confirm current terms on their pricing page).
2. Create a cluster. Note its **Cluster URL** (`https://xxxxx.cloud.qdrant.io`,
   port `6333` included or appended).
3. Create an **API key** for that cluster. Copy it now — Qdrant Cloud shows
   it once.

### 3. Backend on Render — ~5 min

1. Push/merge this branch to whichever branch your Render deploy will track
   (Render Blueprints deploy from a specific branch — pick one and make sure
   it has `render.yaml` at the repo root).
2. Render dashboard → **New** → **Blueprint** → connect this GitHub repo →
   select that branch. Render parses [`render.yaml`](./render.yaml) and shows
   a plan: one **Web Service** (`sakan-backend`), free plan, no database
   (Postgres is external now — see step 1).
3. Before or after clicking **Apply**, fill in env vars on the
   `sakan-backend` service page. Render lists every `sync: false` var from
   `render.yaml` (18 of them as this repo has grown past just the core
   deploy — Stripe billing, WhatsApp, Redis, data-source options are all in
   there too); **only these four are required to get a working deploy**,
   everything else is optional and the app degrades gracefully without it
   (a startup warning, not a crash):
   - `DATABASE_URL` → the Neon connection string from step 1
   - `QDRANT_URL` → the Cluster URL from step 2
   - `QDRANT_API_KEY` → the API key from step 2
   - `JWT_SECRET_KEY` → **required for real users**, not just recommended —
     generate one with `openssl rand -hex 32`; without it every login token
     is forgeable by anyone who reads this repo's source (see "Auth" above)
   - `ANTHROPIC_API_KEY` → optional; leave blank to run entirely on
     deterministic fallbacks (no live LLM reasoning, but the full data path
     works)
   - Everything else (`CORS_ORIGINS`, `REDIS_URL`, `STRIPE_*`,
     `WHATSAPP_*`, `DATA_SOURCE`, `FRONTEND_URL`, `LICENSED_DATA_FEED_*`) —
     leave blank for a first deploy; come back to them per their own README
     sections (Billing, WhatsApp, Data partnership) once the core app is live.
4. Render builds `sakan-backend` from `backend/Dockerfile` (build context is
   the repo root, so it can also `COPY regulations/` in — don't rename or
   move that directory without updating the Dockerfile).
5. Watch the deploy log. On first boot, `backend/docker-entrypoint.sh` runs
   `seed_db.py` (loads the synthetic demo dataset into your Neon Postgres) —
   safe on any instance size. It does **not** run the regulations ingest
   automatically (`RUN_REGULATIONS_INGEST_ON_BOOT` defaults to `false`) —
   see the note below for why, and how to run it.
6. Once live, hit `https://<your-service>.onrender.com/health` — expect
   `{"status":"ok"}`. Then `https://<your-service>.onrender.com/market/ticker`
   should return real seeded transactions.
7. **Copy this backend URL.** You need it for step 4.

**Loading the compliance corpus (a separate step, by design):** `ingest_regulations.py`
loads `sentence-transformers`/PyTorch to embed the 12 regulatory docs, which
reliably exceeds Render's free-tier 512MB and gets the *entire container*
OOM-killed by the platform — not a graceful per-step failure the entrypoint
script's own error handling can catch, since the OS kills the whole process
tree from outside. Discovered by an actual failed deploy on this exact free
tier, not reasoned through in the abstract: the deploy log showed only
`Deploying...` / `Setting WEB_CONCURRENCY=1`, then Render's Events tab
reported `Ran out of memory (used over 512MB) while running your code`,
with no chance for the "ingestion failed, continuing" fallback message to
ever print. Two free ways to actually load it, neither needs a paid Render
plan:
- **Recommended:** add `QDRANT_URL`/`QDRANT_API_KEY` as repo secrets
  (Settings → Secrets and variables → Actions), then manually trigger
  [`.github/workflows/reingest-corpus.yml`](./.github/workflows/reingest-corpus.yml)
  (Actions tab → that workflow → "Run workflow") — GitHub-hosted runners have
  several GB of RAM, no OOM risk, and this workflow already exists for the
  weekly scheduled re-sync.
- Or run it from your own machine: `cd backend && pip install -r
  requirements.txt && python scripts/ingest_regulations.py --regulations-dir
  ../regulations --qdrant-url <your Qdrant Cloud URL> --qdrant-api-key <your key>`.

Until one of those runs at least once, the Compliance Agent responds in its
documented "unable to verify — recommend manual RERA check" fallback mode,
which is a real, intended state (not a crash) — the rest of the app
(comps, valuation, memo) works normally in the meantime.

Other notes that are easy to mistake for bugs: Render's *free* web service
plan spins down after ~15 min idle and takes 30-60s to wake on the next
request (the first Vercel-to-Render call after a quiet period will look
"hung" — it isn't); Neon's free tier auto-suspends an idle database and
takes a moment to wake, similar to
Render's cold start — stack the two and a truly cold first request could take
a while, which is expected, not a hang.

### 4. Frontend on Vercel (~3 min)

1. Vercel dashboard → **Add New** → **Project** → import this GitHub repo.
2. In the import screen's **Root Directory** field, set it to `frontend`
   (Vercel won't find `package.json` at the repo root otherwise — this is
   the single most common failure mode for monorepo imports like this one).
   Framework preset should auto-detect as Next.js; leave build/install
   commands as default ([`frontend/vercel.json`](./frontend/vercel.json)
   already pins them explicitly).
3. Add an environment variable: `NEXT_PUBLIC_API_URL` = the Render backend
   URL from step 3.7 (e.g. `https://sakan-backend.onrender.com`, **no
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
- **Compliance Agent always returns "unable to verify"**: expected until
  the regulations corpus has been ingested at least once — this doesn't
  happen automatically on Render's free tier (see "Loading the compliance
  corpus" above; a Render free-tier shell hits the same 512MB OOM risk as
  the boot-time ingest would). Trigger
  [`.github/workflows/reingest-corpus.yml`](./.github/workflows/reingest-corpus.yml)
  manually (Actions tab → "Run workflow", after adding `QDRANT_URL`/
  `QDRANT_API_KEY` as repo secrets), or run `ingest_regulations.py` from
  your own machine. If you've already done that and it's still failing,
  double check `QDRANT_URL`/`QDRANT_API_KEY` on the Render service match
  your Qdrant Cloud cluster exactly.

**Honesty check on this guide:** every step above matches Render/Vercel/Qdrant
Cloud's documented flows and was reasoned through carefully, but couldn't be
executed end-to-end from this session — its egress proxy is allowlist-based
(npm, PyPI, GitHub, `api.anthropic.com` only) and returns 403 on `vercel.com`,
`render.com`, `cloud.qdrant.io`, and even a plain `docker build` of
`backend/Dockerfile` against Docker Hub. What *was* verified locally: the
Dockerfile/entrypoint are syntactically valid, `render.yaml`/`vercel.json`
parse as valid YAML/JSON, and the `QDRANT_API_KEY` plumbing through
`build_qdrant_client`/`retrieve_clauses` is covered by the existing test
suite (56 passing). If you hit an error not covered above, it's genuinely
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
LEGAL_REVIEW.md               # checklist for the not-yet-real legal-partner engagement (Phase D)
docker-compose.yml            # Postgres + Qdrant for local dev
backend/
  app/
    main.py                   # FastAPI app + router registration
    models.py                 # SQLAlchemy models matching Section 8
    deal_state.py              # DealState (Section 5.1)
    llm.py                     # Anthropic Messages API wrapper
    agents/                    # query / comps / valuation / compliance / memo nodes + graph.py
    rag/retrieval.py           # Qdrant retrieval for the Compliance Agent
    routers/                   # auth, billing, deals, comps, market, whatsapp, ws
    services/                  # comps_service, pipeline_runner, pdf, streaming, billing_service, avm, data_source
  scripts/
    generate_dataset.py        # synthetic demo dataset generator
    seed_db.py                 # loads seed_data/*.csv into Postgres (--provenance flag, see "Data partnership")
    map_dld_columns.py         # real-DLD-data adapter (alternative transactions path)
    ingest_regulations.py      # chunks + embeds regulations/*.md into Qdrant
    purge_old_deal_queries.py  # PII retention enforcement (see "Data retention")
    migrate_billing_columns.py # one-off ALTER TABLE for pre-billing Postgres databases
    migrate_add_data_provenance.py # one-off ALTER TABLE for pre-provenance Postgres databases
    run_evals.py                # comps relevance / valuation accuracy / citation guardrail (see "Evals")
  seed_data/                   # committed synthetic CSVs (demo-scale)
  tests/                       # 85 tests: agents, AVM, data source, API, auth, billing, whatsapp, evals, dataset, RAG ingestion, DLD adapter
data/                          # place a downloaded DLD/Kaggle CSV here (gitignored)
regulations/                   # 12 synthetic RERA/DLD-style regulatory docs (Section 6)
frontend/
  app/                         # Command Deck, Deal Result, Memo Viewer, Comps Explorer, Analytics
  components/                  # design system primitives, ticker, trace drawer, charts, map
  lib/                         # api.ts (backend client + demo-data fallback), types.ts, i18n.ts
extension/                     # Chrome/Edge MV3 extension skeleton (Phase C) -- see extension/README.md
```

## Status — what's actually been verified

This was built and tested in a sandboxed environment with **outbound network
access restricted to an allowlist** (npm, PyPI, GitHub, api.anthropic.com —
not Hugging Face, Kaggle, Docker Hub, or arbitrary tile servers) and **no
`ANTHROPIC_API_KEY`**. That shaped what could be verified directly versus
what's implemented-but-unexercised:

**Verified for real, end-to-end, in this environment:**
- Backend: 85 tests pass (`cd backend && pytest tests/ -v`), covering every
  agent node, the full LangGraph pipeline (both the `comps_search`
  short-circuit and the `full_memo` path), the compliance citation-validation
  guardrail (including a hallucinated-citation rejection test), all 8 API
  endpoints, the WebSocket stream, PDF export, register/login/JWT auth, that
  a second account genuinely can't read a deal it doesn't own, rate limiting
  (drove a client past 10/min and confirmed a real 429, not just that the
  decorator is present), the PII purge script (dry-run vs. real delete,
  correct retention-window boundary, audit_log rows cleaned up alongside
  their parent), and billing (monthly quota enforcement blocking a Starter
  account's 6th full-pipeline query with a real 402, Stripe checkout/webhook
  wiring against a monkeypatched Stripe SDK, and a webhook signature-rejection
  test).
- Billing against the live stack, not just pytest: registered a real account
  through the actual `/billing` page, confirmed `0 / 5 full-pipeline queries
  this month` rendered from a real `/billing/me` call, clicked "Upgrade to
  Pro," and watched the frontend surface Stripe's real "not configured" 501
  as a clean on-page error — this is also how the billing-column schema-drift
  gap got caught and fixed (see `migrate_billing_columns.py` below) before it
  could repeat the `owner_id` incident.
- The eval suite (`python scripts/run_evals.py`) against the real seeded
  dataset: it's what caught the fixed +/-7% fallback-valuation band
  under-covering real held-out sale prices (4.4% band coverage) before this
  session ended, not after — see "Evals" below for the fix and the numbers.
- The Redis-backed WS pub/sub against a **real local Redis instance**, not a
  mock: a genuine publish → multi-subscriber fan-out round-trip, plus the
  full FastAPI app (real Postgres, real auth, real deal pipeline) streaming
  a complete trace over WS with `REDIS_URL` pointed at that instance — the
  actual code path that matters once the backend runs as more than one
  process, not just an isolated unit test of the pub/sub module.
- Real browser flow against the live stack: register → redirected home →
  submit a query while unauthenticated (redirects to `/login`) → register →
  land back on the original page → submit for real → watch the trace stream
  over an authenticated WebSocket → sign out → confirm the deal's direct URL
  now redirects to `/login` instead of leaking it. This is also how a real
  schema-drift bug got caught: the live Postgres instance had a `deal_queries`
  table from before `owner_id` existed, and `create_all()` doesn't alter
  existing tables — surfaced as an opaque browser CORS error (unhandled 500s
  don't carry CORS headers) before the real cause showed up in the server log.
  Worth knowing: this repo has no migration tool (Alembic) wired up yet, so a
  schema change like this needs a manual `ALTER TABLE`/table recreation
  against any already-deployed database, not just a fresh one.
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

## Data retention

`deal_queries.raw_query` and `deal_state` can contain user-entered PII
(buyer names, budgets, deal context) with no expiry by default — a real gap
flagged in the MVP roadmap, not something to leave undocumented.

- **Policy:** deal queries and their audit_log rows are retained for
  **180 days** by default (`PII_RETENTION_DAYS` env var to change it), then
  deleted. This is a starting point, not a researched compliance figure —
  confirm the right window against UAE PDPL requirements specifically before
  relying on it for real user data.
- **Enforcement:** [`backend/scripts/purge_old_deal_queries.py`](./backend/scripts/purge_old_deal_queries.py)
  does the deleting; [`.github/workflows/purge-pii.yml`](./.github/workflows/purge-pii.yml)
  runs it daily via GitHub Actions' `schedule` trigger. That workflow does
  nothing until you add a `DATABASE_URL` repo secret (Settings → Secrets and
  variables → Actions) pointing at the production database — it logs a
  warning and exits cleanly if that secret is missing, rather than failing
  the workflow run.
- Run `python scripts/purge_old_deal_queries.py --dry-run` locally to see
  what a given retention window would delete without deleting anything.
- Out of scope here: account deletion / "right to be forgotten" for the
  `users` table itself is a related but separate feature, not implemented.

## Billing

Phase B ("paid launch") of the MVP roadmap. Four tiers — Starter (free, 5
full-pipeline queries/mo), Pro (AED 299/mo, 50/mo), Team (AED 999/mo,
unmetered), Enterprise (custom, contact-sales only) — see
[`backend/app/services/billing_service.py`](./backend/app/services/billing_service.py)
for the canonical definitions. `/comps` search stays unmetered on every tier;
only `/deals/query` (the full 5-agent pipeline) is quota-gated, since that's
the endpoint that actually spends Anthropic budget per call.

- **Enable it:** set `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`,
  `STRIPE_PRICE_ID_PRO`, and `STRIPE_PRICE_ID_TEAM` (from your Stripe
  dashboard — Team's "per 5 seats" pricing-table language isn't modeled as
  seats here, it's a flat per-account price). Without these, `/billing/plans`
  and `/billing/me` still work (quota enforcement doesn't need Stripe at
  all), but `/billing/checkout` and `/billing/portal` return a clear `501`
  instead of crashing.
- **Never verified against a real Stripe account** — this sandbox has no
  network path to `api.stripe.com`. `backend/tests/test_billing.py` covers
  the checkout/webhook/quota logic against a monkeypatched `stripe` SDK; the
  live `/billing` page was exercised end-to-end in a real browser against the
  real backend (register → see quota → click upgrade → see Stripe's
  "not configured" 501 surface as a clean UI error), which is as far as this
  environment can verify it.
- **Existing deployments:** `users.tier`/`stripe_customer_id`/etc. are new
  columns; like the `owner_id` incident earlier in this project,
  `create_all()` won't add them to an already-deployed `users` table. Run
  `python scripts/migrate_billing_columns.py` once against any Postgres
  database that predates this change (idempotent, safe to re-run) — this
  session used it for real against its own sandbox Postgres before manually
  verifying `/billing` in the browser, which is exactly the schema-drift
  category the earlier incident should have made routine to check for.

## Evals

Phase B's "eval pipeline, not manual spot-checks" item. Turns the three
metrics the roadmap already names into a thresholded, scheduled check:
[`backend/scripts/run_evals.py`](./backend/scripts/run_evals.py), run weekly
by [`.github/workflows/evals.yml`](./.github/workflows/evals.yml) (and on
every push/PR touching an agent).

1. **Comps relevance** — every comp a scenario's SQL+rerank pipeline returns
   must actually match that scenario's filters (hard 100% invariant), and
   most scenarios should return at least one comp.
2. **Valuation accuracy** — real transactions held out of their own comp set;
   does the deterministic fallback valuation band (what the Valuation Agent
   uses without an LLM) actually bracket the real sale price.
3. **Citation guardrail** — a battery of adversarial (retrieved clauses, fake
   LLM response) pairs against the Compliance Agent's citation-validation
   guardrail; every response citing an unretrieved `clause_id` must be
   rejected (hard 100% invariant).

The first two metrics need no network access or secrets — they run against
the seeded synthetic dataset already committed to this repo. A fourth,
best-effort check tries the real retrieval path (embeds the regulatory corpus
into an in-memory Qdrant collection) to report retrieval coverage; it needs
the `sentence-transformers` model to be downloadable, so it degrades to
"skipped" rather than failing the run when it isn't (true in this sandbox;
usually not true on a GitHub Actions runner).

**Three real bugs this eval caught before they shipped**, each one only
visible by actually measuring against held-out real sales rather than
eyeballing the code:
1. The original fallback valuation used a fixed median ± 7% band. Run
   against this repo's own synthetic dataset, that band covered the real
   held-out sale price only **4.4%** of the time — intra-scenario price
   variance is much wider than a flat percentage assumes. Fixed by
   switching to a P25–P75 percentile band of the comps' own prices →
   **66.7%** coverage.
2. Adding the AVM (see "AVM" below) and multiplying its price/sqft
   estimate by the comps' *median* size_sqft actually made things worse —
   **13.3%** coverage. A "2BR" in this dataset ranges from a compact
   ~800 sqft to an elevated ~2,300 sqft layout; collapsing that to one
   median size threw away real size information the comps already
   carried.
3. Fixed by using the comps' P10–P90 size *range* instead of one median
   size — propagating both the AVM's own price/sqft uncertainty and the
   comps' size uncertainty into the final range → **88.9%** coverage, now
   the production fallback path. Full reasoning is in
   `valuation_agent._fallback_valuation`'s docstring.

Run `python scripts/run_evals.py` to see current numbers; thresholds and
the reasoning behind them (why width_ratio gates the range instead of
MAPE) are in the script's `THRESHOLDS` dict.

**LLM observability:** LangGraph pipelines trace to LangSmith automatically
when `LANGCHAIN_TRACING_V2=true`, `LANGCHAIN_API_KEY`, and `LANGCHAIN_PROJECT`
are set — no code change needed, since `langsmith` is already a transitive
dependency of `langgraph`. Not enabled/verified here (would need a LangSmith
account this session can't provision), but it's the "or similar" the roadmap
asks for, and it's a pure env-var flip when you have an account.

## AVM

Phase D's "an actual AVM layer... with the LLM reasoning layered on top for
explanation rather than doing the estimation itself."
[`backend/app/services/avm.py`](./backend/app/services/avm.py) fits a Ridge
regression (one-hot community + property_type, numeric bedrooms + the
subject building's avg_price_per_sqft) predicting **price per sqft** — not
absolute price, since a free-text query like "2BR in Dubai Marina" never
specifies the actual unit's size, and price/sqft is the one quantity
that's comparable across unit sizes.

- The Valuation Agent (`app/agents/valuation_agent.py`) trains/predicts
  this per query (a Ridge fit on a few hundred rows is milliseconds — not
  worth caching a model that would go stale or leak across databases in
  tests), passes the estimate to the LLM as a grounding anchor it's asked
  to reconcile against the comps, and — when there's no LLM — uses it
  directly as the deterministic fallback's primary estimate instead of the
  plain comp-percentile heuristic.
- Not real ML sophistication: ~600 rows across ~140
  community/type/bedroom combinations is not enough data to justify
  anything fancier than Ridge, and `MIN_TRAINING_ROWS = 30` means it
  simply declines to train (returns `None`, same graceful-degradation
  posture as everything else here) rather than fit something meaningless
  on real deployments with too little transaction history yet.
- Verified for real against the seeded dataset: `backend/tests/test_avm.py`
  checks a trained prediction lands within 20% of the real median for a
  known scenario (this is the test that caught bug #2 above), that unseen
  communities/missing fields return `None` instead of a garbage
  extrapolation, and that the agent-level integration actually prefers the
  AVM path when it's available.

## Localization (Arabic + RTL)

Phase C's "Arabic, for real this time... over 60% of the population speaks
Arabic day-to-day." [`frontend/lib/i18n.ts`](./frontend/lib/i18n.ts) holds
the dictionary; `LocaleProvider` (`components/locale-provider.tsx`) drives
`document.documentElement.lang`/`dir` and persists the choice to
`localStorage`. Toggle with the AR/EN button in the header.

- **Scoped to the app chrome** — nav, page headers/subtitles, buttons, the
  auth forms. Data pulled from the backend (community/building names,
  transaction figures, agent-generated memo text) stays as-is: those are
  proper nouns in Dubai real estate regardless of UI language, or would
  need the LLM prompts themselves localized, which is real future work,
  not something a UI toggle can fake.
- **RTL layout, not just translated strings** — Tailwind logical
  properties (`ps-`, `border-e`, etc.) throughout the chrome so the layout
  actually mirrors under `dir="rtl"`, not just the text.
- **A real bug this caught**: Recharts (the charting library) isn't
  RTL-aware — its horizontal-bar category-axis labels overlapped the bars
  under an inherited `dir="rtl"`, only visible by actually taking an
  Arabic-mode screenshot, not from reading the component code. Fixed by
  scoping all three chart containers to `dir="ltr"` explicitly, which is
  standard practice for numeric data visualizations inside an
  otherwise-RTL page, not a workaround.
- Verified with real headless-browser passes in both directions: Command
  Deck, Comps Explorer, Analytics, and the login form all screenshotted in
  Arabic with the nav rail, header, and cards correctly mirrored and zero
  console errors.

## Extension (Chrome/Edge, skeleton)

Phase C's "A Chrome extension or CRM plugin — surfacing a
valuation/compliance check inline on a listing page... beats a standalone
app for adoption." Lives in [`extension/`](./extension) — a Manifest V3
extension with its own README covering what's real vs. not in more detail
than fits here. Short version: popup-based comps search and full deal-query
submission both hit the real backend and were verified end-to-end by
actually loading the extension into headless Chromium (`--load-extension`)
and driving it — a real comps search, a real login, a real deal query that
created a real database row. It deliberately does not scrape listing pages
(bayut.com/propertyfinder.ae's real markup isn't accessible from this
sandbox to build a scraper against, and a guessed selector breaking
silently is worse than not extracting anything) — the floating button on
those sites is an entry point, not an auto-fill, today.

## Legal review (named legal partner)

Phase D's "a named legal/compliance partner... a RERA-licensed firm's name
attached to the corpus is the difference between 'AI guessed' and
'reviewed by counsel.'" This is infrastructure for that engagement, not
the engagement itself — no real firm has reviewed anything in this repo.
[`LEGAL_REVIEW.md`](./LEGAL_REVIEW.md) is the checklist for what a real
review looks like, clause by clause, and how it's recorded.

- Every regulatory document's frontmatter now carries `review_status`
  (`unreviewed` / `pending_review` / `reviewed`), `reviewed_by`, and
  `review_date` — all 12 docs are honestly `unreviewed` today.
  `ingest_regulations.py` refuses to mark a document `reviewed` without a
  named `reviewed_by` (a hard parse error, not a silent default).
- These fields ride the whole way to the Compliance Agent: every clause in
  `DealState.retrieved_clauses` carries its own review status, and
  `compliance_agent.UNREVIEWED_CORPUS_FLAG` gets attached to
  `compliance_flags` automatically whenever *none* of the retrieved
  clauses for that answer are reviewed — which, today, is always. The
  Compliance Card in the UI renders this as an explicit banner ("has not
  been reviewed by a licensed legal partner"), not a buried badge string.
- The moment a real firm reviews even one document and its frontmatter is
  updated + re-ingested, the flag clears automatically for answers
  grounded in that document's clauses — no code change needed, this was
  built to flip on its own once the underlying fact changes.
- Covered by tests: `backend/tests/test_ingest_regulations.py` (frontmatter
  parsing, the reviewed-without-reviewer guard) and
  `backend/tests/test_agents.py` (`_corpus_review_flag`'s three cases —
  none reviewed, one reviewed, empty retrieval).

## WhatsApp

Phase C's "~70% of real Dubai property inquiries arrive over WhatsApp; a
query-by-WhatsApp flow meets agents where they already work instead of
asking them to open a new tab." [`backend/app/routers/whatsapp.py`](./backend/app/routers/whatsapp.py)
implements the WhatsApp Business Cloud API's webhook contract: the GET
handshake Meta uses to verify webhook ownership, `X-Hub-Signature-256`
verification, and parsing inbound text messages out of Meta's documented
payload shape.

- **A message from a new phone number gets a pseudo-account
  auto-provisioned** (`whatsapp+<number>@sakan.internal`, an unusable
  random password) instead of requiring sign-up through the web app first
  — that's the point of meeting agents where they already work. That
  account still goes through the same `billing_service` quota as
  everyone else (Starter tier, 5 full-pipeline queries/month by default),
  no special-casing needed.
- On completion, the pipeline's result gets summarized and sent back over
  WhatsApp by subscribing to the same Redis/in-memory pub/sub channel the
  web UI's WebSocket stream already uses (`app/streaming.py`) — reused
  infrastructure, not a second notification system.
- **Never verified against a real Meta/WhatsApp Business account** — no
  such credentials exist in this sandbox. `backend/tests/test_whatsapp.py`
  (11 tests) covers everything that doesn't need one: the handshake,
  signature verification against a hand-built HMAC, payload parsing
  against a fixture matching Meta's documented shape, pseudo-account
  provisioning/reuse, and quota enforcement stopping a 6th webhook-driven
  query in the same month. The actual outbound call to
  `graph.facebook.com` has never round-tripped against Meta's servers.
- Set `WHATSAPP_VERIFY_TOKEN`, `WHATSAPP_APP_SECRET`,
  `WHATSAPP_ACCESS_TOKEN`, `WHATSAPP_PHONE_NUMBER_ID` from your Meta
  developer app to enable it; without them the GET handshake always 403s
  and the POST handler accepts unverified payloads (dev-only fallback,
  same posture as the Stripe webhook without `STRIPE_WEBHOOK_SECRET`).

## Data partnership

Phase D's "full DLD or portal data partnership... the exclusive or
first-mover data relationship that's hard for a competitor to replicate in
a weekend, unlike the agent orchestration." No such partnership exists —
this is the technical scaffolding for when one does, per the MVP roadmap's
risk #1 ("A valuation is only as defensible as its comps... this needs a
real answer before anything else matters").
[`backend/app/services/data_source.py`](./backend/app/services/data_source.py)
defines a `DataSourceProvider` interface with three implementations:

- `SyntheticDataSource` — this repo's default, wraps the committed seed CSVs.
- `DldKaggleDataSource` — wraps `map_dld_columns.py`'s output: real DLD/Dubai
  Pulse transaction data via a Kaggle mirror, which is real data but not a
  licensed partnership.
- `LicensedFeedDataSource` — a stub for an actual data partnership (DLD's
  official channel, a portal like Bayut/Property Finder, or a brokerage
  data-sharing agreement). Raises a clear error if selected without
  `LICENSED_DATA_FEED_URL` configured, rather than silently returning
  nothing or fabricating rows. **Never called against a real feed** — no
  such feed exists, so its HTTP-call shape is covered by a monkeypatched
  test, not a live integration.

Every `transactions` row carries a `data_provenance` column
(`synthetic` / `dld_kaggle` / `licensed_partner`) so any consumer can tell
which kind of number it's looking at — set automatically by `seed_db.py`'s
`--provenance` flag and hardcoded in `map_dld_columns.py`'s output.
Existing databases need
[`backend/scripts/migrate_add_data_provenance.py`](./backend/scripts/migrate_add_data_provenance.py)
run once (idempotent; backfills existing rows as `synthetic`) — same
schema-drift category as the earlier `owner_id` and billing-column
incidents, and this time caught and fixed *before* it could repeat: run
for real against this session's own sandbox Postgres (600 pre-existing
rows correctly backfilled to `synthetic`, confirmed via `psql` and a live
`/comps` query afterward), not just reasoned through.

When a real partnership exists, swapping it in is: implement
`LicensedFeedDataSource.fetch_transactions()` for the real API shape, set
`DATA_SOURCE=licensed_partner` + the feed credentials, done — no changes
to `comps_service.py`, the agents, or the API layer.

## Ethics & limitations

See `ARCHITECTURE.md` Section 14 (updated) for the full list. In short: all
regulatory documents are synthetic (styled after real RERA/DLD structures,
not copied from them); the default transaction dataset is synthetic;
buildings/developers/off-plan enrichment data is synthetic even when real DLD
transactions are loaded; and any valuation the pipeline produces is a
demonstration of method, not a certified appraisal.
