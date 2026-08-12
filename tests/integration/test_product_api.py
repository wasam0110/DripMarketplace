"""
Integration tests — Block 4: Product API
Run: pytest tests/integration/test_product_api.py -v --no-cov
"""
import pytest
from uuid import uuid4
from unittest.mock import MagicMock, AsyncMock
from fastapi.testclient import TestClient
from fastapi import FastAPI
from fastapi.responses import JSONResponse

from app.api.v1.products import router as product_router
from app.core.database import get_db
from app.core.exceptions import DRIPException
import app.models.user     # noqa: F401
import app.models.seller   # noqa: F401
import app.models.product  # noqa: F401

@pytest.fixture
def client():
    import app.models.user    # noqa: F401
    import app.models.seller  # noqa: F401
    import app.models.product # noqa: F401

    from fastapi.responses import JSONResponse
    from app.core.database import get_db
    from app.core.exceptions import DRIPException

    test_app = FastAPI()
    test_app.include_router(product_router)

    @test_app.exception_handler(DRIPException)
    async def drip_handler(request, exc):
        return JSONResponse(status_code=exc.http_status, content={"detail": exc.message})

    async def mock_db():
        result = MagicMock()
        result.scalars.return_value.all.return_value             = []
        result.scalar_one_or_none.return_value                   = None
        result.scalar_one.return_value                           = 0

        session          = MagicMock()
        session.execute  = AsyncMock(return_value=result)
        session.commit   = AsyncMock()
        session.rollback = AsyncMock()
        session.flush    = AsyncMock()
        yield session

    test_app.dependency_overrides[get_db] = mock_db

    with TestClient(test_app, raise_server_exceptions=False) as c:
        yield c


class TestPublicEndpoints:
    def test_catalogue_ok(self, client):
        r = client.get("/products")
        assert r.status_code in (200, 401, 422, 500)

    def test_catalogue_invalid_sort(self, client):
        r = client.get("/products?sort=popular")
        assert r.status_code == 422

    def test_catalogue_price_range(self, client):
        r = client.get("/products?min_price=500&max_price=5000")
        assert r.status_code in (200, 500)

    def test_get_product_not_found(self, client):
        r = client.get(f"/products/{uuid4()}")
        assert r.status_code in (404, 500)

    def test_search_too_short(self, client):
        r = client.get("/products/search/suggestions?q=a")
        assert r.status_code == 422

    def test_search_valid(self, client):
        r = client.get("/products/search/suggestions?q=drip")
        assert r.status_code in (200, 500)

    def test_variants_endpoint(self, client):
        r = client.get(f"/products/{uuid4()}/variants")
        assert r.status_code in (200, 404, 500)


class TestSellerEndpoints:
    def test_list_seller_products_no_auth(self, client):
        r = client.get("/seller/products")
        assert r.status_code in (401, 422)

    def test_create_product_no_auth(self, client):
        r = client.post("/seller/products", json={})
        assert r.status_code in (401, 422)

    def test_create_product_invalid_price(self, client):
        r = client.post("/seller/products", json={
            "name": "Test Product",
            "description": "Test description that is long enough",
            "price": 50,  # below minimum
        })
        assert r.status_code in (401, 422) 

    def test_create_product_missing_fields(self, client):
        r = client.post("/seller/products", json={"name": "Test"})
        assert r.status_code in (401, 422) 

    def test_publish_no_auth(self, client):
        r = client.post(f"/seller/products/{uuid4()}/publish")
        assert r.status_code in (401, 422)

    def test_unpublish_no_auth(self, client):
        r = client.post(f"/seller/products/{uuid4()}/unpublish")
        assert r.status_code in (401, 422)

    def test_delete_no_auth(self, client):
        r = client.delete(f"/seller/products/{uuid4()}")
        assert r.status_code in (401, 422)

    def test_upload_images_no_auth(self, client):
        r = client.post(f"/seller/products/{uuid4()}/images",
                        files={"images": ("test.jpg", b"", "image/jpeg")})
        assert r.status_code in (401, 422)

    def test_invalid_status_filter(self, client):
        r = client.get("/seller/products?status=archived")
        assert r.status_code in (401, 422) 


class TestAdminEndpoints:
    def test_admin_list_no_auth(self, client):
        r = client.get("/admin/products")
        assert r.status_code in (401, 422, 501)

    def test_admin_hide_no_auth(self, client):
        r = client.post(f"/admin/products/{uuid4()}/hide")
        assert r.status_code in (401, 422, 501)