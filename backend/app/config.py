import os
import warnings

# Deployment environment. "production" flips several dev-only conveniences into
# fail-closed behavior: a missing JWT secret, or an enabled-but-unverified
# Stripe/WhatsApp webhook, becomes a hard startup error instead of a silent
# insecure fallback (see _validate_production_config at the bottom of this file).
SAKAN_ENV = os.environ.get("SAKAN_ENV", "development").strip().lower()
IS_PRODUCTION = SAKAN_ENV == "production"

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
# Free-tier LLM fallback (Google AI Studio, no card required): used only when
# ANTHROPIC_API_KEY is unset, so a paid Anthropic key always wins on quality
# if both are configured. See app/llm.py for the provider dispatch.
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
QDRANT_URL = os.environ.get("QDRANT_URL", "http://localhost:6333")
QDRANT_API_KEY = os.environ.get("QDRANT_API_KEY")  # required for Qdrant Cloud, unused for self-hosted

# ARCHITECTURE.md Section 3: Sonnet for Valuation/Compliance/Memo, Haiku for Query parsing.
# Model *names* double as the provider dispatch key in app/llm.py (a
# "claude-"-prefixed model routes to Anthropic, "gemini-"-prefixed routes to
# Gemini) -- so which default applies here follows the same
# Anthropic-preferred-if-both-set precedence as the rest of this file.
if ANTHROPIC_API_KEY or not GEMINI_API_KEY:
    _DEFAULT_QUERY_MODEL = "claude-haiku-4-5-20251001"
    _DEFAULT_REASONING_MODEL = "claude-sonnet-5"
else:
    _DEFAULT_QUERY_MODEL = "gemini-2.5-flash"
    _DEFAULT_REASONING_MODEL = "gemini-2.5-flash"
QUERY_MODEL = os.environ.get("SAKAN_QUERY_MODEL", _DEFAULT_QUERY_MODEL)
REASONING_MODEL = os.environ.get("SAKAN_REASONING_MODEL", _DEFAULT_REASONING_MODEL)

JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY")
if not JWT_SECRET_KEY:
    if IS_PRODUCTION:
        raise RuntimeError(
            "JWT_SECRET_KEY must be set when SAKAN_ENV=production. Without it the app "
            "would fall back to a hardcoded dev secret, making every issued login token "
            "forgeable by anyone who can read this source. Generate one with "
            "`openssl rand -hex 32`."
        )
    JWT_SECRET_KEY = "dev-only-insecure-secret-do-not-use-in-production"
    warnings.warn(
        "JWT_SECRET_KEY is not set; using a hardcoded dev-only value. "
        "Every deployed environment MUST set a real JWT_SECRET_KEY or issued "
        "tokens are forgeable by anyone who reads this source file.",
        stacklevel=2,
    )
JWT_ALGORITHM = "HS256"
# Short-lived access token now that refresh tokens exist (Phase 3). The frontend
# silently refreshes on expiry; a leaked access token is only valid for an hour.
JWT_ACCESS_TOKEN_EXPIRE_MINUTES = int(os.environ.get("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", 60))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.environ.get("REFRESH_TOKEN_EXPIRE_DAYS", 30))
EMAIL_VERIFY_TOKEN_EXPIRE_HOURS = int(os.environ.get("EMAIL_VERIFY_TOKEN_EXPIRE_HOURS", 24))
PASSWORD_RESET_TOKEN_EXPIRE_HOURS = int(os.environ.get("PASSWORD_RESET_TOKEN_EXPIRE_HOURS", 1))

# Login brute-force protection (Phase 3).
MAX_FAILED_LOGINS = int(os.environ.get("MAX_FAILED_LOGINS", 5))
ACCOUNT_LOCKOUT_MINUTES = int(os.environ.get("ACCOUNT_LOCKOUT_MINUTES", 15))

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

# Cloudflare Turnstile (Phase 16): bot challenge on register/login. Optional --
# app/services/turnstile.py no-ops (accepts every token) when unset, same
# pattern as every other optional integration in this file. Free, unlimited
# challenges, no card (turnstile is a Cloudflare product, unrelated to fronting
# this app's traffic through Cloudflare's CDN/DNS).
TURNSTILE_SECRET_KEY = os.environ.get("TURNSTILE_SECRET_KEY")

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

