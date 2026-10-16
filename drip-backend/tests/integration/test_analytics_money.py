"""Native PostgreSQL to HTTP evidence for fractional-PKR analytics."""

from datetime import UTC, datetime
from decimal import Decimal

import pytest
from sqlalchemy import select
from test_marketplace_regressions import market as marketplace_fixture
from test_resource_ownership import request
from test_seller_analytics_ownership import sellers as sellers_fixture

from app.models.order import Order, OrderAddress, OrderItem, SellerOrder
from app.models.wallet import CommissionLedger, WalletTransaction

pytestmark = pytest.mark.integration
market = marketplace_fixture
sellers = sellers_fixture


def address(order_id, city):
    return OrderAddress(
        order_id=order_id,
        city=city,
        recipient_name="Synthetic",
        phone="03001234567",
        street="Test street",
        province="Punjab",
    )


@pytest.fixture
async def fractional(db, market, sellers):
    # One shared two-seller order, including a partial refund on the first ledger.
    sellers.order.subtotal = sellers.order.total = Decimal("17.06")
    specs = [
        ("10.05", "2.01", "8.04", "2.02", "0.40", "1.62"),
        ("7.01", "1.40", "5.61", "0", "0", "0"),
    ]
    for row, ledger, spec in zip(sellers.rows, sellers.ledgers, specs, strict=True):
        gross, commission, net, refund, reversed_commission, reversed_net = map(Decimal, spec)
        ledger.gross_amount, ledger.commission_amount, ledger.seller_amount = gross, commission, net
        ledger.refunded_gross_amount = refund
        ledger.reversed_commission_amount = reversed_commission
        ledger.reversed_seller_amount = ledger.recovered_seller_amount = reversed_net
        seller_order = await db.get(SellerOrder, ledger.seller_order_id)
        seller_order.subtotal = gross
        item = await db.scalar(
            select(OrderItem).where(
                OrderItem.order_id == sellers.order.id, OrderItem.seller_id == row.seller.id
            )
        )
        item.quantity, item.unit_price, item.subtotal = 1, gross, gross
    when = sellers.order.created_at
    second = Order(
        order_number="WHZ-MONEY-2",
        user_id=market.buyer.id,
        status="completed",
        subtotal=Decimal("10.02"),
        total=Decimal("10.02"),
        shipping_fee=0,
        payment_method="payfast",
        created_at=when,
    )
    db.add(second)
    await db.flush()
    so = SellerOrder(
        order_id=second.id,
        seller_id=market.seller.id,
        subtotal=Decimal("10.02"),
        status="delivered",
    )
    db.add(so)
    await db.flush()
    db.add_all(
        [
            OrderItem(
                order_id=second.id,
                seller_id=market.seller.id,
                product_id=market.product.id,
                variant_id=market.variant.id,
                product_name="Synthetic",
                variant_label="M",
                unit_price=Decimal("10.02"),
                quantity=1,
                subtotal=Decimal("10.02"),
            ),
            CommissionLedger(
                seller_order_id=so.id,
                seller_id=market.seller.id,
                gross_amount=Decimal("10.02"),
                commission_rate=Decimal("0.2"),
                commission_amount=Decimal("2.00"),
                seller_amount=Decimal("8.02"),
                settled_at=when,
            ),
            address(sellers.order.id, "Karachi"),
            address(second.id, "Lahore"),
            WalletTransaction(
                seller_id=market.seller.id,
                type="debit_adjustment",
                amount=Decimal("0.45"),
                balance_after=0,
                reference="slot-purchase:precision-test",
                created_at=when,
            ),
        ]
    )
    market.seller.registration_fee = Decimal("2.35")
    market.seller.registration_paid_at = when
    await db.commit()
    return sellers


