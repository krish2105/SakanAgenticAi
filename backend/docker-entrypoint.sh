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

# Safe to run on boot -- even the smallest free tier -- whenever GEMINI_API_KEY
# is set: app/embeddings.py's GeminiEmbedder calls Google's free embedding API
# over the network instead of loading sentence-transformers/torch in-process,
# so there's no local model weights and no RAM spike. Without a Gemini key,
# ingestion falls back to the local model, which commonly exceeds a 512MB
# free-tier container and gets the *entire container* OOM-killed by the
# platform from outside (not a graceful failure this script's `|| echo ...`
# can catch) -- so that path stays opt-in only via RUN_REGULATIONS_INGEST_ON_BOOT.
if [ -n "${GEMINI_API_KEY:-}" ] || [ "${RUN_REGULATIONS_INGEST_ON_BOOT:-false}" = "true" ]; then
  echo "Ingesting regulatory corpus into Qdrant (best-effort)..."
  python scripts/ingest_regulations.py --regulations-dir /regulations --qdrant-url "${QDRANT_URL:-http://localhost:6333}" \
    || echo "Regulations ingestion failed or Qdrant unreachable -- Compliance Agent will fall back to 'unable to verify' until this succeeds."
else
  echo "Skipping regulations ingest on boot -- no GEMINI_API_KEY (free, no local RAM cost -- would auto-enable this) and RUN_REGULATIONS_INGEST_ON_BOOT unset (would force the RAM-heavy local-model path)."
  echo "Run it once separately instead: locally with 'python scripts/ingest_regulations.py --regulations-dir ../regulations --qdrant-url \$QDRANT_URL --qdrant-api-key \$QDRANT_API_KEY', or via this repo's 'Re-ingest regulatory corpus' GitHub Actions workflow."
fi

echo "Starting API on port ${PORT:-8000}..."
# --proxy-headers + --forwarded-allow-ips="*" make uvicorn trust the platform's
# reverse proxy so request.client.host reflects the real caller (Render/most
# PaaS terminate TLS at a proxy). Safe here because only the platform proxy can
# reach the container; slowapi additionally keys off X-Forwarded-For directly.
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}" \
  --proxy-headers --forwarded-allow-ips="*"
