"""Browser callback outcomes without live Google, Redis or database calls."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from fastapi.responses import RedirectResponse

from app.core.exceptions import AuthenticationError, BusinessRuleError
from app.services import google_oauth as oauth


@pytest.fixture
def flow(monkeypatch):
    monkeypatch.setattr(oauth, "require_configuration", lambda: None)
    monkeypatch.setattr(oauth, "frontend_url", lambda path: "https://shop.example.test" + path)
    redis = SimpleNamespace(getdel=AsyncMock(return_value='{"nonce":"n","verifier":"v"}'))
    monkeypatch.setattr(oauth, "get_redis", lambda: redis)
    request = SimpleNamespace(
        query_params={"state": "bound-state", "error": "access_denied"},
        cookies={oauth.STATE_COOKIE: "bound-state"},
    )
    return request, SimpleNamespace(rollback=AsyncMock()), redis


@pytest.mark.asyncio
async def test_bound_cancellation_consumes_state_without_provider_request(flow, monkeypatch):
    request, db, redis = flow
    client = Mock(side_effect=AssertionError("Provider must not be contacted"))
    monkeypatch.setattr(oauth.httpx, "AsyncClient", client)
    response = await oauth.google_callback_response(request, db)
    assert response.status_code == 303
    assert response.headers["location"] == "https://shop.example.test/auth/callback?error=cancelled"
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["referrer-policy"] == "no-referrer"
    assert "Max-Age=0" in response.headers["set-cookie"]
    assert oauth.CALLBACK_PATH in response.headers["set-cookie"]
    redis.getdel.assert_awaited_once_with("google-state:bound-state")
    db.rollback.assert_awaited_once()
    client.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize("state", ["", "foreign", "x" * 129])
async def test_unbound_cancellation_does_not_consume_state(flow, state):
    request, db, redis = flow
    request.query_params["state"] = state
    response = await oauth.google_callback_response(request, db)
    assert response.headers["location"].endswith("?error=failed")
    redis.getdel.assert_not_awaited()


@pytest.mark.asyncio
async def test_expired_cancellation_is_not_accepted(flow):
    request, db, redis = flow
    redis.getdel.return_value = None
    response = await oauth.google_callback_response(request, db)
    assert response.headers["location"].endswith("?error=failed")


@pytest.mark.asyncio
@pytest.mark.parametrize("query", [{"error": "provider-secret"}, {}])
async def test_provider_error_or_missing_code_never_reflected(flow, query):
    request, db, redis = flow
    request.query_params = {"state": "bound-state", **query}
    response = await oauth.google_callback_response(request, db)
    assert response.headers["location"] == "https://shop.example.test/auth/callback?error=failed"
    redis.getdel.assert_awaited_once()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "error", [AuthenticationError("private"), BusinessRuleError("private"), RuntimeError("private")]
)
async def test_failures_roll_back_without_leaking_details(flow, monkeypatch, error):
    request, db, _ = flow
    monkeypatch.setattr(oauth, "finish_google_login", AsyncMock(side_effect=error))
    response = await oauth.google_callback_response(request, db)
    assert response.headers["location"] == "https://shop.example.test/auth/callback?error=failed"
    assert "private" not in str(response.headers)
    assert "drip_refresh_token" not in response.headers["set-cookie"]
    db.rollback.assert_awaited_once()


@pytest.mark.asyncio
async def test_rollback_failure_still_returns_safe_failure(flow, monkeypatch):
    request, db, _ = flow
    monkeypatch.setattr(
        oauth, "finish_google_login", AsyncMock(side_effect=RuntimeError("private"))
    )
    db.rollback.side_effect = RuntimeError("database offline")
    response = await oauth.google_callback_response(request, db)
    assert response.headers["location"].endswith("?error=failed")


@pytest.mark.asyncio
async def test_success_preserves_existing_cookie_response(flow, monkeypatch):
    request, db, _ = flow
    response = RedirectResponse("https://shop.example.test/auth/callback", status_code=303)
    response.set_cookie("fixture-session", "fixture")
    monkeypatch.setattr(oauth, "finish_google_login", AsyncMock(return_value=response))
    assert await oauth.google_callback_response(request, db) is response
    db.rollback.assert_not_awaited()


@pytest.mark.asyncio
async def test_route_uses_browser_callback_boundary(flow, monkeypatch):
    from app.api.v1.auth import google_callback

    request, db, _ = flow
    response = RedirectResponse("https://shop.example.test/auth/callback", status_code=303)
    handler = AsyncMock(return_value=response)
    monkeypatch.setattr(oauth, "google_callback_response", handler)
    assert await google_callback(request, db) is response
    handler.assert_awaited_once_with(request, db)
