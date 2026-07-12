import os
import warnings

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
QDRANT_URL = os.environ.get("QDRANT_URL", "http://localhost:6333")
QDRANT_API_KEY = os.environ.get("QDRANT_API_KEY")  # required for Qdrant Cloud, unused for self-hosted

# ARCHITECTURE.md Section 3: Sonnet for Valuation/Compliance/Memo, Haiku for Query parsing.
QUERY_MODEL = os.environ.get("SAKAN_QUERY_MODEL", "claude-haiku-4-5-20251001")
REASONING_MODEL = os.environ.get("SAKAN_REASONING_MODEL", "claude-sonnet-5")

JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY")
if not JWT_SECRET_KEY:
    JWT_SECRET_KEY = "dev-only-insecure-secret-do-not-use-in-production"
    warnings.warn(
        "JWT_SECRET_KEY is not set; using a hardcoded dev-only value. "
        "Every deployed environment MUST set a real JWT_SECRET_KEY or issued "
        "tokens are forgeable by anyone who reads this source file.",
        stacklevel=2,
    )
JWT_ALGORITHM = "HS256"
JWT_ACCESS_TOKEN_EXPIRE_MINUTES = int(os.environ.get("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", 60 * 24 * 7))  # 7 days

# Comma-separated list of allowed frontend origins, e.g. "https://sakan.vercel.app,http://localhost:3000".
CORS_ORIGINS = [o.strip() for o in os.environ.get("CORS_ORIGINS", "http://localhost:3000").split(",") if o.strip()]

# Billing (Phase B). All optional -- billing_service degrades to "Stripe not
# configured" (501) responses rather than crashing the app when unset, same
# fallback pattern as ANTHROPIC_API_KEY. FRONTEND_URL is where Stripe Checkout
# redirects after success/cancel.
STRIPE_SECRET_KEY = os.environ.get("STRIPE_SECRET_KEY")
STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET")
STRIPE_PRICE_ID_PRO = os.environ.get("STRIPE_PRICE_ID_PRO")
STRIPE_PRICE_ID_TEAM = os.environ.get("STRIPE_PRICE_ID_TEAM")
FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:3000")

# WhatsApp Business Cloud API (Phase C). All optional -- see
# app/routers/whatsapp.py and README "WhatsApp" for what degrades to a
# no-op vs. what's required. Never verified against a real Meta account
# from this session (no credentials available in this sandbox).
WHATSAPP_VERIFY_TOKEN = os.environ.get("WHATSAPP_VERIFY_TOKEN")  # webhook subscription handshake
WHATSAPP_APP_SECRET = os.environ.get("WHATSAPP_APP_SECRET")  # verifies X-Hub-Signature-256
WHATSAPP_ACCESS_TOKEN = os.environ.get("WHATSAPP_ACCESS_TOKEN")  # Graph API bearer token
WHATSAPP_PHONE_NUMBER_ID = os.environ.get("WHATSAPP_PHONE_NUMBER_ID")  # the sending number's id

# Data source (Phase D). DATA_SOURCE selects which app/services/data_source.py
# provider is active; LICENSED_DATA_FEED_* are for a real data partnership,
# which doesn't exist yet -- see app/services/data_source.py and README
# "Data partnership".
DATA_SOURCE = os.environ.get("DATA_SOURCE", "synthetic")
LICENSED_DATA_FEED_URL = os.environ.get("LICENSED_DATA_FEED_URL")
LICENSED_DATA_FEED_API_KEY = os.environ.get("LICENSED_DATA_FEED_API_KEY")

# Off by default: sentence-transformers + its torch backend is enough on its
# own (a single resident instance, not even counting duplicates) to push a
# 512MB free-tier container over its memory limit -- observed as repeated
# "Ran out of memory" instance failures on Render's free plan even after
# fixing duplicate model loads. Both call sites (comps_service.semantic_rerank,
# compliance_agent's retrieve_clauses) already have documented, honest
# degraded-mode fallbacks (heuristic re-rank; "unable to verify — recommend
# manual RERA check") for exactly this case, so skipping the model entirely
# by default is safer than intermittently losing whole pipeline runs to OOM.
# Set to "true" on a plan with enough RAM to actually use semantic search.
ENABLE_SEMANTIC_EMBEDDINGS = os.environ.get("ENABLE_SEMANTIC_EMBEDDINGS", "false").lower() == "true"
