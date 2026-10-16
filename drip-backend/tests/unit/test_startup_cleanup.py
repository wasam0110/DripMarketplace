"""Lifespan cleanup must run on partial startup and shutdown failures."""

import sys
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import main
import pytest


@pytest.fixture
def resources(monkeypatch):
    callbacks = {}
    for name in ("init_db", "init_redis", "close_db", "close_redis"):
        callbacks[name] = AsyncMock()
        monkeypatch.setattr(main, name, callbacks[name])
    monkeypatch.setattr(main.settings, "SENTRY_DSN", "")
    return callbacks


@pytest.mark.asyncio
@pytest.mark.parametrize("stage", ["init_db", "init_redis", "close_db", "close_redis"])
async def test_closes_both_pools_when_one_stage_fails(resources, stage):
    resources[stage].side_effect = ConnectionError("test outage")
    with pytest.raises(ConnectionError, match="test outage"):
        async with main.lifespan(main.app):
            pass
    resources["close_db"].assert_awaited_once()
    resources["close_redis"].assert_awaited_once()


@pytest.mark.asyncio
async def test_closes_both_pools_on_application_exception(resources):
    with pytest.raises(RuntimeError, match="application failure"):
        async with main.lifespan(main.app):
            raise RuntimeError("application failure")
    resources["close_db"].assert_awaited_once()
    resources["close_redis"].assert_awaited_once()


@pytest.mark.asyncio
@pytest.mark.parametrize("failure", [False, True])
async def test_production_monitoring_startup_and_failure(resources, monkeypatch, failure):
    init = Mock(side_effect=RuntimeError("monitor init") if failure else None)
    monkeypatch.setitem(sys.modules, "sentry_sdk", SimpleNamespace(init=init))
    monkeypatch.setattr(main.settings, "ENVIRONMENT", "production")
    monkeypatch.setattr(main.settings, "SENTRY_DSN", "https://example.invalid/test")
    if failure:
        with pytest.raises(RuntimeError, match="monitor init"):
            async with main.lifespan(main.app):
                pass
    else:
        async with main.lifespan(main.app):
            assert init.call_args.kwargs["include_local_variables"] is False
            assert init.call_args.kwargs["max_request_body_size"] == "never"
            assert init.call_args.kwargs["send_default_pii"] is False
    resources["close_db"].assert_awaited_once()
    resources["close_redis"].assert_awaited_once()
