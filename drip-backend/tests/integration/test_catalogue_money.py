"""Catalogue money agrees with stored prices and authoritative checkout."""

from decimal import Decimal
from uuid import UUID

import pytest
from sqlalchemy import select
from test_marketplace_regressions import ADDRESS
from test_marketplace_regressions import market as marketplace_fixture
from test_resource_ownership import headers

from app.models.order import Order, OrderItem
from app.models.product import Product

pytestmark = pytest.mark.integration
market = marketplace_fixture


async def fractional_prices(db, market, sale="1200.75", override="1100.05"):
    market.product.price = Decimal("1500.25")
    market.product.sale_price = Decimal(sale) if sale is not None else None
    market.variant.price_override = Decimal(override) if override is not None else None
    await db.commit()


@pytest.mark.parametrize(
    "endpoint,shape,expected",
    [
        ("/products", "card", "1500.25"),
        ("/products/{id}", "detail", "1500.25"),
        ("/products/slug/linen-shirt", "detail", "1500.25"),
        ("/products/{id}/variants", "variant", "1100.05"),
        ("/products/search/suggestions?q=Linen", "search", "1200.75"),
        ("/seller/products", "row", "1500.25"),
        ("/seller/products/{id}", "detail", "1500.25"),
    ],
)
async def test_catalogue_routes_preserve_paisa(endpoint, shape, expected, db, market, client):
    await fractional_prices(db, market)
    response = await client.get(
        "/api/v1" + endpoint.format(id=market.product.id), headers=headers(market.seller_user)
    )
    assert response.status_code == 200, response.text
    data = response.json()
    item = (
        data["data"][0]
        if shape in {"card", "row"}
        else data["products"][0]
        if shape == "search"
        else data[0]
        if shape == "variant"
        else data
    )
    assert item["price"] == expected
    if shape in {"card", "detail"}:
        assert item["sale_price"] == "1200.75"
    if shape == "detail":
        assert item["variants"][0]["price"] == "1100.05"
        assert type(item["variants"][0]["stock"]) is int
    await db.refresh(market.product)
    await db.refresh(market.variant)
    assert market.product.price == Decimal("1500.25")
    assert market.product.sale_price == Decimal("1200.75")
    assert market.variant.price_override == Decimal("1100.05")


@pytest.mark.parametrize("sale", [None, "1200.75"])
async def test_wishlist_precision_deduplication_and_isolation(sale, db, market, client):
    await fractional_prices(db, market, sale=sale)
    for _ in range(2):
        added = await client.post(
            "/api/v1/customers/me/wishlist",
            headers=headers(market.buyer),
            json={"product_id": str(market.product.id)},
        )
        assert added.status_code == 201, added.text
        assert added.json()["total"] == 1
        item = added.json()["items"][0]
        assert item["price"] == "1500.25"
        assert item["sale_price"] == sale
    own = await client.get("/api/v1/customers/me/wishlist", headers=headers(market.buyer))
    assert own.status_code == 200, own.text
    assert own.json() == added.json()
    other = await client.get("/api/v1/customers/me/wishlist", headers=headers(market.seller_user))
    assert other.status_code == 200, other.text
    assert other.json() == {"items": [], "total": 0}
    market.product.admin_hidden = True
    await db.commit()
    hidden = await client.get("/api/v1/customers/me/wishlist", headers=headers(market.buyer))
    assert hidden.status_code == 200, hidden.text
    assert hidden.json() == {"items": [], "total": 0}


