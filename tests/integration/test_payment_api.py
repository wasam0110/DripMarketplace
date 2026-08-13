"""Integration tests — Block 6: Payments."""
import pytest
from uuid import uuid4
from unittest.mock import MagicMock, AsyncMock
from fastapi import FastAPI
from fastapi.testclient import TestClient
from fastapi.responses import JSONResponse

import app.models.user     # noqa
import app.models.seller   # noqa
import app.models.product  # noqa
import app.models.order    # noqa
import app.models.coupon   # noqa
import app.models.payment  # noqa

from app.api.v1.payments import router as payment_router
from app.core.database import get_db
from app.core.exceptions import DRIPException


@pytest.fixture
def client():
    test_app = FastAPI()
    test_app.include_router(payment_router)

    @test_app.exception_handler(DRIPException)
    async def drip_handler(request, exc):
        return JSONResponse(status_code=exc.http_status, content={"detail": exc.message})

    result = MagicMock()
    result.scalars.return_value.all.return_value        = []
    result.scalar_one_or_none.return_value              = None
    result.scalar_one.return_value                      = 0

    async def mock_db():
        session          = MagicMock()
        session.execute  = AsyncMock(return_value=result)
        session.commit   = AsyncMock()
        session.rollback = AsyncMock()
        session.flush    = AsyncMock()
        yield session

    test_app.dependency_overrides[get_db] = mock_db
    with TestClient(test_app, raise_server_exceptions=False) as c:
        yield c


class TestCustomerEndpoints:
    def test_initiate_no_auth(self, client):
        r = client.post("/payments/initiate",
                        json={"order_id": str(uuid4())})
        assert r.status_code in (401, 422)

    def test_status_no_auth(self, client):
        r = client.get(f"/payments/{uuid4()}/status")
        assert r.status_code in (401, 422)

    def test_retry_no_auth(self, client):
        r = client.post(f"/payments/{uuid4()}/retry",
                        json={"payment_method": "jazzcash"})
        assert r.status_code in (401, 422)

    def test_retry_invalid_method(self, client):
        r = client.post(f"/payments/{uuid4()}/retry",
                        json={"payment_method": "paypal"})
        assert r.status_code == 422


class TestCallbackEndpoints:
    def test_jazzcash_callback_ok(self, client):
        """Gateway callbacks always return 200."""
        r = client.post("/payments/callback/jazzcash",
                        data={"pp_ResponseCode": "111", "pp_SecureHash": "bad"})
        assert r.status_code == 200

    def test_easypaisa_callback_ok(self, client):
        r = client.post("/payments/callback/easypaisa",
                        json={"responseCode": "9999", "hash": "bad"})
        assert r.status_code == 200

    def test_stripe_callback_ok(self, client):
        r = client.post("/payments/callback/stripe",
                        json={"type": "payment_intent.succeeded"},
                        headers={"stripe-signature": "invalid"})
        assert r.status_code == 200


class TestAdminEndpoints:
    def test_gateway_status_no_auth(self, client):
        r = client.get("/payments/gateway-status")
        assert r.status_code in (401, 422)

    def test_list_payments_no_auth(self, client):
        r = client.get("/payments")
        assert r.status_code in (401, 422)

    def test_list_payments_invalid_status(self, client):
        r = client.get("/payments?status=unknown")
        assert r.status_code == 422

    def test_refund_no_auth(self, client):
        r = client.post(f"/payments/{uuid4()}/refund",
                        json={"amount": 500, "reason": "Customer returned item"})
        assert r.status_code in (401, 422)

    def test_refund_short_reason(self, client):
        r = client.post(f"/payments/{uuid4()}/refund",
                        json={"amount": 500, "reason": "bad"})
        assert r.status_code == 422

    def test_refund_zero_amount(self, client):
        r = client.post(f"/payments/{uuid4()}/refund",
                        json={"amount": 0, "reason": "Valid long reason here"})
        assert r.status_code == 422