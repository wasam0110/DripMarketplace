"""Native product HTTP regressions: real rows/auth and exact application outcomes.

Uses the shared disposable TEST_DATABASE_URL fixture, never a mocked database.
"""

from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select
from test_marketplace_regressions import market as marketplace_fixture
from test_resource_ownership import headers

from app.models.product import Product, ProductImage, ProductInventory, ProductVariant

pytestmark = pytest.mark.integration
market = marketplace_fixture
BASE = "/api/v1"
VALID_PRODUCT = {
    "name": "Synthetic product",
    "description": "A synthetic product for boundary verification",
    "price": 100,
}


async def snapshot(db):
    return [
        sorted(
            tuple(map(str, row))
            for row in (await db.execute(select(*model.__table__.columns))).all()
        )
        for model in (Product, ProductImage, ProductVariant, ProductInventory)
    ]


def assert_error(response, status, code, fields=()):
    assert response.status_code == status, response.text
    error = response.json()["error"]
    assert error["code"] == code
    assert error["message"]
    assert set(fields) <= set(error.get("fields", {}))


async def test_empty_catalogue_returns_documented_page(client):
    response = await client.get(BASE + "/products")
    assert response.status_code == 200, response.text
    assert response.json() == {
        "data": [],
        "pagination": {"next_cursor": None, "has_next": False, "limit": 20},
    }


async def test_catalogue_returns_seeded_public_product(client, market):
    response = await client.get(BASE + "/products")
    assert response.status_code == 200, response.text
    body = response.json()
    assert [row["id"] for row in body["data"]] == [str(market.product.id)]
    assert body["data"][0]["price"] == "1500.00"
    assert body["data"][0]["sale_price"] == "1200.00"
    assert body["pagination"] == {"next_cursor": None, "has_next": False, "limit": 20}


async def test_catalogue_invalid_sort_is_validation_not_server_error(client, db, market):
    before = await snapshot(db)
    response = await client.get(BASE + "/products", params={"sort": "popular"})
    assert_error(response, 422, "VALIDATION_ERROR", ["query → sort"])
    assert await snapshot(db) == before


@pytest.mark.parametrize(
    "low,high,included", [(500, 5000, True), (1200, 1200, True), (1300, 5000, False)]
)
async def test_catalogue_price_range_filters_effective_price(client, market, low, high, included):
    response = await client.get(BASE + "/products", params={"min_price": low, "max_price": high})
    assert response.status_code == 200, response.text
    assert [row["id"] for row in response.json()["data"]] == (
        [str(market.product.id)] if included else []
    )


@pytest.mark.parametrize("suffix", ["", "/variants"])
async def test_missing_product_returns_not_found(client, suffix):
    response = await client.get(f"{BASE}/products/{uuid4()}{suffix}")
    assert_error(response, 404, "NOT_FOUND")


async def test_search_too_short_is_validation_error(client):
    response = await client.get(BASE + "/products/search/suggestions", params={"q": "a"})
    assert_error(response, 422, "VALIDATION_ERROR", ["query → q"])


@pytest.mark.parametrize(
    "query,product_match,brand_match",
    [("linen", True, False), ("Test Brand", False, True), ("absent", False, False)],
)
async def test_search_returns_expected_suggestions(
    client, market, query, product_match, brand_match
):
    response = await client.get(BASE + "/products/search/suggestions", params={"q": query})
    assert response.status_code == 200, response.text
    body = response.json()
    assert set(body) == {"products", "brands"}
    assert [row["id"] for row in body["products"]] == (
        [str(market.product.id)] if product_match else []
    )
    assert [row["id"] for row in body["brands"]] == ([str(market.seller.id)] if brand_match else [])
    if product_match:
        assert body["products"][0]["price"] == "1200.00"


