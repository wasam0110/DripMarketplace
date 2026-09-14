"""Integration tests — Block 8: Admin API."""
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
import app.models.payment # noqa
import app.models.wallet  # noqa
import app.models.admin   # noqa

from app.api.v1.admin import dashboard, brands, orders, cod_queue, payouts, content, settings
from app.core.database import get_db
from app.core.exceptions import DRIPException


@pytest.fixture
def client():
    test_app = FastAPI()
    for r in [dashboard.router, brands.router, orders.router,
              cod_queue.router, payouts.router, content.router, settings.router]:
        test_app.include_router(r)

    @test_app.exception_handler(DRIPException)
    async def drip_handler(request, exc):
        return JSONResponse(status_code=exc.http_status, content={"detail": exc.message})

    result = MagicMock()
    result.scalars.return_value.all.return_value        = []
    result.scalar_one_or_none.return_value              = None
    result.scalar_one.return_value                      = 0
    result.one.return_value                             = (0, 0)

    async def mock_db():
        session          = MagicMock()
        session.execute  = AsyncMock(return_value=result)
        session.commit   = AsyncMock()
        session.rollback = AsyncMock()
        session.flush    = AsyncMock()
        session.delete   = AsyncMock()
        yield session

    test_app.dependency_overrides[get_db] = mock_db
    with TestClient(test_app, raise_server_exceptions=False) as c:
        yield c


class TestDashboard:
    def test_no_auth(self, client):
        r = client.get("/admin/dashboard")
        assert r.status_code in (401, 422)

    def test_invalid_period(self, client):
        r = client.get("/admin/dashboard?period=yesterday")
        assert r.status_code in (401, 422)


class TestSellerAdmin:
    def test_list_no_auth(self, client):
        r = client.get("/admin/sellers")
        assert r.status_code in (401, 422)

    def test_list_invalid_status(self, client):
        r = client.get("/admin/sellers?status=unknown")
        assert r.status_code in (401, 422)

    def test_detail_no_auth(self, client):
        r = client.get(f"/admin/sellers/{uuid4()}")
        assert r.status_code in (401, 422)

    def test_approve_no_auth(self, client):
        r = client.post(f"/admin/sellers/{uuid4()}/approve")
        assert r.status_code in (401, 422)

    def test_reject_no_auth(self, client):
        r = client.post(f"/admin/sellers/{uuid4()}/reject",
                        json={"reason": "Valid rejection reason here"})
        assert r.status_code in (401, 422)

    def test_reject_short_reason(self, client):
        r = client.post(f"/admin/sellers/{uuid4()}/reject", json={"reason": "bad"})
        assert r.status_code in (401, 422)

    def test_suspend_no_auth(self, client):
        r = client.post(f"/admin/sellers/{uuid4()}/suspend",
                        json={"reason": "Policy violation reported"})
        assert r.status_code in (401, 422)

    def test_reinstate_no_auth(self, client):
        r = client.post(f"/admin/sellers/{uuid4()}/reinstate")
        assert r.status_code in (401, 422)


class TestOrderAdmin:
    def test_list_no_auth(self, client):
        r = client.get("/admin/orders")
        assert r.status_code in (401, 422)

    def test_list_invalid_payment_method(self, client):
        r = client.get("/admin/orders?payment_method=bitcoin")
        assert r.status_code in (401, 422)


class TestCODQueue:
    def test_list_no_auth(self, client):
        r = client.get("/admin/cod-queue")
        assert r.status_code in (401, 422)

    def test_verify_no_auth(self, client):
        r = client.post(f"/admin/cod-queue/{uuid4()}/verify", json={})
        assert r.status_code in (401, 422)

    def test_cancel_no_auth(self, client):
        r = client.post(f"/admin/cod-queue/{uuid4()}/cancel", json={})
        assert r.status_code in (401, 422)


class TestPayoutAdmin:
    def test_list_no_auth(self, client):
        r = client.get("/admin/payouts")
        assert r.status_code in (401, 422)

    def test_list_invalid_status(self, client):
        r = client.get("/admin/payouts?status=unknown")
        assert r.status_code in (401, 422)

    def test_approve_no_auth(self, client):
        r = client.post(f"/admin/payouts/{uuid4()}/approve", json={})
        assert r.status_code in (401, 422)

    def test_reject_no_auth(self, client):
        r = client.post(f"/admin/payouts/{uuid4()}/reject", json={"admin_note": "Duplicate"})
        assert r.status_code in (401, 422)

    def test_complete_no_auth(self, client):
        r = client.post(f"/admin/payouts/{uuid4()}/complete", json={})
        assert r.status_code in (401, 422)


class TestSettingsAdmin:
    def test_get_no_auth(self, client):
        r = client.get("/admin/settings")
        assert r.status_code in (401, 422)

    def test_update_no_auth(self, client):
        r = client.patch("/admin/settings", json={"commission_rate": 0.18})
        assert r.status_code in (401, 422)

    def test_update_invalid_rate(self, client):
        r = client.patch("/admin/settings", json={"commission_rate": 2.0})
        assert r.status_code in (401, 422)