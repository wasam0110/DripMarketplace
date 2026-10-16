"""Dependency failure must be visible to HTTP health probes, without leaking details."""

from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.api.v1 import health


@pytest.mark.parametrize(("db_fails", "redis_fails", "status"), [
    (False, False, 200), (True, False, 503), (False, True, 503), (True, True, 503),
])
async def test_health_status_and_session_cleanup(monkeypatch, db_fails, redis_fails, status):
    closed = []
    session = AsyncMock()
    session.execute.side_effect = ConnectionError("private database details") if db_fails else None

    async def sessions():
        try:
            yield session
        finally:
            closed.append(True)

    redis = AsyncMock()
    redis.ping.side_effect = ConnectionError("private redis details") if redis_fails else None
    monkeypatch.setattr(health, "get_db", sessions)
    monkeypatch.setattr(health, "get_redis", lambda: redis)
    app = FastAPI()
    app.include_router(health.router)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/health")
    assert response.status_code == status
    assert response.json()["status"] == ("ok" if status == 200 else "degraded")
    assert response.json()["database"] == ("error" if db_fails else "ok")
    assert response.json()["redis"] == ("error" if redis_fails else "ok")
    assert "private" not in response.text
    assert closed == [True]
