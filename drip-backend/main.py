"""
main.py
───────
FastAPI application factory for WearHowZ API.
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

from collections.abc import AsyncIterator
from contextlib import AsyncExitStack, asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException
from starlette.responses import Response

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.database import close_db, init_db
from app.core.error_responses import error_response, http_error_response, unexpected_error_response
from app.core.exceptions import DRIPException, RateLimitError
from app.core.log_privacy import scrub_sentry_event
from app.core.logging import configure_logging, get_logger
from app.core.middleware import (
    ErrorBoundaryMiddleware,
    LoggingMiddleware,
    RateLimitMiddleware,
    RequestIDMiddleware,
    SecurityHeadersMiddleware,
)
from app.core.redis import close_redis, init_redis
from app.schemas.common import ErrorResponse

logger = get_logger(__name__)


# ── Lifespan ──────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Manage startup and shutdown of shared resources."""
    # ── Startup ───────────────────────────────────────────────────────────────
    configure_logging()
    logger.info(
        "drip.startup",
        version=settings.APP_VERSION,
        environment=settings.ENVIRONMENT,
    )

    # Register cleanup before initialization: a failed connection check can
    # already have allocated a pool. The stack attempts both closures even if
    # another closure fails, and also runs on cancellation/startup failure.
    async with AsyncExitStack() as resources:
        resources.push_async_callback(close_redis)
        resources.push_async_callback(close_db)
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
                send_default_pii=False,
                include_local_variables=False,
                max_request_body_size="never",
                before_send=scrub_sentry_event,
                before_send_transaction=scrub_sentry_event,
            )
            logger.info("sentry.initialised")

        logger.info("drip.ready")
        try:
            yield
        finally:
            logger.info("drip.shutdown")
    logger.info("drip.stopped")


# ── Application factory ───────────────────────────────────────────────────────

def create_application() -> FastAPI:
    app = FastAPI(
            swagger_ui_parameters={"url": "/openapi.json"},

        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description=(
            "WearHowZ API — multi-vendor streetwear & casual fashion platform. "
            "Built on FastAPI + PostgreSQL + Redis."
        ),
        docs_url=settings.docs_url,
        redoc_url=settings.redoc_url,
        openapi_url="/openapi.json" if settings.is_development else None,
        lifespan=lifespan,
        # Global response codes shown in docs
        responses={
            status: {"description": description, "model": ErrorResponse}
            for status, description in {
                400: "Bad request", 401: "Unauthorized", 403: "Forbidden",
                404: "Not found", 405: "Method not allowed", 409: "Conflict",
                413: "Payload too large", 415: "Unsupported media type",
                422: "Validation or business rule error", 429: "Rate limited",
                500: "Internal server error", 502: "Upstream service error",
                503: "Service unavailable", 504: "Gateway timeout",
            }.items()
        },
    )

    # ── Middleware (applied in reverse registration order) ─────────────────────
    # Starlette uses LIFO order: the last registered wrapper runs first.

    # 4. Rate limiting (innermost — runs just before the handler)
    app.add_middleware(RateLimitMiddleware)

    # 3. Request logging
    app.add_middleware(LoggingMiddleware)

    # Convert unexpected route/inner-middleware failures before outer headers run.
    app.add_middleware(ErrorBoundaryMiddleware)

    # 2. Request ID stamping
    app.add_middleware(RequestIDMiddleware)

    # Security headers wrap normal and error-boundary responses; CORS is outside them.
    app.add_middleware(SecurityHeadersMiddleware)

    # CORS (must be added separately via add_middleware for correct ordering)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-Request-ID", "X-Guest-Token"],
        expose_headers=["X-Request-ID", "X-RateLimit-Remaining"],
    )

    # ── Routes ────────────────────────────────────────────────────────────────
    app.include_router(api_router, prefix=settings.API_PREFIX)

    # ── Exception handlers ────────────────────────────────────────────────────
    _register_exception_handlers(app)

    return app


def _register_exception_handlers(app: FastAPI) -> None:
    """Register global exception handlers that produce consistent error JSON."""

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException) -> Response:
        return http_error_response(request, exc)

    @app.exception_handler(DRIPException)
    async def drip_exception_handler(
        request: Request, exc: DRIPException
    ) -> JSONResponse:
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
        return error_response(
            request,
            status_code=exc.http_status,
            code=exc.code,
            message=exc.message,
            fields=exc.fields,
            headers=headers,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        """Convert Pydantic validation errors to DRIP error format."""
        fields: dict[str, str] = {}
        for error in exc.errors():
            location = error["loc"]
            if location and location[0] == "body":
                location = location[1:]
            loc = " → ".join(str(part) for part in location)
            fields[loc or "request"] = error["msg"]

        return error_response(
            request,
            status_code=422,
            code="VALIDATION_ERROR",
            message="Request validation failed. Please check the highlighted fields.",
            fields=fields,
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        """
        Catch-all for unexpected exceptions.
        Logs the full error but returns only a generic message to the client.
        """
        return unexpected_error_response(request, exc)


# ── Module entry point ────────────────────────────────────────────────────────
app: FastAPI = create_application()
