from unittest.mock import AsyncMock

import pytest

from app.core import database, redis
from app.tasks import worker


async def test_partial_startup_closes_both_resources(monkeypatch):
    monkeypatch.setattr(worker, "configure_logging", lambda: None)
    monkeypatch.setattr(database, "init_db", AsyncMock())
    monkeypatch.setattr(redis, "init_redis", AsyncMock(side_effect=RuntimeError("unavailable")))
    db_close, redis_close = AsyncMock(), AsyncMock()
    monkeypatch.setattr(database, "close_db", db_close)
    monkeypatch.setattr(redis, "close_redis", redis_close)
    with pytest.raises(RuntimeError, match="unavailable"):
        await worker.startup({})
    db_close.assert_awaited_once()
    redis_close.assert_awaited_once()


async def test_shutdown_closes_database_even_if_redis_close_fails(monkeypatch):
    db_close = AsyncMock()
    monkeypatch.setattr(database, "close_db", db_close)
    monkeypatch.setattr(redis, "close_redis", AsyncMock(side_effect=RuntimeError("close failed")))
    with pytest.raises(RuntimeError, match="close failed"):
        await worker.shutdown({})
    db_close.assert_awaited_once()
