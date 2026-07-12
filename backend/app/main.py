from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import comps, deals, market, ws

app = FastAPI(
    title="Sakan AI",
    description="Agentic real-estate deal-intelligence API for Dubai (see ARCHITECTURE.md).",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # portfolio demo scope; tighten for a real deployment
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(deals.router)
app.include_router(comps.router)
app.include_router(market.router)
app.include_router(ws.router)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
