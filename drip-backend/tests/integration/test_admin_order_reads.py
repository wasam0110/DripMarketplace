"""Admin order reads keep exact snapshots, filtered totals and strict permissions."""

from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy import select
from test_marketplace_regressions import market as marketplace_fixture
from test_resource_ownership import headers

from app.models.order import (
    Order,
    OrderAddress,
    OrderItem,
    OrderStatus,
    SellerOrder,
    SellerOrderStatus,
    StoredPaymentMethod,
)
from app.models.product import Product, ProductInventory, ProductVariant, SizeType
from app.models.seller import Seller, SellerStatus
from app.models.user import User, UserRole
from app.models.wallet import CommissionLedger

pytestmark = pytest.mark.integration
market = marketplace_fixture
WHEN = datetime(2026, 10, 28, tzinfo=UTC)


@pytest.fixture
async def orders(db, market):
    user = User(
        email="admin-orders-other@example.test",
        password_hash="synthetic-only",
        role=UserRole.seller,
        has_verified_email=True,
    )
    db.add(user)
    await db.flush()
    seller = Seller(
        user_id=user.id,
        brand_name="Second Brand",
        slug="admin-orders-other",
        status=SellerStatus.suspended,
    )
    db.add(seller)
    await db.flush()
    product = Product(
        seller_id=seller.id,
        name="Current product name",
        slug="admin-order-other",
        price=Decimal("900.99"),
        is_published=False,
    )
    db.add(product)
    await db.flush()
    variant = ProductVariant(
        product_id=product.id,
        sku="ADMIN-OTHER",
        size_type=SizeType.alpha,
        size_value="S",
        colour="Blue",
    )
    db.add(variant)
    await db.flush()
    rows, splits = {}, {}
    for name, status, method, subtotal, discount, shipping, guest in [
        (
            "multi",
            OrderStatus.processing,
            StoredPaymentMethod.cod,
            "1700.55",
            "100.05",
            "200.25",
            False,
        ),
        (
            "guest",
            OrderStatus.pending_cod_verification,
            StoredPaymentMethod.cod,
            "500.50",
            "0",
            "200.25",
            True,
        ),
        (
            "online",
            OrderStatus.pending_payment,
            StoredPaymentMethod.payfast,
            "500.50",
            "0",
            "0",
            False,
        ),
        ("legacy", OrderStatus.completed, StoredPaymentMethod.card, "300.30", "0", "0", True),
    ]:
        order = Order(
            user_id=None if guest else market.buyer.id,
            guest_email="guest-orders@example.test" if guest else None,
            guest_name="Guest Buyer" if guest else None,
            guest_phone="03001234567" if guest else None,
            order_number=f"WHZ-ADMIN-{name}",
            status=status,
            payment_method=method,
            subtotal=Decimal(subtotal),
            discount_amount=Decimal(discount),
            shipping_fee=Decimal(shipping),
            total=Decimal(subtotal) - Decimal(discount) + Decimal(shipping),
            notes="Saved checkout note",
            created_at=WHEN,
            checkout_key_hash=("a" if name == "multi" else name[0]) * 64,
            checkout_request_hash="b" * 64,
        )
        db.add(order)
        await db.flush()
        if name != "legacy":
            db.add(
                OrderAddress(
                    order_id=order.id,
                    recipient_name="Snapshot Recipient",
                    phone="03001234567",
                    street="1 Test Street",
                    city="Lahore",
                    province="Punjab",
                    note="Saved delivery note",
                )
            )
        allocations = [
            (
                market.seller.id,
                market.product.id,
                market.variant.id,
                "1000.25" if name == "multi" else subtotal,
            )
        ]
        if name == "multi":
            allocations.append((seller.id, product.id, variant.id, "700.30"))
        splits[name] = []
        for index, (seller_id, product_id, variant_id, amount) in enumerate(allocations):
            db.add(
                OrderItem(
                    order_id=order.id,
                    seller_id=seller_id,
                    product_id=product_id,
                    variant_id=variant_id,
                    product_name=f"Saved checkout item {index}",
                    variant_label="M / Ivory",
                    unit_price=Decimal(amount),
                    quantity=1,
                    subtotal=Decimal(amount),
                )
            )
            split = SellerOrder(
                order_id=order.id,
                seller_id=seller_id,
                status=SellerOrderStatus.shipped if index else SellerOrderStatus.processing,
                subtotal=Decimal(amount),
                tracking_number="SAVED-TRACK" if index else None,
                courier_name="Test Courier" if index else None,
                shipped_at=WHEN if index else None,
            )
            db.add(split)
            await db.flush()
            splits[name].append(split)
            if name == "multi":
                commission = Decimal("100.03" if index == 0 else "70.03")
                db.add(
                    CommissionLedger(
                        seller_order_id=split.id,
                        seller_id=seller_id,
                        gross_amount=Decimal(amount),
                        commission_rate=Decimal("0.1"),
                        commission_amount=commission,
                        seller_amount=Decimal(amount) - commission,
                        refunded_gross_amount=Decimal("200") if index == 0 else Decimal(0),
                        reversed_commission_amount=Decimal("20") if index == 0 else Decimal(0),
                        reversed_seller_amount=Decimal("180") if index == 0 else Decimal(0),
                    )
                )
        rows[name] = order
    await db.commit()
    return SimpleNamespace(rows=rows, other=seller, splits=splits)


