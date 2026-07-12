"""Structured (JSON) logging + a request-id context that threads through every
log line of a request.

Kept dependency-free on purpose (no python-json-logger): a small Formatter
subclass emits one JSON object per line, which is what Render/Datadog/Loki want,
and a ContextVar carries the per-request id so pipeline logs emitted from a
worker thread can still be correlated back to the request that started them.

Call configure_logging() once at startup (app.main). Idempotent.
"""
from __future__ import annotations

import contextvars
import datetime as _dt
import json
import logging
import os

# Set by RequestIDMiddleware; read by the log filter below. Defaults to "-" for
# log lines emitted outside any request (startup, scheduled tasks).
request_id_ctx: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="-")

_CONFIGURED = False


class _RequestIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_ctx.get()
        return True


class JsonFormatter(logging.Formatter):
    """One JSON object per line. Includes the request id and, on error, the
    exception type/message/traceback."""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": _dt.datetime.fromtimestamp(record.created, _dt.timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
            "request_id": getattr(record, "request_id", "-"),
        }
        if record.exc_info:
            payload["exc_type"] = record.exc_info[0].__name__ if record.exc_info[0] else None
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def configure_logging() -> None:
    """Route the root logger (and uvicorn's) through the JSON formatter.

    LOG_LEVEL env var controls verbosity (default INFO). LOG_FORMAT=plain falls
    back to a human-readable formatter for local dev."""
    global _CONFIGURED
    if _CONFIGURED:
        return

    level = os.environ.get("LOG_LEVEL", "INFO").upper()
    plain = os.environ.get("LOG_FORMAT", "json").lower() == "plain"

    handler = logging.StreamHandler()
    handler.addFilter(_RequestIdFilter())
    if plain:
        handler.setFormatter(
            logging.Formatter("%(levelname)s [%(name)s] [%(request_id)s] %(message)s")
        )
    else:
        handler.setFormatter(JsonFormatter())

    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level)

    # uvicorn installs its own handlers; route them through ours so access and
    # error logs share the JSON format and request id.
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        lg = logging.getLogger(name)
        lg.handlers = []
        lg.propagate = True

    _CONFIGURED = True
