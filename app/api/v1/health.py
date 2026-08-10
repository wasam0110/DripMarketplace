"""
app/api/v1/health.py
─────────────────────
Health check endpoint used by Railway's health monitor.
Returns status of database and Redis connections.
Not rate-limited. Not logged (filtered in middleware).
"""

from fastapi import APIRouter
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
async def health_check() -> HealthResponse:
    """
    Returns OK if both the database and Redis are reachable.
    Used by Railway uptime monitoring and load balancer health checks.
    """
    db_status    = "ok"
    redis_status = "ok"

    # Database ping
    try:
        async for session in get_db():
            await session.execute(text("SELECT 1"))
            break
    except Exception:
        db_status = "error"

    # Redis ping
    try:
        await get_redis().ping()
    except Exception:
        redis_status = "error"

    overall = "ok" if db_status == "ok" and redis_status == "ok" else "degraded"

    return HealthResponse(
        status=overall,
        database=db_status,
        redis=redis_status,
        version=settings.APP_VERSION,
        environment=settings.ENVIRONMENT,
    )