async def snapshot(db):
    state = {}
    for model in (
        Order,
        OrderAddress,
        OrderItem,
        SellerOrder,
        CommissionLedger,
        ProductInventory,
        Product,
    ):
        state[model.__tablename__] = sorted(
            tuple(map(str, row))
            for row in (await db.execute(select(*model.__table__.columns))).all()
        )
    return state


@pytest.mark.parametrize("role", ["guest", "buyer", "seller_user", "unverified"])
@pytest.mark.parametrize("detail", [False, True])
async def test_only_verified_admin_reads(client, db, market, orders, role, detail):
    if role == "unverified":
        market.admin.has_verified_email = False
        await db.commit()
    before = await snapshot(db)
    auth = (
        {}
        if role == "guest"
        else headers(market.admin if role == "unverified" else getattr(market, role))
    )
    response = await client.get(
        "/api/v1/admin/orders" + (f"/{orders.rows['multi'].id}" if detail else ""), headers=auth
    )
    assert response.status_code in (401, 403), response.text
    assert await snapshot(db) == before


@pytest.mark.parametrize(
    "params,names",
    [
        ({}, {"multi", "guest", "online", "legacy"}),
        ({"status": "processing"}, {"multi"}),
        ({"payment_method": "cod"}, {"multi", "guest"}),
        ({"payment_method": "payfast"}, {"online"}),
        ({"status": "completed"}, {"legacy"}),
        ({"seller_id": "other"}, {"multi"}),
        ({"seller_id": "own", "payment_method": "cod"}, {"multi", "guest"}),
        ({"seller_id": "missing"}, set()),
        ({"status": "processing", "payment_method": "payfast"}, set()),
    ],
)
async def test_filters_whole_order_totals_and_no_mutation(
    client, db, market, orders, params, names
):
    params = dict(params)
    if "seller_id" in params:
        params["seller_id"] = str(
            orders.other.id
            if params["seller_id"] == "other"
            else market.seller.id
            if params["seller_id"] == "own"
            else uuid4()
        )
    before = await snapshot(db)
    response = await client.get(
        "/api/v1/admin/orders", headers=headers(market.admin), params=params
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["total"] == payload["totals"]["order_count"] == len(names)
    assert payload["per_page"] == 25 and payload["total_pages"] == 1
    expected = sorted((orders.rows[name] for name in names), key=lambda row: row.id, reverse=True)
    assert [row["id"] for row in payload["data"]] == [str(row.id) for row in expected]
    assert Decimal(payload["totals"]["total_gmv"]) == sum(
        (row.total for row in expected), Decimal(0)
    )
    assert Decimal(payload["totals"]["total_commission"]) == (
        Decimal("150.06") if "multi" in names else Decimal(0)
    )
    for row in payload["data"]:
        order = next(item for item in expected if str(item.id) == row["id"])
        assert Decimal(row["total"]) == order.total
        assert Decimal(row["commission"]) == (
            Decimal("150.06") if order.id == orders.rows["multi"].id else Decimal(0)
        )
        assert row["seller_count"] == len(
            orders.splits[next(name for name, value in orders.rows.items() if value.id == order.id)]
        )
    assert await snapshot(db) == before


async def test_detail_is_private_exact_snapshot_with_all_brands(client, db, market, orders):
    before = await snapshot(db)
    response = await client.get(
        f"/api/v1/admin/orders/{orders.rows['multi'].id}", headers=headers(market.admin)
    )
    assert response.status_code == 200, response.text
    detail = response.json()
    assert detail["user_id"] == str(market.buyer.id)
    assert detail["subtotal"] == "1700.55" and detail["total"] == "1800.75"
    assert detail["discount_amount"] == "100.05" and detail["shipping_fee"] == "200.25"
    assert detail["commission"] == "150.06"
    assert detail["address"]["recipient_name"] == "Snapshot Recipient"
    assert {row["product_name"] for row in detail["items"]} == {
        "Saved checkout item 0",
        "Saved checkout item 1",
    }
    assert {row["seller_id"] for row in detail["seller_orders"]} == {
        str(market.seller.id),
        str(orders.other.id),
    }
    shipment = next(
        row for row in detail["seller_orders"] if row["seller_id"] == str(orders.other.id)
    )
    assert shipment["tracking_number"] == "SAVED-TRACK" and shipment["status"] == "shipped"
    assert all(
        secret not in response.text
        for secret in (
            "checkout_key_hash",
            "checkout_request_hash",
            "guest_email",
            "guest_phone",
            "password_hash",
            "access_token",
        )
    )
    assert await snapshot(db) == before


async def test_guest_legacy_missing_address_and_no_ledger(client, db, market, orders):
    response = await client.get(
        f"/api/v1/admin/orders/{orders.rows['legacy'].id}", headers=headers(market.admin)
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["address"] is payload["user_id"] is None
    assert payload["customer_name"] == "Guest Buyer"
    assert payload["payment_method"] == "card" and Decimal(payload["commission"]) == 0
    empty = orders.rows["guest"]
    for row in (await db.scalars(select(OrderItem).where(OrderItem.order_id == empty.id))).all():
        await db.delete(row)
    for row in orders.splits["guest"]:
        await db.delete(row)
    await db.commit()
    await db.refresh(empty, ["items", "seller_orders"])
    response = await client.get(f"/api/v1/admin/orders/{empty.id}", headers=headers(market.admin))
    assert response.status_code == 200
    assert response.json()["items"] == response.json()["seller_orders"] == []


async def test_pages_are_stable_and_keep_matching_totals(client, market, orders):
    all_ids = sorted((str(row.id) for row in orders.rows.values()), reverse=True)
    seen = []
    for page in range(1, 6):
        response = await client.get(
            "/api/v1/admin/orders",
            headers=headers(market.admin),
            params={"page": page, "per_page": 1},
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["page"] == page and payload["per_page"] == 1 and payload["total_pages"] == 4
        assert Decimal(payload["totals"]["total_gmv"]) == Decimal("3302.30")
        seen.extend(row["id"] for row in payload["data"])
    assert seen == all_ids


async def test_seller_filter_does_not_duplicate_parent_order(client, db, market, orders):
    db.add(
        SellerOrder(
            order_id=orders.rows["multi"].id,
            seller_id=orders.other.id,
            status=SellerOrderStatus.pending,
            subtotal=Decimal(0),
        )
    )
    await db.commit()
    response = await client.get(
        "/api/v1/admin/orders",
        headers=headers(market.admin),
        params={"seller_id": str(orders.other.id)},
    )
    assert response.status_code == 200
    assert response.json()["total"] == len(response.json()["data"]) == 1
    assert response.json()["totals"]["total_gmv"] == "1800.75"


@pytest.mark.parametrize(
    "params",
    [
        {"page": 0},
        {"per_page": 0},
        {"per_page": 101},
        {"status": "pending"},
        {"payment_method": "card"},
        {"seller_id": "invalid"},
    ],
)
async def test_invalid_filters(client, market, params):
    response = await client.get(
        "/api/v1/admin/orders", headers=headers(market.admin), params=params
    )
    assert response.status_code == 422


async def test_missing_and_malformed_detail(client, market):
    assert (
        await client.get(f"/api/v1/admin/orders/{uuid4()}", headers=headers(market.admin))
    ).status_code == 404
    assert (
        await client.get("/api/v1/admin/orders/invalid", headers=headers(market.admin))
    ).status_code == 422
