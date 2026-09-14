"""
app/core/middleware.py
──────────────────────
Middleware stack (applied in order in main.py):
  1. SecurityHeadersMiddleware  — adds HTTP security headers to every response
  2. RequestIDMiddleware        — stamps each request with a unique ID
  3. LoggingMiddleware          — structured request/response logging
  4. RateLimitMiddleware        — sliding-window rate limiting via Redis
"""

from __future__ import annotations

import time
import uuid
from collections.abc import Callable

import structlog
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.types import ASGIApp

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


# ── 1. Security Headers ────────────────────────────────────────────────────────

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Adds HTTP security headers to every response.
    Headers defined in security architecture doc (34-security-architecture.md).
    """

    _HEADERS = {
        "X-Content-Type-Options":    "nosniff",
        "X-Frame-Options":           "DENY",
        "X-XSS-Protection":          "1; mode=block",
        "Referrer-Policy":           "strict-origin-when-cross-origin",
        "Permissions-Policy":        "camera=(), microphone=(), geolocation=()",
        "Strict-Transport-Security": "max-age=63072000; includeSubDomains; preload",
        "Content-Security-Policy": (
            "default-src 'self'; "
            "script-src 'self' https://js.stripe.com; "
            "frame-src https://js.stripe.com; "
            "frame-ancestors 'none';"
        ),
        "Cross-Origin-Opener-Policy": "same-origin",
    }

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        response = await call_next(request)
        for header, value in self._HEADERS.items():
            response.headers[header] = value
        return response


# ── 2. Request ID ─────────────────────────────────────────────────────────────

class RequestIDMiddleware(BaseHTTPMiddleware):
    """
    Stamps every request with a short unique ID.
    • Reads X-Request-ID header if provided by a proxy; generates one otherwise.
    • Stores the ID in request.state.request_id.
    • Echoes it back in the response header.
    • Binds it to the structlog context for the duration of the request.
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())[:12]
        request.state.request_id = request_id

        # Bind to structlog context (cleared automatically after request)
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id)

        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


# ── 3. Request Logging ────────────────────────────────────────────────────────

class LoggingMiddleware(BaseHTTPMiddleware):
    """
    Logs every request and response with timing information.
    Skips health check endpoint to avoid log spam.
    Never logs request bodies (may contain passwords or card numbers).
    """

    _SKIP_PATHS = {"/api/v1/health", "/favicon.ico"}

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if request.url.path in self._SKIP_PATHS:
            return await call_next(request)

        start_ns = time.perf_counter_ns()
        response = await call_next(request)
        duration_ms = (time.perf_counter_ns() - start_ns) / 1_000_000

        level = "warning" if response.status_code >= 400 else "info"
        getattr(logger, level)(
            "http.request",
            method=request.method,
            path=request.url.path,
            status=response.status_code,
            duration_ms=round(duration_ms, 2),
            client_ip=self._get_client_ip(request),
        )
        return response

    @staticmethod
    def _get_client_ip(request: Request) -> str:
        # Respect X-Forwarded-For if set by a trusted proxy (Railway injects this)
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"


# ── 4. Rate Limiting ──────────────────────────────────────────────────────────

# Map of (method_prefix, path_prefix) → (max_requests, window_seconds)
_RATE_LIMIT_RULES: list[tuple[str, str, int, int]] = [
    ("POST", "/api/v1/auth/login",            5,   300),   # 5 per 5 min per IP
    ("POST", "/api/v1/auth/register",         3,   3600),  # 3 per hour per IP
    ("POST", "/api/v1/auth/forgot-password",  3,   3600),  # 3 per hour per IP
    ("POST", "/api/v1/orders",                10,  60),    # 10 per min per user
    ("POST", "/api/v1/payments/callback",     100, 60),    # 100 per min per IP
    ("",     "/api/v1/admin",                 500, 60),    # 500 per min (admin)
    ("",     "/api/v1/seller",                200, 60),    # 200 per min (seller)
    ("GET",  "/api/v1",                       120, 60),    # 120 per min (public reads)
    ("",     "/api/v1",                       200, 60),    # 200 per min (all other)
]


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Sliding-window rate limiter backed by Redis.

    Key structure: drip:rl:{method}:{path_prefix}:{identifier}
    Identifier: user_id if authenticated, otherwise client IP.

    Returns 429 with Retry-After header when limit exceeded.
    Silently skips rate limiting if Redis is unavailable (fail-open).
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # Skip health checks and OPTIONS (CORS preflight)
        if request.url.path == "/api/v1/health" or request.method == "OPTIONS":
            return await call_next(request)

        limit, window = self._get_limit(request.method, request.url.path)
        identifier    = self._get_identifier(request)
        key           = f"drip:rl:{request.method}:{request.url.path[:50]}:{identifier}"

        try:
            allowed, remaining = await self._check(key, limit, window)
        except Exception:
            # Redis unavailable — fail open (don't block traffic)
            logger.warning("rate_limit.redis_unavailable", path=request.url.path)
            return await call_next(request)

        if not allowed:
            logger.warning(
                "rate_limit.exceeded",
                path=request.url.path,
                identifier=identifier,
                limit=limit,
                window=window,
            )
            return JSONResponse(
                status_code=429,
                content={
                    "error": {
                        "code":    "RATE_LIMITED",
                        "message": "Too many requests. Please wait and try again.",
                        "request_id": getattr(request.state, "request_id", None),
                    }
                },
                headers={
                    "Retry-After":            str(window),
                    "X-RateLimit-Limit":      str(limit),
                    "X-RateLimit-Remaining":  "0",
                    "X-RateLimit-Reset":      str(int(time.time()) + window),
                },
            )

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"]     = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(max(0, remaining - 1))
        return response

    @staticmethod
    def _get_limit(method: str, path: str) -> tuple[int, int]:
        for rule_method, rule_path, limit, window in _RATE_LIMIT_RULES:
            method_match = not rule_method or method == rule_method
            if method_match and path.startswith(rule_path):
                return limit, window
        return 200, 60  # Default

    @staticmethod
    def _get_identifier(request: Request) -> str:
        # Prefer user ID from token (set by auth dependency later in the chain)
        user_id = getattr(request.state, "user_id", None)
        if user_id:
            return f"u:{user_id}"
        # Fall back to IP address
        forwarded = request.headers.get("X-Forwarded-For")
        ip = forwarded.split(",")[0].strip() if forwarded else (
            request.client.host if request.client else "unknown"
        )
        return f"ip:{ip}"

    @staticmethod
    async def _check(key: str, limit: int, window: int) -> tuple[bool, int]:
        """
        Increment the counter and return (allowed, current_count).
        Uses Redis INCR + EXPIRE for atomic sliding-window behaviour.
        """
        from app.core.redis import get_redis
        redis = get_redis()

        count = await redis.incr(key)
        if count == 1:
            await redis.expire(key, window)
        return count <= limit, limit - count