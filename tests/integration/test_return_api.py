"""Integration tests — Block 10: Returns & Disputes."""
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
import app.models.return_  # noqa

from app.api.v1.returns import router as returns_router
from app.core.database import get_db
from app.core.exceptions import DRIPException

VALID_RETURN_PAYLOAD = {
    "seller_order_id": str(uuid4()),
    "reason":          "Item arrived damaged and not as described in listing",
    "items":           [{"order_item_id": str(uuid4()), "quantity": 1}],
}


@pytest.fixture
def client():
    test_app = FastAPI()
    test_app.include_router(returns_router)

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


class TestCustomerReturnEndpoints:
    def test_request_return_no_auth(self, client):
        r = client.post("/returns", json=VALID_RETURN_PAYLOAD)
        assert r.status_code in (401, 422)

    def test_request_return_short_reason(self, client, customer_headers):
        r = client.post("/returns", json={**VALID_RETURN_PAYLOAD, "reason": "bad"}, headers=customer_headers)
        assert r.status_code == 422

    def test_request_return_empty_items(self, client, customer_headers):
        r = client.post("/returns", json={**VALID_RETURN_PAYLOAD, "items": []}, headers=customer_headers)
        assert r.status_code == 422

    def test_list_returns_no_auth(self, client):
        r = client.get("/returns")
        assert r.status_code in (401, 422)

    def test_get_return_no_auth(self, client):
        r = client.get(f"/returns/{uuid4()}")
        assert r.status_code in (401, 422)

    def test_open_dispute_no_auth(self, client):
        r = client.post(f"/returns/{uuid4()}/dispute",
                        json={"message": "Opening dispute for unfair rejection"})
        assert r.status_code in (401, 422)

    def test_open_dispute_short_message(self, client, customer_headers):
        r = client.post(f"/returns/{uuid4()}/dispute", json={"message": "bad"}, headers=customer_headers)
        assert r.status_code == 422

    def test_get_dispute_no_auth(self, client):
        r = client.get(f"/returns/{uuid4()}/dispute")
        assert r.status_code in (401, 422)

    def test_add_message_no_auth(self, client):
        r = client.post(f"/returns/{uuid4()}/dispute/messages",
                        json={"body": "Here is my evidence"})
        assert r.status_code in (401, 422)


class TestAdminReturnEndpoints:
    def test_list_returns_no_auth(self, client):
        r = client.get("/admin/returns")
        assert r.status_code in (401, 422)

    def test_list_returns_invalid_status(self, client):
        r = client.get("/admin/returns?status=unknown")
        assert r.status_code in (401, 422)

    def test_approve_no_auth(self, client):
        r = client.post(f"/admin/returns/{uuid4()}/approve", json={})
        assert r.status_code in (401, 422)

    def test_reject_no_auth(self, client):
        r = client.post(f"/admin/returns/{uuid4()}/reject", json={})
        assert r.status_code in (401, 422)

    def test_received_no_auth(self, client):
        r = client.post(f"/admin/returns/{uuid4()}/received", json={})
        assert r.status_code in (401, 422)

    def test_refund_no_auth(self, client):
        r = client.post(f"/admin/returns/{uuid4()}/refund", json={})
        assert r.status_code in (401, 422)

    def test_list_disputes_no_auth(self, client):
        r = client.get("/admin/disputes")
        assert r.status_code in (401, 422)

    def test_list_disputes_invalid_status(self, client):
        r = client.get("/admin/disputes?status=unknown")
        assert r.status_code in (401, 422)

    def test_resolve_dispute_no_auth(self, client):
        r = client.post(f"/admin/disputes/{uuid4()}/resolve", json={
            "in_favor_of": "customer",
            "resolution_note": "Customer provided clear evidence"
        })
        assert r.status_code in (401, 422)

    def test_resolve_invalid_in_favor_of(self, client, admin_headers):
        r = client.post(f"/admin/disputes/{uuid4()}/resolve", json={
            "in_favor_of": "platform",
            "resolution_note": "Resolution note here"
        }, headers=admin_headers)
        assert r.status_code == 422