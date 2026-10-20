"""Full application-stack error contracts, without live databases or providers."""

import asyncio
from unittest.mock import AsyncMock, Mock

import pytest
from fastapi import FastAPI, HTTPException
from httpx import ASGITransport, AsyncClient
from main import create_application
from pydantic import BaseModel

from app.core.config import settings
from app.core.exceptions import BusinessRuleError, ExternalServiceError, RateLimitError
from app.core.middleware import ErrorBoundaryMiddleware, RateLimitMiddleware
from app.schemas.common import ErrorResponse

pytestmark = pytest.mark.unit


class ProbeInput(BaseModel):
    quantity: int


@pytest.fixture(scope="module")
def error_app():
    app = create_application()

    @app.get("/__errors/http/{status}", include_in_schema=False)
    async def explicit_http_error(status: int):
        detail = "private-provider-secret" if status >= 500 else "Public error explanation"
        raise HTTPException(
            status, detail, headers={"Retry-After": "17", "WWW-Authenticate": "Bearer"}
        )

    @app.get("/__errors/unhandled", include_in_schema=False)
    async def unexpected_error():
        raise RuntimeError("private-provider-secret")

    @app.get("/__errors/domain/{kind}", include_in_schema=False)
    async def domain_error(kind: str):
        if kind == "rate":
            raise RateLimitError(23)
        if kind == "upstream":
            raise ExternalServiceError(detail="private-provider-secret")
        raise BusinessRuleError("Public business rule", fields={"quantity": "Not available"})

    @app.post("/__errors/validation", include_in_schema=False)
    async def validate_body(body: ProbeInput):
        return {"quantity": body.quantity}

    @app.get("/__errors/structured", include_in_schema=False)
    async def structured_detail():
        raise HTTPException(400, {"internal": "private-provider-secret"})

    @app.get("/__errors/response", response_model=ProbeInput, include_in_schema=False)
    async def invalid_response():
        return {"quantity": "private-provider-secret"}

    return app


@pytest.fixture
async def error_client(monkeypatch, error_app):
    monkeypatch.setattr("app.core.error_responses.logger", Mock())
    monkeypatch.setattr(RateLimitMiddleware, "_check", AsyncMock(return_value=(True, 10)))

    async with AsyncClient(
        transport=ASGITransport(app=error_app, raise_app_exceptions=False),
        base_url="http://testserver",
        headers={"X-Request-ID": "error-contract", "Origin": settings.ALLOWED_ORIGINS[0]},
    ) as client:
        yield client


def assert_error(response, status, code):
    assert response.status_code == status, response.text
    assert response.headers["content-type"].startswith("application/json")
    payload = response.json()
    assert set(payload) == {"error"}
    assert payload["error"]["code"] == code
    assert isinstance(payload["error"]["message"], str)
    assert payload["error"]["request_id"] == response.headers["x-request-id"] == "error-contract"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert "script-src 'self';" in response.headers["content-security-policy"]
    assert "frame-src 'none';" in response.headers["content-security-policy"]
    assert "stripe.com" not in response.headers["content-security-policy"]
    assert response.headers["access-control-allow-origin"] == settings.ALLOWED_ORIGINS[0]
    assert response.headers["cache-control"] == "no-store"
    assert "private-provider-secret" not in response.text
    return payload["error"]


@pytest.mark.parametrize(
    "status,code",
    [
        (400, "BAD_REQUEST"),
        (401, "UNAUTHORIZED"),
        (403, "FORBIDDEN"),
        (404, "NOT_FOUND"),
        (405, "METHOD_NOT_ALLOWED"),
        (409, "CONFLICT"),
        (413, "PAYLOAD_TOO_LARGE"),
        (415, "UNSUPPORTED_MEDIA_TYPE"),
        (422, "VALIDATION_ERROR"),
        (429, "RATE_LIMITED"),
        (500, "INTERNAL_ERROR"),
        (502, "EXTERNAL_SERVICE_ERROR"),
        (503, "SERVICE_UNAVAILABLE"),
        (504, "GATEWAY_TIMEOUT"),
        (418, "HTTP_418"),
        (599, "HTTP_599"),
    ],
)
async def test_http_errors_use_envelope_and_keep_headers(error_client, status, code):
    response = await error_client.get(f"/__errors/http/{status}")
    error = assert_error(response, status, code)
    if status < 500:
        assert error["message"] == "Public error explanation"
    assert response.headers["retry-after"] == "17"
    assert response.headers["www-authenticate"] == "Bearer"


