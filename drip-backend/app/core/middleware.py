"""
app/core/middleware.py
──────────────────────
Middleware stack (applied in order in main.py):
  1. SecurityHeadersMiddleware  — adds HTTP security headers to every response
  2. RequestIDMiddleware        — stamps each request with a unique ID
  3. ErrorBoundaryMiddleware    — safe pre-response failures inside outer headers
  4. LoggingMiddleware          — structured request/response logging
  5. RateLimitMiddleware        — fixed-window rate limiting via Redis
"""

from __future__ import annotations

import time
import uuid

import structlog
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.config import settings
from app.core.client_ip import client_ip
from app.core.error_responses import error_response, unexpected_error_response
from app.core.logging import get_logger

logger = get_logger(__name__)


class ErrorBoundaryMiddleware:
    """Catch pre-response failures inside request-ID, security and CORS wrappers."""

    def __init__(self, app: ASGIApp) -> None:
        """Store the configuration and dependencies used by ErrorBoundaryMiddleware."""
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Convert pre-response HTTP failures to API errors; propagate started-response
        failures.
        """
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        response_started = False

        async def tracked_send(message: Message) -> None:
            """Track response headers so the error boundary cannot send a second response."""
            nonlocal response_started
            if message["type"] == "http.response.start":
                response_started = True
            await send(message)

        try:
            await self.app(scope, receive, tracked_send)
        except Exception as exc:
            # A streaming/background failure cannot replace an already-started response.
            # Cancellation (BaseException) also deliberately propagates unchanged.
            if response_started:
                raise
            response = unexpected_error_response(Request(scope), exc)
            await response(scope, receive, send)


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
            "script-src 'self'; "
            "frame-src 'none'; "
            "frame-ancestors 'none';"
        ),
        "Cross-Origin-Opener-Policy": "same-origin",
    }

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        """Attach the configured security headers after downstream request handling."""
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
        """Bind a request ID to logging context and echo it in the response."""
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
        """Measure downstream request duration and emit structured request metadata."""
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
        """Resolve the client through the configured trusted-proxy policy for request logs."""
        return client_ip(request, settings.TRUSTED_PROXY_IPS) or "unknown"


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
    Fixed-window rate limiter backed by Redis.

    Key structure: drip:rl:{method}:{path_prefix}:{identifier}
    Identifier: user_id if authenticated, otherwise client IP.

    Returns 429 with Retry-After header when limit exceeded.
    Silently skips rate limiting if Redis is unavailable (fail-open).
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        """Apply the Redis rate rule, returning 429 when exhausted and allowing Redis
        outages.
        """
        # Skip health checks and OPTIONS (CORS preflight)
        if request.url.path == "/api/v1/health" or request.method == "OPTIONS":
            return await call_next(request)

        scope, limit, window = self._get_rule(request.method, request.url.path)
        identifier    = self._get_identifier(request)
        key           = f"drip:rl:{scope}:{identifier}"

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
            return error_response(
                request,
                status_code=429,
                code="RATE_LIMITED",
                message="Too many requests. Please wait and try again.",
                headers={
                    "Retry-After":            str(window),
                    "X-RateLimit-Limit":      str(limit),
                    "X-RateLimit-Remaining":  "0",
                    "X-RateLimit-Reset":      str(int(time.time()) + window),
                },
            )

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"]     = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(max(0, remaining))
        return response

    @staticmethod
    def _get_limit(method: str, path: str) -> tuple[int, int]:
        """Expose the selected rate limit and window without its Redis scope identifier."""
        _, limit, window = RateLimitMiddleware._get_rule(method, path)
        return limit, window

    @staticmethod
    def _get_rule(method: str, path: str) -> tuple[str, int, int]:
        """Choose the first matching method/path rule or the shared default rate window."""
        for rule_method, rule_path, limit, window in _RATE_LIMIT_RULES:
            method_match = not rule_method or method == rule_method
            if method_match and (path == rule_path or path.startswith(rule_path + "/")):
                return f"{rule_method or '*'}:{rule_path}", limit, window
        return "*:default", 200, 60

    @staticmethod
    def _get_identifier(request: Request) -> str:
        """Partition rate counters by authenticated user when available, otherwise trusted
        client IP.
        """
        # Only use an identity supplied by earlier trusted middleware. Route auth
        # dependencies run later, so the normal outer limiter is per client IP.
        user_id = getattr(request.state, "user_id", None)
        if user_id:
            return f"u:{user_id}"
        # Fall back to IP address
        ip = client_ip(request, settings.TRUSTED_PROXY_IPS) or "unknown"
        return f"ip:{ip}"

    @staticmethod
    async def _check(key: str, limit: int, window: int) -> tuple[bool, int]:
        """
        Increment the counter and return (allowed, remaining_requests).
        Redis MULTI/EXEC keeps INCR and initial expiry atomic. EXPIRE NX also
        repairs legacy counters missing a TTL without extending active windows.
        """
        from app.core.redis import get_redis
        redis = get_redis()

        async with redis.pipeline(transaction=True) as pipeline:
            pipeline.incr(key)
            pipeline.expire(key, window, nx=True)
            count, _ = await pipeline.execute()
        return count <= limit, limit - count
