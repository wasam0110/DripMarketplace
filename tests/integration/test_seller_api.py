"""
Integration tests — Block 3: Seller API endpoints
Run: pytest tests/integration/test_seller_api.py -v

Tests schema validation and route shapes.
Full DB/auth E2E: docker-compose up, then pytest --integration.
"""
import pytest
from uuid import uuid4
from unittest.mock import MagicMock, AsyncMock
from fastapi.testclient import TestClient
from fastapi import FastAPI
from app.core.database import get_db 
from app.api.deps import get_db
from app.api.v1.sellers import router as seller_router


@pytest.fixture(scope="module")
def client():
    from fastapi.responses import JSONResponse
    from app.core.exceptions import DRIPException

    app = FastAPI()
    app.include_router(seller_router)

    # Register the same exception handler the real app uses
    @app.exception_handler(DRIPException)
    async def drip_handler(request, exc):
        return JSONResponse(
            status_code=exc.http_status,
            content={"detail": exc.message},
        )

    # Override get_db so tests never touch the real database
    async def mock_db():
        session = MagicMock()
        session.execute  = AsyncMock()
        session.commit   = AsyncMock()
        session.rollback = AsyncMock()
        session.flush    = AsyncMock()
        session.close    = AsyncMock()
        yield session

    app.dependency_overrides[get_db] = mock_db

    with TestClient(app) as c:
        yield c


VALID_REG_PAYLOAD = {
    "email":           "newbrand@drip.pk",
    "password":        "Password123",
    "first_name":      "Ali",
    "brand_name":      "New Streetwear Brand",
    "description":     "Authentic streetwear for the culture of Pakistan",
    "return_policy":   "No returns on sale items, exchange within 7 days",
    "whatsapp_number": "03001234567",
    "extra_slots":     0,
}


class TestSlotPriceEndpoint:
    def test_zero_extra(self, client):
        r = client.get("/seller/register/slot-price")
        assert r.status_code == 200
        d = r.json()
        assert d["registration_fee"] == 5000
        assert d["total_slots"]      == 50
        assert d["total_cost"]       == 5000

    def test_twenty_extra(self, client):
        r = client.get("/seller/register/slot-price?extra_slots=20")
        assert r.status_code == 200
        d = r.json()
        assert d["extra_cost"]  == 1000
        assert d["total_cost"]  == 6000
        assert d["total_slots"] == 70

    def test_negative_rejected(self, client):
        r = client.get("/seller/register/slot-price?extra_slots=-1")
        assert r.status_code == 422

    def test_over_limit_rejected(self, client):
        r = client.get("/seller/register/slot-price?extra_slots=99999")
        assert r.status_code == 422


class TestRegisterEndpoint:
    def test_empty_payload_rejected(self, client):
        r = client.post("/seller/register", json={})
        assert r.status_code == 422

    def test_invalid_phone_rejected(self, client):
        r = client.post("/seller/register", json={
            **VALID_REG_PAYLOAD, "whatsapp_number": "12345"
        })
        assert r.status_code == 422

    def test_weak_password_rejected(self, client):
        r = client.post("/seller/register", json={
            **VALID_REG_PAYLOAD, "password": "password"
        })
        assert r.status_code == 422

    def test_short_description_rejected(self, client):
        r = client.post("/seller/register", json={
            **VALID_REG_PAYLOAD, "description": "Too short"
        })
        assert r.status_code == 422


class TestPrivateEndpoints:
    """All private endpoints return 401/422 without a valid token."""

    def test_get_profile_no_auth(self, client):
        r = client.get("/seller/me")
        assert r.status_code in (401, 422)

    def test_patch_profile_no_auth(self, client):
        r = client.patch("/seller/me", json={"description": "New desc"})
        assert r.status_code in (401, 422)

    def test_dashboard_no_auth(self, client):
        r = client.get("/seller/dashboard")
        assert r.status_code in (401, 422)

    def test_dashboard_invalid_period(self, client):
        r = client.get("/seller/dashboard?period=yesterday")
        assert r.status_code in (401, 422)

    def test_orders_no_auth(self, client):
        r = client.get("/seller/orders")
        assert r.status_code in (401, 422)

    def test_orders_invalid_status(self, client):
        r = client.get("/seller/orders?status=unknown")
        assert r.status_code in (401, 422)

    def test_order_detail_stub(self, client):
        r = client.get(f"/seller/orders/{uuid4()}")
        assert r.status_code in (401, 422, 501)

    def test_bank_accounts_no_auth(self, client):
        r = client.get("/seller/bank-accounts")
        assert r.status_code in (401, 422)

    def test_bank_account_empty_body(self, client):
        r = client.post("/seller/bank-accounts", json={})
        assert r.status_code in (401, 422)

    def test_analytics_no_auth(self, client):
        r = client.get("/seller/analytics/revenue")
        assert r.status_code in (401, 422)

    def test_analytics_invalid_period(self, client):
        r = client.get("/seller/analytics/revenue?period=5y")
        assert r.status_code in (401, 422)

    def test_analytics_invalid_granularity(self, client):
        r = client.get("/seller/analytics/revenue?granularity=hour")
        assert r.status_code in (401, 422)

    def test_slot_purchase_zero_qty(self, client):
        r = client.post("/seller/slots/purchase",
                        json={"quantity": 0, "payment_method": "wallet"})
        assert r.status_code in (401, 422)

    def test_slot_purchase_bad_method(self, client):
        r = client.post("/seller/slots/purchase",
                        json={"quantity": 5, "payment_method": "stripe"})
        assert r.status_code in (401, 422)