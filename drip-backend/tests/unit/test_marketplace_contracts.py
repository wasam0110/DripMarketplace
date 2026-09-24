from collections import Counter
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock
import pytest
from main import app
from app.core.exceptions import BusinessRuleError, AuthenticationError, ExternalServiceError
from app.services.image_service import ImageService
from app.core.security import revoke_token, is_token_revoked


def test_unique_routes_and_gap_contracts():
    routes = [(method, route.path) for route in app.routes for method in getattr(route, "methods", [])]
    assert not [key for key, count in Counter(routes).items() if count > 1]
    for method, path in [("GET", "/brands"), ("GET", "/categories"), ("GET", "/content/banners"), ("GET", "/admin/analytics/cohort"), ("GET", "/seller/analytics/revenue"), ("PATCH", "/admin/content/banners/{banner_id}"), ("PATCH", "/seller/products/{product_id}/variants/{variant_id}"), ("GET", "/auth/google/callback")]:
        assert (method, "/api/v1" + path) in routes
    assert app.openapi()["info"]["title"] == "WearHowZ API"


@pytest.mark.parametrize("data", [b"", b"not an image", b"\xff\xd8\xffbroken", b"\x89PNGbroken"])
def test_corrupt_image_validation(data):
    service = ImageService()
    with pytest.raises(BusinessRuleError):
        service.validate(data)
        service.to_webp(data)


async def test_logout_revocation_and_redis_outage(monkeypatch):
    await revoke_token("test-jti", datetime.now(UTC) + timedelta(minutes=5))
    assert await is_token_revoked("test-jti")
    assert not await is_token_revoked("other-jti")
    import app.core.redis as redis_module
    monkeypatch.setattr(redis_module._redis, "get", AsyncMock(side_effect=RuntimeError("offline")))
    with pytest.raises(ExternalServiceError):
        await is_token_revoked("unknown")


async def test_google_configuration_and_browser_state(monkeypatch):
    from fastapi import Response, Request
    from app.services.google_oauth import start_google_login, finish_google_login
    from app.core.config import settings
    monkeypatch.setattr(settings, "GOOGLE_CLIENT_ID", "")
    with pytest.raises(ExternalServiceError):
        await start_google_login(Response())
    monkeypatch.setattr(settings, "GOOGLE_CLIENT_ID", "test-client")
    monkeypatch.setattr(settings, "GOOGLE_CLIENT_SECRET", "test-secret")
    response = Response()
    started = await start_google_login(response)
    assert "code_challenge=" in started["authorization_url"]
    assert "HttpOnly" in response.headers["set-cookie"]
    request = Request({"type": "http", "query_string": b"code=fake&state=mismatch", "headers": []})
    with pytest.raises(AuthenticationError):
        await finish_google_login(request, AsyncMock())
