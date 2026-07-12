import os

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
QDRANT_URL = os.environ.get("QDRANT_URL", "http://localhost:6333")

# ARCHITECTURE.md Section 3: Sonnet for Valuation/Compliance/Memo, Haiku for Query parsing.
QUERY_MODEL = os.environ.get("SAKAN_QUERY_MODEL", "claude-haiku-4-5-20251001")
REASONING_MODEL = os.environ.get("SAKAN_REASONING_MODEL", "claude-sonnet-5")
