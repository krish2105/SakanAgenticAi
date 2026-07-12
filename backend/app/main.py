from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.config import CORS_ORIGINS
from app.routers import auth, billing, comps, deals, market, whatsapp, ws
from app.routers.deals import limiter

app = FastAPI(
    title="Sakan AI",
    description="Agentic real-estate deal-intelligence API for Dubai (see ARCHITECTURE.md).",
    version="0.1.0",
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,  # set via CORS_ORIGINS env var; defaults to localhost dev only
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(billing.router)
app.include_router(deals.router)
app.include_router(comps.router)
app.include_router(market.router)
app.include_router(whatsapp.router)
app.include_router(ws.router)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
