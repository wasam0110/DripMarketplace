"""
app/api/v1/health.py
─────────────────────
Health check endpoint used by Railway's health monitor.
Returns status of database and Redis connections.
Not rate-limited. Not logged (filtered in middleware).
"""

import asyncio
from contextlib import aclosing

from fastapi import APIRouter, Response
from sqlalchemy import text

from app.core.config import settings
from app.core.database import get_db
from app.core.redis import get_redis
from app.schemas.common import HealthResponse

router = APIRouter(tags=["health"])


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Platform health check",
    include_in_schema=settings.is_development,
)
async def health_check(response: Response) -> HealthResponse:
    """
    Returns OK if both the database and Redis are reachable.
    Used by Railway uptime monitoring and load balancer health checks.
    """
    db_status    = "ok"
    redis_status = "ok"

    # Database ping
    try:
        async with asyncio.timeout(3), aclosing(get_db()) as sessions:
            async for session in sessions:
                await session.execute(text("SELECT 1"))
                break
    except Exception:
        db_status = "error"

    # Redis ping
    try:
        async with asyncio.timeout(3):
            await get_redis().ping()
    except Exception:
        redis_status = "error"

    overall = "ok" if db_status == "ok" and redis_status == "ok" else "degraded"
    response.status_code = 200 if overall == "ok" else 503

    return HealthResponse(
        status=overall,
        database=db_status,
        redis=redis_status,
        version=settings.APP_VERSION,
        environment=settings.ENVIRONMENT,
    )
