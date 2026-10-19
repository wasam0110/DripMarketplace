"""Typed seller-order reads preserve exact checkout values and brand boundaries."""

from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select
from test_marketplace_regressions import ADDRESS, guest_payload
from test_marketplace_regressions import market as marketplace_fixture
from test_resource_ownership import headers, snapshot

from app.models.order import Order, OrderAddress, SellerOrder, SellerOrderStatus
from app.models.product import Product, ProductInventory, ProductVariant, SizeType
from app.models.seller import Seller, SellerStatus
from app.models.user import User, UserRole
from app.schemas.order import CartItemInput
from app.services.order_service import OrderService

pytestmark = pytest.mark.integration
market = marketplace_fixture
ROW_KEYS = {
    "id",
    "order_id",
    "order_number",
    "status",
    "subtotal",
    "tracking_number",
    "courier_name",
    "shipped_at",
    "delivered_at",
    "created_at",
}


@pytest.fixture
async def fulfilment(db, market):
    other_user = User(
        email="fulfilment-other@example.com",
        password_hash="synthetic-only",
        role=UserRole.seller,
        has_verified_email=True,
    )
    db.add(other_user)
    await db.flush()
    other = Seller(
        user_id=other_user.id,
        brand_name="Other fulfilment brand",
        slug="fulfilment-other",
        status=SellerStatus.active,
        total_slots=50,
    )
    db.add(other)
    await db.flush()
    product = Product(
        seller_id=other.id,
        name="Other item",
        slug="fulfilment-other",
        price=Decimal("700.05"),
        is_published=True,
    )
    db.add(product)
    await db.flush()
    variant = ProductVariant(
        product_id=product.id,
        sku="FULFILMENT-OTHER",
        size_type=SizeType.alpha,
        size_value="M",
        colour="Blue",
    )
    db.add(variant)
    await db.flush()
    db.add(ProductInventory(variant_id=variant.id, stock=20, reserved=0))
    market.product.sale_price = Decimal("1200.75")
    await db.commit()
    payload = guest_payload(market)
    payload.items.append(CartItemInput(variant_id=variant.id, quantity=3))
    created = await OrderService(db).create_guest_order(payload)
    order = await db.get(Order, created.order_id)
    seller_orders = list(
        (await db.scalars(select(SellerOrder).where(SellerOrder.order_id == order.id))).all()
    )
    by_seller = {so.seller_id: so for so in seller_orders}
    return SimpleNamespace(
        order=order,
        token=created.guest_token,
        rows=[
            (
                market.seller_user,
                by_seller[market.seller.id],
                "1200.75",
                2,
                "2401.50",
                market.product.name,
            ),
            (other_user, by_seller[other.id], "700.05", 3, "2100.15", product.name),
        ],
    )


async def test_exact_two_brand_reads_match_checkout_without_mutation(client, db, fulfilment):
    before = await snapshot(db)
    customer = await client.get(
        f"/api/v1/orders/{fulfilment.order.id}",
        headers={"X-Guest-Token": fulfilment.token},
    )
    assert customer.status_code == 200, customer.text
    assert Decimal(customer.json()["subtotal"]) == Decimal("4501.65")
    for user, so, price, quantity, subtotal, name in fulfilment.rows:
        listed = await client.get("/api/v1/seller/orders", headers=headers(user))
        assert listed.status_code == 200, listed.text
        page = listed.json()
        assert page["pagination"] == {"page": 1, "per_page": 25, "total": 1, "total_pages": 1}
        row = page["data"][0]
        assert set(row) == ROW_KEYS
        assert row["id"] == str(so.id) and row["order_id"] == str(fulfilment.order.id)
        assert row["subtotal"] == subtotal
        assert row["created_at"] == so.created_at.isoformat()
        detail = await client.get(f"/api/v1/seller/orders/{so.id}", headers=headers(user))
        assert detail.status_code == 200, detail.text
        data = detail.json()
        assert set(data) == ROW_KEYS | {"shipping_address", "items"}
        assert {key: data[key] for key in ROW_KEYS} == row
        assert data["shipping_address"] == {**ADDRESS, "note": None}
        assert len(data["items"]) == 1
        item = data["items"][0]
        assert set(item) == {"product_name", "variant_label", "unit_price", "quantity", "subtotal"}
        assert item["product_name"] == name
        assert (item["unit_price"], item["quantity"], item["subtotal"]) == (
            price,
            quantity,
            subtotal,
        )
        own_customer_item = next(
            i for i in customer.json()["items"] if i["seller_id"] == str(so.seller_id)
        )
        assert Decimal(item["unit_price"]) == Decimal(own_customer_item["unit_price"])
        assert Decimal(item["subtotal"]) == Decimal(own_customer_item["subtotal"])
    assert await snapshot(db) == before


