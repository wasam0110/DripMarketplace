"""Integration tests — Block 11: Analytics API."""
import pytest
from unittest.mock import MagicMock, AsyncMock
from fastapi import FastAPI
from fastapi.testclient import TestClient
from fastapi.responses import JSONResponse

import app.models.user    # noqa
import app.models.seller  # noqa
import app.models.product # noqa
import app.models.order   # noqa
import app.models.wallet  # noqa

from app.api.v1.analytics.seller import router as seller_analytics_router
from app.api.v1.analytics.admin  import router as admin_analytics_router
from app.core.database import get_db
from app.core.exceptions import DRIPException


@pytest.fixture
def client():
    test_app = FastAPI()
    test_app.include_router(seller_analytics_router)
    test_app.include_router(admin_analytics_router)

    @test_app.exception_handler(DRIPException)
    async def drip_handler(request, exc):
        return JSONResponse(status_code=exc.http_status, content={"detail": exc.message})

    result = MagicMock()
    result.scalars.return_value.all.return_value = []
    result.scalar_one_or_none.return_value       = None
    result.scalar_one.return_value               = 0
    result.one.return_value                      = (0, 0, 0, 0)
    result.all.return_value                      = []

    async def mock_db():
        session         = MagicMock()
        session.execute = AsyncMock(return_value=result)
        session.commit  = AsyncMock()
        session.flush   = AsyncMock()
        yield session

    test_app.dependency_overrides[get_db] = mock_db
    with TestClient(test_app, raise_server_exceptions=False) as c:
        yield c


class TestSellerAnalyticsEndpoints:
    def test_overview_no_auth(self, client):
        r = client.get("/seller/analytics/overview")
        assert r.status_code in (401, 422)

    def test_overview_invalid_period(self, client):
        r = client.get("/seller/analytics/overview?period=5y")
        assert r.status_code in (401, 422)

    def test_revenue_no_auth(self, client):
        r = client.get("/seller/analytics/revenue")
        assert r.status_code in (401, 422)

    def test_revenue_invalid_granularity(self, client):
        r = client.get("/seller/analytics/revenue?granularity=hour")
        assert r.status_code in (401, 422)

    def test_top_products_no_auth(self, client):
        r = client.get("/seller/analytics/top-products")
        assert r.status_code in (401, 422)

    def test_top_products_invalid_sort(self, client):
        r = client.get("/seller/analytics/top-products?sort_by=profit")
        assert r.status_code in (401, 422)

    def test_inventory_health_no_auth(self, client):
        r = client.get("/seller/analytics/inventory-health")
        assert r.status_code in (401, 422)


class TestAdminAnalyticsEndpoints:
    def test_platform_no_auth(self, client):
        r = client.get("/admin/analytics/platform")
        assert r.status_code in (401, 422)

    def test_platform_invalid_period(self, client):
        r = client.get("/admin/analytics/platform?period=2y")
        assert r.status_code in (401, 422)

    def test_revenue_no_auth(self, client):
        r = client.get("/admin/analytics/revenue")
        assert r.status_code in (401, 422)

    def test_top_sellers_no_auth(self, client):
        r = client.get("/admin/analytics/top-sellers")
        assert r.status_code in (401, 422)

    def test_cohort_no_auth(self, client):
        r = client.get("/admin/analytics/cohort")
        assert r.status_code in (401, 422)

    def test_cohort_over_limit(self, client):
        r = client.get("/admin/analytics/cohort?months=13")
        assert r.status_code in (401, 422)

    def test_payment_methods_no_auth(self, client):
        r = client.get("/admin/analytics/payment-methods")
        assert r.status_code in (401, 422)

    def test_cities_no_auth(self, client):
        r = client.get("/admin/analytics/cities")
        assert r.status_code in (401, 422)

    def test_conversion_no_auth(self, client):
        r = client.get("/admin/analytics/conversion")
        assert r.status_code in (401, 422)

    def test_search_queries_no_auth(self, client):
        r = client.get("/admin/analytics/search-queries")
        assert r.status_code in (401, 422)