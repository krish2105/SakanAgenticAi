"""Request-scoped middleware: assign/propagate a request id and log one
structured access line per request (method, path, status, duration).
"""
from __future__ import annotations

import logging
import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.logging_config import request_id_ctx

log = logging.getLogger("sakan.access")

_REQUEST_ID_HEADER = "X-Request-ID"


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Reuses an inbound X-Request-ID (so a value assigned by an upstream proxy
    or the frontend survives), else mints one. Binds it to the logging
    ContextVar for the duration of the request and echoes it on the response so
    a client can quote it in a bug report."""

    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = request.headers.get(_REQUEST_ID_HEADER) or uuid.uuid4().hex
        token = request_id_ctx.set(request_id)
        start = time.perf_counter()
        status_code = 500
        try:
            response = await call_next(request)
            status_code = response.status_code
            response.headers[_REQUEST_ID_HEADER] = request_id
            return response
        finally:
            duration_ms = round((time.perf_counter() - start) * 1000, 1)
            # /healthz and /readyz are polled constantly by the platform; don't
            # flood logs with them.
            if request.url.path not in ("/healthz", "/readyz", "/health"):
                log.info(
                    "%s %s -> %s (%sms)",
                    request.method,
                    request.url.path,
                    status_code,
                    duration_ms,
                )
            request_id_ctx.reset(token)