async def test_foreign_and_missing_seller_order_ids_remain_404(client, db, fulfilment):
    user, own, *_ = fulfilment.rows[0]
    other_user, foreign, *_ = fulfilment.rows[1]
    before = await snapshot(db)
    for actor, target in [(user, foreign.id), (other_user, own.id), (user, uuid4())]:
        response = await client.get(f"/api/v1/seller/orders/{target}", headers=headers(actor))
        assert response.status_code == 404, response.text
        assert response.json()["error"]["code"] == "NOT_FOUND"
    assert await snapshot(db) == before


@pytest.mark.parametrize("actor,status", [(None, 401), ("buyer", 403), ("admin", 403)])
async def test_seller_read_role_boundaries(client, market, fulfilment, actor, status):
    auth = headers(getattr(market, actor)) if actor else {}
    for path in ["/api/v1/seller/orders", f"/api/v1/seller/orders/{fulfilment.rows[0][1].id}"]:
        response = await client.get(path, headers=auth)
        assert response.status_code == status, response.text


@pytest.mark.parametrize("query", ["status=shipped", "page=2"])
async def test_empty_filtered_or_later_pages_keep_shape(client, fulfilment, query):
    user = fulfilment.rows[0][0]
    response = await client.get(f"/api/v1/seller/orders?{query}", headers=headers(user))
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["data"] == []
    assert result["pagination"] == {
        "page": 2 if query == "page=2" else 1,
        "per_page": 25,
        "total": 1 if query == "page=2" else 0,
        "total_pages": 1,
    }


async def test_invalid_filter_and_page_still_reject(client, fulfilment):
    for query in ["page=0", "status=unsupported"]:
        response = await client.get(
            f"/api/v1/seller/orders?{query}",
            headers=headers(fulfilment.rows[0][0]),
        )
        assert response.status_code == 422, response.text


@pytest.mark.parametrize("state", ["shipped", "delivered"])
async def test_tracking_and_timestamp_fields_survive_response_validation(
    client, db, fulfilment, state
):
    user, so, *_ = fulfilment.rows[0]
    when = datetime(2026, 10, 18, 9, 10, 11, 123456, tzinfo=UTC)
    so.status = SellerOrderStatus(state)
    so.tracking_number, so.courier_name = "SYNTHETIC-TRACK", "Synthetic courier"
    so.shipped_at = when
    so.delivered_at = when if state == "delivered" else None
    await db.commit()
    response = await client.get(f"/api/v1/seller/orders/{so.id}", headers=headers(user))
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["status"] == state
    assert data["tracking_number"] == "SYNTHETIC-TRACK"
    assert data["courier_name"] == "Synthetic courier"
    assert data["shipped_at"] == when.isoformat()
    assert data["delivered_at"] == (when.isoformat() if state == "delivered" else None)


async def test_legacy_missing_address_keeps_empty_fallback(client, db, fulfilment):
    address = await db.scalar(
        select(OrderAddress).where(OrderAddress.order_id == fulfilment.order.id)
    )
    await db.delete(address)
    await db.commit()
    db.expire(fulfilment.order, ["address"])
    user, so, *_ = fulfilment.rows[0]
    response = await client.get(f"/api/v1/seller/orders/{so.id}", headers=headers(user))
    assert response.status_code == 200, response.text
    assert response.json()["shipping_address"] == {
        "recipient_name": "",
        "phone": "",
        "city": "",
        "province": "",
        "street": "",
        "note": None,
    }


async def test_pagination_crosses_25_rows_without_cross_seller_leakage(client, db, fulfilment):
    user, first, *_ = fulfilment.rows[0]
    for index in range(25):
        order = Order(
            order_number=f"WHZ-READ-PAGE-{index}",
            guest_email="pagination@example.com",
            subtotal=Decimal("100.25"),
            total=Decimal("100.25"),
            shipping_fee=0,
            payment_method="cod",
        )
        db.add(order)
        await db.flush()
        db.add(
            SellerOrder(order_id=order.id, seller_id=first.seller_id, subtotal=Decimal("100.25"))
        )
    await db.commit()
    pages = []
    for page in (1, 2):
        response = await client.get(f"/api/v1/seller/orders?page={page}", headers=headers(user))
        assert response.status_code == 200, response.text
        data = response.json()
        assert data["pagination"] == {"page": page, "per_page": 25, "total": 26, "total_pages": 2}
        assert len(data["data"]) == (25 if page == 1 else 1)
        pages.extend(data["data"])
    ids = {UUID(item["id"]) for item in pages}
    assert len(ids) == 26 and first.id in ids
    assert fulfilment.rows[1][1].id not in ids