async def test_router_404_and_405(error_client):
    assert_error(await error_client.get("/__errors/missing"), 404, "NOT_FOUND")
    wrong_method = await error_client.post("/__errors/unhandled")
    assert_error(wrong_method, 405, "METHOD_NOT_ALLOWED")
    assert "GET" in wrong_method.headers["allow"]


async def test_unexpected_error_keeps_outer_headers_and_hides_details(error_client):
    assert_error(await error_client.get("/__errors/unhandled"), 500, "INTERNAL_ERROR")


@pytest.mark.parametrize(
    "kind,status,code",
    [
        ("business", 422, "BUSINESS_RULE_VIOLATION"),
        ("upstream", 502, "EXTERNAL_SERVICE_ERROR"),
        ("rate", 429, "RATE_LIMITED"),
    ],
)
async def test_existing_domain_errors_keep_codes_and_fields(error_client, kind, status, code):
    response = await error_client.get(f"/__errors/domain/{kind}")
    error = assert_error(response, status, code)
    if kind == "business":
        assert error["fields"] == {"quantity": "Not available"}
    if kind == "rate":
        assert response.headers["retry-after"] == "23"


async def test_validation_fields_do_not_include_raw_input(error_client):
    response = await error_client.post(
        "/__errors/validation", json={"quantity": "private-provider-secret"}
    )
    error = assert_error(response, 422, "VALIDATION_ERROR")
    assert "quantity" in error["fields"]


async def test_middleware_rate_limit_keeps_retry_metadata(error_client, monkeypatch):
    monkeypatch.setattr(RateLimitMiddleware, "_check", AsyncMock(return_value=(False, 0)))
    response = await error_client.get("/__errors/unhandled")
    assert_error(response, 429, "RATE_LIMITED")
    assert int(response.headers["retry-after"]) > 0
    assert response.headers["x-ratelimit-remaining"] == "0"


async def test_non_string_http_details_are_not_serialized(error_client):
    error = assert_error(await error_client.get("/__errors/structured"), 400, "BAD_REQUEST")
    assert error["message"] == "Bad Request"


async def test_invalid_response_is_generic_500(error_client):
    assert_error(await error_client.get("/__errors/response"), 500, "INTERNAL_ERROR")


async def test_malformed_json_and_path_have_validation_envelopes(error_client):
    response = await error_client.post(
        "/__errors/validation", content="{", headers={"Content-Type": "application/json"}
    )
    assert_error(response, 422, "VALIDATION_ERROR")
    assert_error(await error_client.get("/__errors/http/not-an-int"), 422, "VALIDATION_ERROR")


async def test_error_does_not_allow_untrusted_origin(error_client):
    response = await error_client.get(
        "/__errors/unhandled", headers={"Origin": "https://untrusted.example.test"}
    )
    assert response.status_code == 500
    assert "access-control-allow-origin" not in response.headers


async def test_generated_request_id_matches_error_body(error_client):
    del error_client.headers["X-Request-ID"]
    response = await error_client.get("/__errors/unhandled")
    assert response.headers["x-request-id"]
    assert response.json()["error"]["request_id"] == response.headers["x-request-id"]


@pytest.mark.parametrize("status", [204, 304])
async def test_bodyless_status_is_preserved(error_client, status):
    response = await error_client.get(f"/__errors/http/{status}")
    assert response.status_code == status
    assert response.content == b""


async def test_error_boundary_never_sends_second_response():
    async def streaming_app(scope, receive, send):
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"partial", "more_body": True})
        raise RuntimeError("stream failure")

    send = AsyncMock()
    with pytest.raises(RuntimeError, match="stream failure"):
        await ErrorBoundaryMiddleware(streaming_app)({"type": "http"}, AsyncMock(), send)
    assert send.await_count == 2


async def test_error_boundary_does_not_swallow_cancellation():
    app, send = AsyncMock(side_effect=asyncio.CancelledError), AsyncMock()
    with pytest.raises(asyncio.CancelledError):
        await ErrorBoundaryMiddleware(app)({"type": "http"}, AsyncMock(), send)
    send.assert_not_awaited()