@pytest.mark.parametrize(
    "sale,override,expected",
    [(None, None, "1500.25"), ("1200.75", None, "1200.75"), ("1200.75", "1100.05", "1100.05")],
)
async def test_variant_display_matches_checkout(
    sale,
    override,
    expected,
    db,
    market,
    client,
    isolated_redis,
):
    await fractional_prices(db, market, sale=sale, override=override)
    response = await client.get(f"/api/v1/products/{market.product.id}")
    assert response.status_code == 200, response.text
    assert response.json()["sale_price"] == sale
    shown = response.json()["variants"][0]["price"]
    assert shown == expected
    quote = await client.post(
        "/api/v1/orders/guest/quote",
        json={"items": [{"variant_id": str(market.variant.id), "quantity": 2}]},
    )
    assert quote.status_code == 200, quote.text
    assert Decimal(quote.json()["items"][0]["unit_price"]) == Decimal(shown)
    assert Decimal(quote.json()["subtotal"]) == Decimal(expected) * 2
    await isolated_redis.hset(f"cart:{market.buyer.id}", str(market.variant.id), 2)
    cart = await client.get("/api/v1/cart", headers=headers(market.buyer))
    assert cart.status_code == 200, cart.text
    assert Decimal(cart.json()["items"][0]["unit_price"]) == Decimal(shown)
    created = await client.post(
        "/api/v1/orders",
        headers=headers(market.buyer),
        json={"shipping_address": ADDRESS, "payment_method": "cod"},
    )
    assert created.status_code == 201, created.text
    order = await db.get(Order, UUID(created.json()["order_id"]))
    item = await db.scalar(select(OrderItem).where(OrderItem.order_id == order.id))
    assert item.unit_price == Decimal(shown)
    assert order.subtotal == Decimal(expected) * 2
    assert order.total == order.subtotal + order.shipping_fee
    assert Decimal(created.json()["total"]) == order.total


@pytest.mark.parametrize("sort", ["price_asc", "price_desc"])
async def test_fractional_price_cursors_and_whole_rupee_filters(sort, db, market, client):
    await fractional_prices(db, market, sale="1200.75", override=None)
    # Two equal prices exercise the UUID tie-breaker; all share an integer part.
    for index, price in enumerate(["1200.25", "1200.75"]):
        db.add(
            Product(
                seller_id=market.seller.id,
                name=f"Precision {index}",
                slug=f"precision-{index}",
                price=Decimal(price),
                is_published=True,
            )
        )
    await db.commit()
    seen = []
    prices = []
    params = {"sort": sort, "limit": 1, "min_price": 1200, "max_price": 1201}
    for _ in range(3):
        response = await client.get("/api/v1/products", params=params)
        assert response.status_code == 200, response.text
        data = response.json()
        assert len(data["data"]) == 1
        card = data["data"][0]
        seen.append(card["id"])
        prices.append(card["sale_price"] or card["price"])
        cursor = data["pagination"]["next_cursor"]
        if cursor is None:
            break
        params["cursor"] = cursor
    assert len(seen) == len(set(seen)) == 3
    assert prices == sorted(["1200.25", "1200.75", "1200.75"], reverse=sort == "price_desc")
    assert cursor is None
    excluded = await client.get("/api/v1/products", params={"max_price": 1200})
    assert excluded.status_code == 200, excluded.text
    assert excluded.json()["data"] == []


async def test_seller_whole_rupee_updates_preserve_untouched_fractions(db, market, client):
    await fractional_prices(db, market)
    updated = await client.put(
        f"/api/v1/seller/products/{market.product.id}",
        headers=headers(market.seller_user),
        json={"name": "Updated Linen Shirt"},
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["price"] == "1500.25"
    assert updated.json()["sale_price"] == "1200.75"
    variant = await client.patch(
        f"/api/v1/seller/products/{market.product.id}/variants/{market.variant.id}",
        headers=headers(market.seller_user),
        json={"price_override": 1000},
    )
    assert variant.status_code == 200, variant.text
    assert variant.json()["price"] == "1000.00"
    cleared = await client.patch(
        f"/api/v1/seller/products/{market.product.id}/variants/{market.variant.id}",
        headers=headers(market.seller_user),
        json={"price_override": None},
    )
    assert cleared.status_code == 200, cleared.text
    assert cleared.json()["price"] == "1200.75"
