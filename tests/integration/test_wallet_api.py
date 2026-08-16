"""Integration tests — Block 7: Wallet API."""
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

from app.api.v1.wallet import router as wallet_router
from app.core.database import get_db
from app.core.exceptions import DRIPException


@pytest.fixture
def client():
    test_app = FastAPI()
    test_app.include_router(wallet_router)

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
        yield session

    test_app.dependency_overrides[get_db] = mock_db
    with TestClient(test_app, raise_server_exceptions=False) as c:
        yield c


class TestSellerWalletEndpoints:
    def test_summary_no_auth(self, client):
        r = client.get("/seller/wallet")
        assert r.status_code in (401, 422)

    def test_transactions_no_auth(self, client):
        r = client.get("/seller/wallet/transactions")
        assert r.status_code in (401, 422)

    def test_transactions_invalid_type(self, client):
        r = client.get("/seller/wallet/transactions?tx_type=unknown")
        assert r.status_code == 422

    def test_withdraw_no_auth(self, client):
        r = client.post("/seller/wallet/withdraw", json={
            "amount": 500,
            "bank_account_id": str(uuid4()),
        })
        assert r.status_code in (401, 422)

    def test_withdraw_below_minimum(self, client):
        r = client.post("/seller/wallet/withdraw", json={
            "amount": 499,
            "bank_account_id": str(uuid4()),
        })
        assert r.status_code == 422

    def test_withdraw_zero(self, client):
        r = client.post("/seller/wallet/withdraw", json={
            "amount": 0,
            "bank_account_id": str(uuid4()),
        })
        assert r.status_code == 422

    def test_payouts_no_auth(self, client):
        r = client.get("/seller/wallet/payouts")
        assert r.status_code in (401, 422)

    def test_payouts_invalid_status(self, client):
        r = client.get("/seller/wallet/payouts?status=unknown")
        assert r.status_code == 422

    def test_commission_no_auth(self, client):
        r = client.get("/seller/wallet/commission-breakdown")
        assert r.status_code in (401, 422)


class TestAdminWalletEndpoints:
    def test_overview_no_auth(self, client):
        r = client.get("/admin/wallet/overview")
        assert r.status_code in (401, 422)

    def test_admin_payouts_no_auth(self, client):
        r = client.get("/admin/wallet/payouts")
        assert r.status_code in (401, 422)

    def test_admin_payouts_invalid_status(self, client):
        r = client.get("/admin/wallet/payouts?status=unknown")
        assert r.status_code == 422

    def test_approve_no_auth(self, client):
        r = client.post(f"/admin/wallet/payouts/{uuid4()}/approve", json={})
        assert r.status_code in (401, 422)

    def test_reject_no_auth(self, client):
        r = client.post(f"/admin/wallet/payouts/{uuid4()}/reject", json={})
        assert r.status_code in (401, 422)