@pytest.mark.parametrize("kind", ["lifespan", "websocket"])
async def test_error_boundary_passes_non_http_scopes_through(kind):
    app, receive, send, scope = AsyncMock(), AsyncMock(), AsyncMock(), {"type": kind}
    await ErrorBoundaryMiddleware(app)(scope, receive, send)
    app.assert_awaited_once_with(scope, receive, send)


def test_openapi_documents_actual_error_models(error_app):
    schema = error_app.openapi()
    count = 0
    for path, item in schema["paths"].items():
        for method, operation in item.items():
            if method not in {"get", "post", "put", "patch", "delete", "options", "head"}:
                continue
            count += 1
            for status in (400, 401, 403, 404, 405, 409, 413, 415, 422, 429, 500, 502, 503, 504):
                expected = (
                    "HealthResponse"
                    if path.endswith("/health") and status == 503
                    else "ErrorResponse"
                )
                assert operation["responses"][str(status)]["content"]["application/json"][
                    "schema"
                ] == {"$ref": f"#/components/schemas/{expected}"}, (path, method, status)
    assert count > 180


def test_development_health_schema_preserves_degraded_response(monkeypatch):
    from app.api.v1.health import router

    # Visibility is set when this module is imported, before the test environment changes.
    monkeypatch.setattr(router.routes[0], "include_in_schema", True)
    app = FastAPI(responses={503: {"model": ErrorResponse}})
    app.include_router(router, prefix="/api/v1")
    schema = app.openapi()
    response = schema["paths"]["/api/v1/health"]["get"]["responses"]["503"]
    assert response["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/HealthResponse"
    }


async def test_success_body_is_not_wrapped(error_client):
    response = await error_client.post("/__errors/validation", json={"quantity": 2})
    assert response.status_code == 200
    assert response.json() == {"quantity": 2}
    assert "cache-control" not in response.headers


async def test_cors_preflight_keeps_protocol_response(error_client):
    response = await error_client.options(
        "/__errors/validation",
        headers={
            "Origin": "https://untrusted.example.test",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert response.status_code == 400
    assert response.headers["content-type"].startswith("text/plain")
    assert "access-control-allow-origin" not in response.headers


@pytest.mark.parametrize("path", ["/docs", "/redoc", "/docs/oauth2-redirect"])
async def test_development_docs_allow_assets_and_bootstrap(monkeypatch, path):
    monkeypatch.setattr(settings, "ENVIRONMENT", "development")
    monkeypatch.setattr(RateLimitMiddleware, "_check", AsyncMock(return_value=(True, 10)))
    async with AsyncClient(
        transport=ASGITransport(app=create_application()), base_url="http://testserver"
    ) as client:
        response = await client.get(path)
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/html")
        policy = response.headers["content-security-policy"]
        assert "script-src 'self' https://cdn.jsdelivr.net 'unsafe-inline';" in policy
        assert "style-src 'self' https://cdn.jsdelivr.net" in policy
        assert "https://fonts.googleapis.com 'unsafe-inline';" in policy
        assert "font-src 'self' https://fonts.gstatic.com;" in policy
        assert "img-src 'self' data: https://fastapi.tiangolo.com;" in policy
        assert "connect-src 'self';" in policy
        assert "frame-ancestors 'none';" in policy
        assert response.headers["x-content-type-options"] == "nosniff"
        schema = await client.get("/openapi.json")
        assert schema.status_code == 200
        assert "script-src 'self';" in schema.headers["content-security-policy"]
        missing = await client.get("/docs/not-a-doc-page")
        assert missing.status_code == 404
        assert "'unsafe-inline'" not in missing.headers["content-security-policy"]


@pytest.mark.parametrize("environment", ["test", "production"])
@pytest.mark.parametrize("path", ["/docs", "/redoc", "/docs/oauth2-redirect"])
async def test_non_development_docs_stay_disabled_and_strict(monkeypatch, environment, path):
    monkeypatch.setattr(settings, "ENVIRONMENT", environment)
    monkeypatch.setattr(RateLimitMiddleware, "_check", AsyncMock(return_value=(True, 10)))
    async with AsyncClient(
        transport=ASGITransport(app=create_application()), base_url="http://testserver"
    ) as client:
        response = await client.get(path)
    assert response.status_code == 404
    policy = response.headers["content-security-policy"]
    assert "script-src 'self';" in policy
    assert "'unsafe-inline'" not in policy
    assert "cdn.jsdelivr.net" not in policy