# Dubai Pulse's official open-data API (Phase 12b) -- free, no partnership
# needed, just a registered account (dubaipulse.gov.ae -> request the
# "Transactions" dataset -> API Key/Secret arrive by email). Distinct from
# LICENSED_DATA_FEED_*: this is the government's own public dataset, not a
# paid/exclusive feed. See scripts/ingest_dld_open_api.py.
DLD_OPEN_DATA_API_KEY = os.environ.get("DLD_OPEN_DATA_API_KEY")
DLD_OPEN_DATA_API_SECRET = os.environ.get("DLD_OPEN_DATA_API_SECRET")

# Real DLD-derived transaction data via a RapidAPI marketplace listing (free
# tier, no Dubai Pulse business registration needed) -- see
# scripts/ingest_bayut_transactions.py. A different real-data path than the
# two above: a third party's resale of the same underlying DLD registry,
# not the government's own channel.
RAPIDAPI_KEY = os.environ.get("RAPIDAPI_KEY")

def _validate_production_config() -> None:
    """When SAKAN_ENV=production, refuse to boot with a webhook that's enabled
    but unverifiable. Both Stripe and WhatsApp webhooks fall back to accepting
    *unsigned* payloads when their signing secret is unset -- fine for local dev,
    but in production that's a forgeable-subscription-upgrade / forged-inbound-
    message hole. If the integration is configured at all, its signing secret
    becomes mandatory."""
    problems: list[str] = []

    if STRIPE_SECRET_KEY and not STRIPE_WEBHOOK_SECRET:
        problems.append(
            "STRIPE_WEBHOOK_SECRET is required because STRIPE_SECRET_KEY is set "
            "(otherwise /billing/webhook would accept unsigned, forgeable events)"
        )

    whatsapp_configured = any(
        [WHATSAPP_VERIFY_TOKEN, WHATSAPP_ACCESS_TOKEN, WHATSAPP_PHONE_NUMBER_ID]
    )
    if whatsapp_configured and not WHATSAPP_APP_SECRET:
        problems.append(
            "WHATSAPP_APP_SECRET is required because WhatsApp is configured "
            "(otherwise /whatsapp/webhook would accept unsigned, forged messages)"
        )

    if problems:
        raise RuntimeError(
            "Refusing to start in production (SAKAN_ENV=production) with insecure "
            "config:\n  - " + "\n  - ".join(problems)
        )


if IS_PRODUCTION:
    _validate_production_config()


# Master switch for semantic RAG (Compliance Agent citation retrieval +
# comps re-ranking). Historically off by default because the local
# sentence-transformers/torch backend alone is enough to push a 512MB
# free-tier container over its memory limit -- observed as repeated "Ran out
# of memory" instance failures on Render's free plan. That constraint no
# longer applies once GEMINI_API_KEY is set: app/embeddings.py's
# GeminiEmbedder calls Google's free embedding API over the network, with no
# local model weights and no RAM cost, so there's no reason to leave
# semantic RAG off in that case. Default therefore follows GEMINI_API_KEY;
# an explicit ENABLE_SEMANTIC_EMBEDDINGS=true/false always overrides it (e.g.
# to force the local model, or to disable semantic RAG even with a Gemini
# key on hand). Both call sites (comps_service.semantic_rerank,
# compliance_agent's retrieve_clauses) have documented, honest degraded-mode
# fallbacks (heuristic re-rank; "unable to verify — recommend manual RERA
# check") for whenever no provider is available.
_semantic_embeddings_raw = os.environ.get("ENABLE_SEMANTIC_EMBEDDINGS")
if _semantic_embeddings_raw is None:
    ENABLE_SEMANTIC_EMBEDDINGS = bool(GEMINI_API_KEY)
else:
    ENABLE_SEMANTIC_EMBEDDINGS = _semantic_embeddings_raw.strip().lower() == "true"
