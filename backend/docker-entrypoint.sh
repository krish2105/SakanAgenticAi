#!/usr/bin/env bash
set -e

echo "Seeding synthetic demo dataset (idempotent, safe to re-run)..."
python scripts/seed_db.py --seed-dir seed_data || echo "seed_db.py failed -- continuing without re-seeding."

echo "Ingesting regulatory corpus into Qdrant (best-effort)..."
python scripts/ingest_regulations.py --regulations-dir /regulations --qdrant-url "${QDRANT_URL:-http://localhost:6333}" \
  || echo "Regulations ingestion failed or Qdrant unreachable -- Compliance Agent will fall back to 'unable to verify' until this succeeds."

echo "Starting API on port ${PORT:-8000}..."
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
