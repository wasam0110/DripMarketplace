"""Cache failure isolation, transaction cleanup, images and runtime settings."""

import io
from unittest.mock import AsyncMock, MagicMock

import pytest
from PIL import Image

from app.core import database, redis
from app.core.exceptions import BusinessRuleError
from app.services.image_service import ImageService


async def test_cache_round_trip_expiry_and_scoped_invalidation(isolated_redis):
    assert await redis.cache_set("test:one", "value", 60)
    assert await redis.cache_get("test:one") == "value"
    assert await isolated_redis.ttl("test:one") > 0
    await redis.cache_delete("test:one")
    assert await redis.cache_get("test:one") is None
    assert await redis.cache_delete_pattern("test:*") == 0
    await redis.cache_set("test:two", "value", 60)
    await redis.cache_set("other", "keep", 60)
    assert await redis.cache_delete_pattern("test:*") == 1
    assert await redis.cache_get("other") == "keep"


async def test_cache_outage_is_nonfatal(monkeypatch):
    monkeypatch.setattr(redis, "_redis", None)
    with pytest.raises(RuntimeError):
        redis.get_redis()
    assert await redis.cache_get("key") is None
    assert not await redis.cache_set("key", "value", 60)
    await redis.cache_delete("key")
    assert await redis.cache_delete_pattern("test:*") == 0


async def test_request_session_rolls_back_and_closes(monkeypatch):
    session = AsyncMock()
    session.__aenter__.return_value = session
    monkeypatch.setattr(database, "_session_factory", MagicMock(return_value=session))
    dependency = database.get_db()
    assert await anext(dependency) is session
    with pytest.raises(ValueError):
        await dependency.athrow(ValueError("failed operation"))
    session.rollback.assert_awaited_once()
    session.close.assert_awaited_once()
    assert database._json_deserializer(database._json_serializer({"amount": 5})) == {"amount": 5}


async def test_database_initialization_failure_disposes_on_close(monkeypatch):
    engine = AsyncMock()
    connection = AsyncMock()
    connection.__aenter__.side_effect = ConnectionError("offline")
    engine.connect = MagicMock(return_value=connection)
    monkeypatch.setattr(database, "create_engine_and_session", lambda: (engine, MagicMock()))
    with pytest.raises(ConnectionError):
        await database.init_db()
    await database.close_db()
    engine.dispose.assert_awaited_once()


async def test_redis_initialization_failure_and_cleanup(monkeypatch):
    client = AsyncMock()
    client.ping.side_effect = ConnectionError("offline")
    monkeypatch.setattr(redis.aioredis, "from_url", lambda *args, **kwargs: client)
    with pytest.raises(ConnectionError):
        await redis.init_redis()
    await redis.close_redis()
    client.aclose.assert_awaited_once()


async def test_image_conversion_and_delete_boundaries(monkeypatch):
    service = ImageService()
    with pytest.raises(BusinessRuleError, match="5 MB"):
        service.validate(b"x" * (5 * 1024 * 1024 + 1))
    data = io.BytesIO()
    Image.new("L", (8, 8), 100).save(data, format="PNG")
    webp = service.to_webp(data.getvalue())
    assert service.validate(webp) == "image/webp"
    delete = AsyncMock()
    monkeypatch.setattr(service.storage, "delete", delete)
    await service.delete("https://untrusted.example/any-file")
    delete.assert_not_awaited()
    await service.delete(service.storage.get_public_url("products", "test.webp"))
    delete.assert_awaited_once_with("products", "test.webp")


def test_log_scrubber_redacts_credentials():
    from app.core.logging import _scrub_sensitive

    value = _scrub_sensitive(
        None, "info", {"password": "secret", "Authorization": "Bearer secret", "event": "login"}
    )
    assert value == {"password": "[REDACTED]", "Authorization": "[REDACTED]", "event": "login"}


def test_structured_logging_configuration_restores_host_logging(monkeypatch):
    import logging

    import structlog

    from app.core.config import settings
    from app.core.logging import configure_logging, get_logger

    root = logging.getLogger()
    handlers, level = root.handlers[:], root.level
    configuration = structlog.get_config().copy()
    named_levels = {
        name: logging.getLogger(name).level
        for name in ("uvicorn.access", "sqlalchemy.engine", "asyncpg")
    }
    try:
        for environment in ("development", "test"):
            monkeypatch.setattr(settings, "ENVIRONMENT", environment)
            configure_logging()
            get_logger("release-test").info("test-event", password="must-be-redacted")
            assert root.level == (logging.DEBUG if environment == "development" else logging.INFO)
    finally:
        root.handlers, root.level = handlers, level
        structlog.configure(**configuration)
        for name, saved_level in named_levels.items():
            logging.getLogger(name).setLevel(saved_level)
