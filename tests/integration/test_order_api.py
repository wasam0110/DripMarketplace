"""Integration tests — Block 5: Orders & Cart."""
import pytest
from uuid import uuid4
from unittest.mock import MagicMock, AsyncMock
from fastapi import FastAPI
from fastapi.testclient import TestClient
from fastapi.responses import JSONResponse

import app.models.user    # noqa
import app.models.seller  # noqa
import app.models.product # noqa
import app.models.order   # noqa
import app.models.coupon  # noqa

from app.api.v1.orders import router as order_router
from app.api.v1.cart   import router as cart_router
from app.core.database import get_db
from app.core.exceptions import DRIPException


@pytest.fixture
def client():
    test_app = FastAPI()
    test_app.include_router(order_router)
    test_app.include_router(cart_router)

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


VALID_ORDER_PAYLOAD = {
    "shipping_address": {
        "recipient_name": "Ali Khan",
        "phone":          "03001234567",
        "street":         "House 5, Street 12, DHA Phase 6",
        "city":           "Karachi",
        "province":       "Sindh",
    },
    "payment_method": "cod",
}


class TestOrderEndpoints:
    def test_place_order_no_auth(self, client):
        r = client.post("/orders", json=VALID_ORDER_PAYLOAD)
        assert r.status_code in (401, 422)

    def test_place_order_invalid_payment_method(self, client):
        r = client.post("/orders", json={**VALID_ORDER_PAYLOAD, "payment_method": "bitcoin"})
        assert r.status_code in (401, 422)

    def test_place_order_missing_address(self, client):
        r = client.post("/orders", json={"payment_method": "cod"})
        assert r.status_code in (401, 422)

    def test_guest_order_no_items(self, client):
        r = client.post("/orders/guest", json={**VALID_ORDER_PAYLOAD,
            "guest_email": "test@test.com", "guest_name": "Ali", "guest_phone": "03001234567",
            "items": []})
        assert r.status_code == 422

    def test_guest_order_invalid_phone(self, client):
        r = client.post("/orders/guest", json={**VALID_ORDER_PAYLOAD,
            "guest_email": "test@test.com", "guest_name": "Ali", "guest_phone": "12345",
            "items": [{"variant_id": str(uuid4()), "quantity": 1}]})
        assert r.status_code == 422

    def test_list_orders_no_auth(self, client):
        r = client.get("/orders")
        assert r.status_code in (401, 422)

    def test_get_order_no_auth(self, client):
        r = client.get(f"/orders/{uuid4()}")
        assert r.status_code in (401, 422)

    def test_cancel_order_no_auth(self, client):
        r = client.post(f"/orders/{uuid4()}/cancel", json={"reason": "Changed mind"})
        assert r.status_code in (401, 422)

    def test_get_order_by_number_missing_email(self, client):
        r = client.get("/orders/number/DRIP-202408-AB1234")
        assert r.status_code == 422   # email query param required


class TestCouponEndpoints:
    def test_validate_no_auth(self, client):
        r = client.post("/coupons/validate", json={"code": "DRIP10", "subtotal": 5000})
        assert r.status_code in (401, 422)

    def test_validate_zero_subtotal(self, client):
        r = client.post("/coupons/validate", json={"code": "DRIP10", "subtotal": 0})
        assert r.status_code in (401, 422)


class TestSellerOrderEndpoints:
    def test_list_seller_orders_no_auth(self, client):
        r = client.get("/seller/orders")
        assert r.status_code in (401, 422)

    def test_list_seller_orders_invalid_status(self, client):
        r = client.get("/seller/orders?status=unknown")
        assert r.status_code in (401, 422)

    def test_update_status_no_auth(self, client):
        r = client.put(f"/seller/orders/{uuid4()}/status",
                       json={"status": "processing"})
        assert r.status_code in (401, 422)

    def test_update_status_shipped_no_tracking(self, client):
        r = client.put(f"/seller/orders/{uuid4()}/status",
                       json={"status": "shipped"})
        assert r.status_code in (401, 422)

    def test_update_status_invalid_status(self, client):
        r = client.put(f"/seller/orders/{uuid4()}/status",
                       json={"status": "cancelled"})
        assert r.status_code in (401, 422)


class TestCartEndpoints:
    def test_get_cart_no_auth(self, client):
        r = client.get("/cart")
        assert r.status_code in (401, 422)

    def test_add_to_cart_no_auth(self, client):
        r = client.post("/cart", json={"variant_id": str(uuid4()), "quantity": 1})
        assert r.status_code in (401, 422)

    def test_add_to_cart_zero_qty(self, client):
        r = client.post("/cart", json={"variant_id": str(uuid4()), "quantity": 0})
        assert r.status_code in (401, 422)

    def test_update_cart_item_no_auth(self, client):
        r = client.patch(f"/cart/{uuid4()}", json={"quantity": 2})
        assert r.status_code in (401, 422)

    def test_remove_cart_item_no_auth(self, client):
        r = client.delete(f"/cart/{uuid4()}")
        assert r.status_code in (401, 422)

    def test_clear_cart_no_auth(self, client):
        r = client.post("/cart/clear")
        assert r.status_code in (401, 422)