CASES = [
    (
        "seller",
        "overview",
        {
            "gross_revenue": "18.05",
            "commission_paid": "3.61",
            "net_earnings": "14.44",
            "avg_order_value": "9.03",
        },
    ),
    (
        "seller",
        "revenue",
        {"data.0.gross": "18.05", "data.0.commission": "3.61", "data.0.net": "14.44"},
    ),
    ("seller", "top-products", {"data.0.revenue": "20.07"}),
    (
        "admin",
        "platform",
        {
            "total_gmv": "27.08",
            "commission_revenue": "5.01",
            "slot_revenue": "2.80",
            "avg_order_value": "13.54",
        },
    ),
    (
        "admin",
        "revenue",
        {"data.0.gross": "25.06", "data.0.commission": "5.01", "data.0.net": "20.05"},
    ),
    (
        "admin",
        "top-sellers",
        {
            "data.0.gmv": "18.05",
            "data.0.commission": "3.61",
            "data.1.gmv": "7.01",
            "data.1.commission": "1.40",
        },
    ),
    ("admin", "payment-methods", {"cod.total": "17.06", "payfast.total": "10.02"}),
    ("admin", "cities", {"data.0.total_gmv": "17.06", "data.1.total_gmv": "10.02"}),
]


def at(data, path):
    for part in path.split("."):
        data = data[int(part)] if isinstance(data, list) else data[part]
    return data


async def snapshot(db):
    return [
        list((await db.execute(select(model.__table__).order_by(model.id))).all())
        for model in (Order, OrderItem, SellerOrder, CommissionLedger, WalletTransaction)
    ]


@pytest.mark.parametrize("role,endpoint,expected", CASES)
async def test_fractional_money_survives_database_to_http(
    role,
    endpoint,
    expected,
    fractional,
    market,
    db,
    client,
    isolated_redis,
):
    before = await snapshot(db)
    user = market.admin if role == "admin" else market.seller_user
    response = await request(client, isolated_redis, user, "GET", f"/{role}/analytics/{endpoint}")
    assert response.status_code == 200, response.text
    data = response.json()
    for path, amount in expected.items():
        assert at(data, path) == amount, (path, data)
    if endpoint == "overview":
        assert type(data["order_count"]) is int and data["order_count"] == 2
        assert Decimal(data["gross_revenue"]) == Decimal(data["commission_paid"]) + Decimal(
            data["net_earnings"]
        )
    elif endpoint == "revenue":
        row = data["data"][0]
        assert type(row["orders"]) is int
        assert Decimal(row["gross"]) == Decimal(row["commission"]) + Decimal(row["net"])
    elif endpoint == "payment-methods":
        assert data["cod"]["share"] == 63.0 and data["payfast"]["share"] == 37.0
        assert type(data["cod"]["share"]) is float
    elif endpoint == "cities":
        assert data["data"][0]["share"] == 63.0
    assert await snapshot(db) == before


@pytest.mark.parametrize("endpoint", ["payment-methods", "cities"])
async def test_sub_rupee_totals_keep_nonzero_shares(
    endpoint,
    db,
    market,
    client,
    isolated_redis,
):
    for index, (amount, method, city) in enumerate(
        [("0.01", "cod", "Karachi"), ("0.03", "payfast", "Lahore")]
    ):
        order = Order(
            order_number=f"WHZ-TINY-{index}",
            user_id=market.buyer.id,
            status="completed",
            subtotal=Decimal(amount),
            total=Decimal(amount),
            shipping_fee=0,
            payment_method=method,
            created_at=datetime.now(UTC),
        )
        db.add(order)
        await db.flush()
        db.add(address(order.id, city))
    await db.commit()
    response = await request(
        client, isolated_redis, market.admin, "GET", f"/admin/analytics/{endpoint}"
    )
    assert response.status_code == 200, response.text
    data = response.json()
    if endpoint == "payment-methods":
        assert (data["cod"]["total"], data["cod"]["share"]) == ("0.01", 25.0)
        assert (data["payfast"]["total"], data["payfast"]["share"]) == ("0.03", 75.0)
    else:
        assert [(row["total_gmv"], row["share"]) for row in data["data"]] == [
            ("0.03", 75.0),
            ("0.01", 25.0),
        ]


@pytest.mark.parametrize("role,endpoint,expected", CASES)
async def test_empty_money_reports_have_stable_types(
    role, endpoint, expected, market, client, isolated_redis
):
    user = market.admin if role == "admin" else market.seller_user
    response = await request(client, isolated_redis, user, "GET", f"/{role}/analytics/{endpoint}")
    assert response.status_code == 200, response.text
    data = response.json()
    if endpoint in ("revenue", "cities"):
        assert data["data"] == []
    else:
        for path in expected:
            if path.startswith("data.1."):
                continue  # Only the market's seller exists in this empty fixture.
            assert at(data, path) == "0.00"
