import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.config import CORS_ORIGINS
from app.logging_config import configure_logging, request_id_ctx
from app.middleware import RequestIDMiddleware
from app.observability import check_readiness, init_sentry
from app.ratelimit import limiter
from app.routers import admin, auth, billing, comps, deals, market, whatsapp, ws

configure_logging()
init_sentry()
log = logging.getLogger("sakan.main")

app = FastAPI(
    title="Sakan AI",
    description="Agentic real-estate deal-intelligence API for Dubai (see ARCHITECTURE.md).",
    version="0.1.0",
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# RequestIDMiddleware is added last so it runs first (outermost) -- every
# request, including CORS preflight, gets an id bound before anything else logs.
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,  # set via CORS_ORIGINS env var; defaults to localhost dev only
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID"],
)
app.add_middleware(RequestIDMiddleware)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch-all: log the full traceback (with the request id, via the logging
    context) and return a clean JSON 500 instead of leaking internals. Sentry,
    if enabled, captures the exception through its own integration."""
    log.exception("Unhandled error on %s %s", request.method, request.url.path)
    # The 500 handler runs in Starlette's ServerErrorMiddleware, which sits
    # above RequestIDMiddleware, so set the correlation header here directly.
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
        headers={"X-Request-ID": request_id_ctx.get()},
    )


app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(billing.router)
app.include_router(deals.router)
app.include_router(comps.router)
app.include_router(market.router)
app.include_router(whatsapp.router)
app.include_router(ws.router)


@app.get("/healthz")
@app.get("/health")  # kept as an alias -- render.yaml's healthCheckPath points here
async def healthz() -> dict:
    """Liveness: is the process up and serving. Deliberately does NOT touch
    the database or Qdrant, so a cold dependency never fails the platform's
    health check (and thus never triggers a restart loop)."""
    return {"status": "ok"}


@app.get("/readyz")
async def readyz() -> JSONResponse:
    """Readiness: can we serve real traffic. Checks the database (hard
    dependency) plus Redis/Qdrant (reported, not gating). 503 if not ready."""
    ok, checks = check_readiness()
    return JSONResponse(status_code=200 if ok else 503, content={"ready": ok, "checks": checks})
