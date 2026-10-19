"""Real route/dependency error envelopes against isolated PostgreSQL rows."""

from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from sqlalchemy import func, select
from test_marketplace_regressions import market as marketplace_fixture
from test_resource_ownership import headers

from app.core.config import settings
from app.models.payment import Payment
from app.services.payment_service import PaymentService

pytestmark = pytest.mark.integration
market = marketplace_fixture


def assert_contract(response, status, code):
    assert response.status_code == status, response.text
    assert set(response.json()) == {"error"}
    error = response.json()["error"]
    assert error["code"] == code
    assert error["request_id"] == response.headers["x-request-id"]
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["x-content-type-options"] == "nosniff"


@pytest.mark.parametrize(
    "case,status,code",
    [
        ("anonymous", 401, "UNAUTHORIZED"),
        ("wrong_role", 403, "FORBIDDEN"),
        ("missing", 404, "NOT_FOUND"),
        ("invalid_id", 422, "VALIDATION_ERROR"),
    ],
)
async def test_real_auth_resource_and_validation_errors(client, market, case, status, code):
    path, auth = "/api/v1/payments", {}
    if case == "wrong_role":
        path, auth = "/api/v1/payments", headers(market.buyer)
    elif case == "missing":
        path = f"/api/v1/products/{uuid4()}"
    elif case == "invalid_id":
        path = "/api/v1/products/invalid"
    response = await client.get(path, headers=auth)
    assert_contract(response, status, code)


@pytest.mark.parametrize(
    "case,status,code",
    [
        ("ip", 403, "FORBIDDEN"),
        ("length", 400, "BAD_REQUEST"),
        ("declared_size", 413, "PAYLOAD_TOO_LARGE"),
        ("actual_size", 413, "PAYLOAD_TOO_LARGE"),
    ],
)
async def test_callback_rejections_do_not_reach_payment_service(
    client,
    db,
    monkeypatch,
    case,
    status,
    code,
):
    handler = AsyncMock()
    monkeypatch.setattr(PaymentService, "handle_payfast_callback", handler)
    monkeypatch.setattr(settings, "PAYFAST_IPN_IPS", ["192.0.2.1"] if case == "ip" else [])
    request_headers = {"Content-Type": "application/x-www-form-urlencoded"}
    body = b""
    if case == "length":
        request_headers["Content-Length"] = "invalid"
    elif case == "declared_size":
        request_headers["Content-Length"] = "16385"
    elif case == "actual_size":
        request_headers["Content-Length"] = "0"
        body = b"a" * 16385
    before = await db.scalar(select(func.count(Payment.id)))
    response = await client.post(
        "/api/v1/payments/callback/payfast",
        content=body,
        headers=request_headers,
    )
    assert_contract(response, status, code)
    handler.assert_not_awaited()
    assert await db.scalar(select(func.count(Payment.id))) == before
