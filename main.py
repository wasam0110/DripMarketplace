"""
main.py
───────
FastAPI application factory for DRIP Marketplace API.

Startup sequence:
  1. Configure structured logging
  2. Initialise database connection pool
  3. Initialise Redis connection pool
  4. Register middleware (order matters — outermost applied last)
  5. Include API router
  6. Register global exception handlers

Shutdown sequence:
  1. Close database pool (drain in-flight queries)
  2. Close Redis pool
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.database import close_db, init_db
from app.core.exceptions import DRIPException, RateLimitError, ServerError
from app.core.logging import configure_logging, get_logger
from app.core.middleware import (
    LoggingMiddleware,
    RateLimitMiddleware,
    RequestIDMiddleware,
    SecurityHeadersMiddleware,
)
from app.core.redis import close_redis, init_redis

logger = get_logger(__name__)


# ── Lifespan ──────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage startup and shutdown of shared resources."""
    # ── Startup ───────────────────────────────────────────────────────────────
    configure_logging()
    logger.info(
        "drip.startup",
        version=settings.APP_VERSION,
        environment=settings.ENVIRONMENT,
    )

    await init_db()
    await init_redis()

    # Sentry initialisation (production only)
    if settings.SENTRY_DSN and settings.is_production:
        import sentry_sdk
        sentry_sdk.init(
            dsn=settings.SENTRY_DSN,
            environment=settings.ENVIRONMENT,
            release=f"drip-api@{settings.APP_VERSION}",
            traces_sample_rate=0.1,
        )
        logger.info("sentry.initialised")

    logger.info("drip.ready")
    yield

    # ── Shutdown ──────────────────────────────────────────────────────────────
    logger.info("drip.shutdown")
    await close_db()
    await close_redis()
    logger.info("drip.stopped")


# ── Application factory ───────────────────────────────────────────────────────

def create_application() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description=(
            "DRIP Marketplace API — multi-vendor streetwear & casual fashion platform. "
            "Built on FastAPI + PostgreSQL + Redis."
        ),
        docs_url=settings.docs_url,
        redoc_url=settings.redoc_url,
        openapi_url="/openapi.json" if settings.is_development else None,
        lifespan=lifespan,
        # Global response codes shown in docs
        responses={
            400: {"description": "Validation error"},
            401: {"description": "Unauthorized"},
            403: {"description": "Forbidden"},
            404: {"description": "Not found"},
            429: {"description": "Rate limited"},
            500: {"description": "Internal server error"},
        },
    )

    # ── Middleware (applied in reverse registration order) ─────────────────────
    # Note: Starlette applies middleware in LIFO order, so the first registered
    # is the outermost wrapper (last to run before the route handler).

    # 4. Rate limiting (innermost — runs just before the handler)
    app.add_middleware(RateLimitMiddleware)

    # 3. Request logging
    app.add_middleware(LoggingMiddleware)

    # 2. Request ID stamping
    app.add_middleware(RequestIDMiddleware)

    # 1. Security headers (outermost — always sets headers even on errors)
    app.add_middleware(SecurityHeadersMiddleware)

    # CORS (must be added separately via add_middleware for correct ordering)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
        expose_headers=["X-Request-ID", "X-RateLimit-Remaining"],
    )

    # ── Routes ────────────────────────────────────────────────────────────────
    app.include_router(api_router, prefix=settings.API_PREFIX)

    # ── Exception handlers ────────────────────────────────────────────────────
    _register_exception_handlers(app)

    return app


def _register_exception_handlers(app: FastAPI) -> None:
    """Register global exception handlers that produce consistent error JSON."""

    @app.exception_handler(DRIPException)
    async def drip_exception_handler(
        request: Request, exc: DRIPException
    ) -> JSONResponse:
        request_id = getattr(request.state, "request_id", None)
        if exc.http_status >= 500:
            logger.error(
                "drip.exception",
                code=exc.code,
                detail=exc.detail,
                path=request.url.path,
            )
        headers: dict[str, str] = {}
        if isinstance(exc, RateLimitError):
            headers["Retry-After"] = str(exc.retry_after)
        return JSONResponse(
            status_code=exc.http_status,
            content=exc.to_response(request_id),
            headers=headers,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        """Convert Pydantic validation errors to DRIP error format."""
        request_id = getattr(request.state, "request_id", None)
        fields: dict[str, str] = {}
        for error in exc.errors():
            loc = " → ".join(str(l) for l in error["loc"] if l != "body")
            fields[loc or "request"] = error["msg"]

        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code":       "VALIDATION_ERROR",
                    "message":    "Request validation failed. Please check the highlighted fields.",
                    "fields":     fields,
                    "request_id": request_id,
                }
            },
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        """
        Catch-all for unexpected exceptions.
        Logs the full error but returns only a generic message to the client.
        """
        request_id = getattr(request.state, "request_id", None)
        logger.exception(
            "drip.unhandled_exception",
            path=request.url.path,
            method=request.method,
            request_id=request_id,
            exc_info=exc,
        )
        server_error = ServerError()
        return JSONResponse(
            status_code=500,
            content=server_error.to_response(request_id),
        )


# ── Module entry point ────────────────────────────────────────────────────────
app: FastAPI = create_application()