"""
app/core/logging.py
───────────────────
Structured JSON logging via structlog.

Rules (from security architecture):
  • Never log: passwords, card numbers, JWT tokens, payment secrets, raw PII.
  • In production: JSON to stdout (Railway captures and forwards to log aggregator).
  • In development: human-readable coloured output.
  • Every log line carries: timestamp, level, event, request_id, environment.
"""

import logging
import sys
from typing import Any

import structlog
from structlog.types import EventDict, WrappedLogger

from app.core.config import settings


# ── PII scrubber ──────────────────────────────────────────────────────────────
_SENSITIVE_KEYS = frozenset({
    "password", "password_hash", "token", "access_token", "refresh_token",
    "jwt", "secret", "api_key", "apikey", "authorization",
    "card_number", "cvv", "cvc", "integrity_salt", "hash_key",
    "private_key", "service_role_key", "totp_secret",
})


def _scrub_sensitive(
    logger: WrappedLogger,
    method: str,
    event_dict: EventDict,
) -> EventDict:
    """Remove sensitive fields from log events before they are written."""
    for key in list(event_dict.keys()):
        if key.lower() in _SENSITIVE_KEYS:
            event_dict[key] = "[REDACTED]"
    return event_dict


# ── Shared processors ─────────────────────────────────────────────────────────
_shared_processors: list[Any] = [
    structlog.contextvars.merge_contextvars,
    structlog.stdlib.add_log_level,
    structlog.stdlib.add_logger_name,
    structlog.processors.TimeStamper(fmt="iso", utc=True),
    structlog.processors.StackInfoRenderer(),
    _scrub_sensitive,
    structlog.processors.dict_tracebacks,
]


def configure_logging() -> None:
    """Call once at application startup."""
    log_level = logging.DEBUG if settings.is_development else logging.INFO

    if settings.is_development:
        # Human-readable coloured output in dev
        renderer = structlog.dev.ConsoleRenderer(colors=True)
    else:
        # Machine-parseable JSON in staging/production
        renderer = structlog.processors.JSONRenderer()

    structlog.configure(
        processors=[
            *_shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        wrapper_class=structlog.BoundLogger,
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=_shared_processors,
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.handlers = [handler]
    root_logger.setLevel(log_level)

    # Quiet noisy third-party loggers
    for name in ("uvicorn.access", "sqlalchemy.engine", "asyncpg"):
        logging.getLogger(name).setLevel(
            logging.WARNING if not settings.is_development else logging.INFO
        )


def get_logger(name: str = __name__) -> structlog.BoundLogger:
    return structlog.get_logger(name)


# Module-level logger for use within this package
logger = get_logger(__name__)