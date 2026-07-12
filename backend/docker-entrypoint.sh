#!/usr/bin/env bash
set -e

echo "Running database migrations (alembic upgrade head)..."
# Owns the schema in production. run_migrations.py adopts a pre-Alembic DB by
# stamping the baseline, so this is safe on the existing live database too.
# Fail hard here (no `|| true`): starting the API against an un-migrated schema
# would fail confusingly later -- better to fail the deploy loudly now.
python scripts/run_migrations.py

echo "Seeding synthetic demo dataset (idempotent, safe to re-run)..."
python scripts/seed_db.py --seed-dir seed_data || echo "seed_db.py failed -- continuing without re-seeding."

if [ "${RUN_REGULATIONS_INGEST_ON_BOOT:-false}" = "true" ]; then
  echo "Ingesting regulatory corpus into Qdrant (best-effort)..."
  python scripts/ingest_regulations.py --regulations-dir /regulations --qdrant-url "${QDRANT_URL:-http://localhost:6333}" \
    || echo "Regulations ingestion failed or Qdrant unreachable -- Compliance Agent will fall back to 'unable to verify' until this succeeds."
else
  # Off by default: sentence-transformers/torch during this step commonly
  # exceeds a 512MB free-tier container, and that's an OOM kill of the
  # *entire container* from outside (the OS/orchestrator, not this script),
  # which the `|| echo ...` fallback above can't catch -- it takes the
  # whole deploy down instead of just degrading the Compliance Agent to
  # its documented "unable to verify" fallback. Run the ingest once from
  # somewhere with more RAM instead: a local machine, or
  # .github/workflows/reingest-corpus.yml's workflow_dispatch trigger
  # (GitHub-hosted runners have several GB of RAM, no OOM risk there).
  echo "Skipping regulations ingest on boot (set RUN_REGULATIONS_INGEST_ON_BOOT=true to enable -- only safe on a plan with enough RAM for sentence-transformers/torch, not the smallest free tier)."
  echo "Run it once separately instead: locally with 'python scripts/ingest_regulations.py --regulations-dir ../regulations --qdrant-url \$QDRANT_URL --qdrant-api-key \$QDRANT_API_KEY', or via this repo's 'Re-ingest regulatory corpus' GitHub Actions workflow."
fi

echo "Starting API on port ${PORT:-8000}..."
# --proxy-headers + --forwarded-allow-ips="*" make uvicorn trust the platform's
# reverse proxy so request.client.host reflects the real caller (Render/most
# PaaS terminate TLS at a proxy). Safe here because only the platform proxy can
# reach the container; slowapi additionally keys off X-Forwarded-For directly.
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}" \
  --proxy-headers --forwarded-allow-ips="*"