async def test_variants_return_real_price_and_stock(client, market):
    response = await client.get(f"{BASE}/products/{market.product.id}/variants")
    assert response.status_code == 200, response.text
    assert response.json() == [
        {
            "id": str(market.variant.id),
            "sku": "TEST-M",
            "size_type": "alpha",
            "size_value": "M",
            "colour": "Ivory",
            "price": "1200.00",
            "stock": 8,
            "available_stock": 8,
            "is_active": True,
        }
    ]


@pytest.mark.parametrize(
    "method,path",
    [
        ("GET", "/seller/products"),
        ("POST", "/seller/products"),
        ("POST", "/seller/products/{id}/publish"),
        ("POST", "/seller/products/{id}/unpublish"),
        ("DELETE", "/seller/products/{id}"),
        ("POST", "/seller/products/{id}/images"),
        ("GET", "/admin/products"),
        ("POST", "/admin/products/{id}/hide"),
    ],
)
async def test_protected_product_routes_require_auth_without_mutation(
    client, db, market, method, path
):
    before = await snapshot(db)
    kwargs = {}
    if path.endswith("/images"):
        client.headers.pop("Content-Type", None)
        kwargs["files"] = {"images": ("test.jpg", b"\xff\xd8\xff", "image/jpeg")}
    elif method == "POST":
        kwargs["json"] = VALID_PRODUCT if path == "/seller/products" else {}
    response = await client.request(method, BASE + path.format(id=market.product.id), **kwargs)
    assert_error(response, 401, "UNAUTHORIZED")
    assert await snapshot(db) == before


@pytest.mark.parametrize(
    "payload,fields",
    [
        ({**VALID_PRODUCT, "price": 50}, {"price"}),
        ({"name": "Test"}, {"description", "price"}),
    ],
)
async def test_authenticated_product_validation_rejects_named_fields(
    client, db, market, payload, fields
):
    auth = headers(market.seller_user)
    control = await client.get(BASE + "/seller/products", headers=auth)
    assert control.status_code == 200, control.text
    before = await snapshot(db)
    response = await client.post(BASE + "/seller/products", headers=auth, json=payload)
    assert_error(response, 422, "VALIDATION_ERROR", fields)
    assert await snapshot(db) == before


async def test_valid_authenticated_product_is_persisted(client, db, market):
    response = await client.post(
        BASE + "/seller/products", headers=headers(market.seller_user), json=VALID_PRODUCT
    )
    assert response.status_code == 201, response.text
    body = response.json()
    stored = await db.get(Product, UUID(body["id"]))
    assert stored.seller_id == market.seller.id
    assert stored.name == VALID_PRODUCT["name"]
    assert stored.price == Decimal("100.00")
    assert body["price"] == "100.00"
    assert not stored.is_published


async def test_authenticated_invalid_status_filter_is_validation_error(client, db, market):
    before = await snapshot(db)
    response = await client.get(
        BASE + "/seller/products",
        headers=headers(market.seller_user),
        params={"status": "archived"},
    )
    assert_error(response, 422, "VALIDATION_ERROR", ["query → status"])
    assert await snapshot(db) == before


@pytest.mark.parametrize("status,included", [("all", True), ("published", True), ("draft", False)])
async def test_authenticated_status_filter_returns_correct_products(
    client, market, status, included
):
    response = await client.get(
        BASE + "/seller/products", headers=headers(market.seller_user), params={"status": status}
    )
    assert response.status_code == 200, response.text
    assert [row["id"] for row in response.json()["data"]] == (
        [str(market.product.id)] if included else []
    )


async def test_admin_can_list_and_hide_product(client, db, market):
    auth = headers(market.admin)
    listing = await client.get(BASE + "/admin/products", headers=auth)
    assert listing.status_code == 200, listing.text
    assert [row["id"] for row in listing.json()["data"]] == [str(market.product.id)]
    hidden = await client.post(f"{BASE}/admin/products/{market.product.id}/hide", headers=auth)
    assert hidden.status_code == 200, hidden.text
    await db.refresh(market.product)
    assert market.product.admin_hidden is True
    public = await client.get(f"{BASE}/products/{market.product.id}")
    assert_error(public, 404, "NOT_FOUND")
