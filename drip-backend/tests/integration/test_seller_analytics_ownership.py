"""Real two-seller HTTP analytics, inventory scoping and threshold contracts."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace

import pytest
from sqlalchemy import select
from test_marketplace_regressions import market as marketplace_fixture
from test_resource_ownership import headers, request

from app.models.analytics import AnalyticsEvent
from app.models.order import Order, OrderItem, OrderStatus, SellerOrder, SellerOrderStatus
from app.models.product import Product, ProductInventory, ProductVariant, SizeType
from app.models.seller import Seller, SellerStatus
from app.models.user import User, UserRole
from app.models.wallet import CommissionLedger

pytestmark = pytest.mark.integration
market = marketplace_fixture
PERIODS = ("7d", "30d", "90d", "1y")


@pytest.fixture
async def sellers(db, market):
    other_user = User(
        email="analytics-other@example.com",
        password_hash="synthetic-only",
        role=UserRole.seller,
        has_verified_email=True,
    )
    db.add(other_user)
    await db.flush()
    other = Seller(
        user_id=other_user.id,
        brand_name="Private Analytics Brand",
        slug="analytics-other",
        status=SellerStatus.active,
        total_slots=50,
    )
    db.add(other)
    await db.flush()
    product = Product(
        seller_id=other.id,
        name="Private analytics product",
        slug="analytics-other",
        price=1000,
        is_published=False,
        view_count=5,
    )
    db.add(product)
    await db.flush()
    variant = ProductVariant(
        product_id=product.id,
        sku="ANALYTICS-OTHER",
        size_type=SizeType.alpha,
        size_value="M",
        colour="Blue",
    )
    db.add(variant)
    await db.flush()
    inventory = ProductInventory(variant_id=variant.id, stock=17, reserved=2, reorder_point=20)
    market.inventory.stock, market.inventory.reserved, market.inventory.reorder_point = 8, 2, 10
    market.product.view_count = 2
    db.add(inventory)
    rows = [
        SimpleNamespace(
            user=market.seller_user,
            seller=market.seller,
            product=market.product,
            variant=market.variant,
            inventory=market.inventory,
            subtotal=1000,
            gross=800,
            commission=160,
            net=640,
            units=2,
            views=2,
            available=6,
        ),
        SimpleNamespace(
            user=other_user,
            seller=other,
            product=product,
            variant=variant,
            inventory=inventory,
            subtotal=7000,
            gross=7000,
            commission=1400,
            net=5600,
            units=7,
            views=5,
            available=15,
        ),
    ]
    when = datetime.now(UTC) - timedelta(days=2)
    order = Order(
        order_number="WHZ-ANALYTICS",
        user_id=market.buyer.id,
        status=OrderStatus.completed,
        subtotal=8000,
        total=8000,
        shipping_fee=0,
        payment_method="cod",
        created_at=when,
    )
    db.add(order)
    await db.flush()
    ledgers, events = [], []
    for row in rows:
        seller_order = SellerOrder(
            order_id=order.id,
            seller_id=row.seller.id,
            subtotal=row.subtotal,
            status=SellerOrderStatus.delivered,
        )
        db.add(seller_order)
        await db.flush()
        db.add(
            OrderItem(
                order_id=order.id,
                seller_id=row.seller.id,
                product_id=row.product.id,
                variant_id=row.variant.id,
                product_name=row.product.name,
                variant_label="M",
                unit_price=Decimal(row.subtotal) / row.units,
                quantity=row.units,
                subtotal=row.subtotal,
            )
        )
        refunded = row.subtotal - row.gross
        ledger = CommissionLedger(
            seller_order_id=seller_order.id,
            seller_id=row.seller.id,
            gross_amount=row.subtotal,
            commission_rate=Decimal("0.2"),
            commission_amount=Decimal(row.subtotal) * Decimal("0.2"),
            seller_amount=Decimal(row.subtotal) * Decimal("0.8"),
            refunded_gross_amount=refunded,
            reversed_commission_amount=Decimal(refunded) * Decimal("0.2"),
            reversed_seller_amount=Decimal(refunded) * Decimal("0.8"),
            recovered_seller_amount=Decimal(refunded) * Decimal("0.8"),
            settled_at=when,
        )
        ledgers.append(ledger)
        events.extend(
            AnalyticsEvent(kind="product_view", product_id=row.product.id, created_at=when)
            for _ in range(row.views)
        )
    db.add_all([*ledgers, *events])
    await db.commit()
    return SimpleNamespace(rows=rows, order=order, ledgers=ledgers, events=events)


async def get(client, redis, row, path, **params):
    response = await request(client, redis, row.user, "GET", path, params=params)
    assert response.status_code == 200, response.text
    return response.json()


@pytest.mark.parametrize("period", PERIODS)
async def test_seller_overview_counts_only_owned_sales_and_views(
    client, isolated_redis, sellers, period
):
    for row in sellers.rows:
        data = await get(client, isolated_redis, row, "/seller/analytics/overview", period=period)
        assert data == {
            "period": period,
            "gross_revenue": f"{row.gross:.2f}",
            "commission_paid": f"{row.commission:.2f}",
            "net_earnings": f"{row.net:.2f}",
            "order_count": 1,
            "units_sold": row.units,
            "avg_order_value": f"{row.gross:.2f}",
            "total_views": row.views,
            "conversion_rate": round(100 / row.views, 2),
        }


@pytest.mark.parametrize("granularity", ["day", "week", "month"])
async def test_revenue_buckets_stay_seller_scoped(client, isolated_redis, sellers, granularity):
    for period in PERIODS:
        for row in sellers.rows:
            data = await get(
                client,
                isolated_redis,
                row,
                "/seller/analytics/revenue",
                period=period,
                granularity=granularity,
            )
            assert data["period"] == period and data["granularity"] == granularity
            assert len(data["data"]) == 1
            assert {k: data["data"][0][k] for k in ("gross", "commission", "net", "orders")} == {
                "gross": f"{row.gross:.2f}",
                "commission": f"{row.commission:.2f}",
                "net": f"{row.net:.2f}",
                "orders": 1,
            }


@pytest.mark.parametrize("sort_by", ["revenue", "units", "views"])
async def test_top_products_never_expose_other_brands(client, isolated_redis, sellers, sort_by):
    for period in PERIODS:
        for row in sellers.rows:
            data = await get(
                client,
                isolated_redis,
                row,
                "/seller/analytics/top-products",
                period=period,
                sort_by=sort_by,
                limit=1,
            )
            assert len(data["data"]) == 1
            item = data["data"][0]
            assert item["product_id"] == str(row.product.id)
            assert item["product_name"] == row.product.name
            assert item["revenue"] == f"{row.subtotal:.2f}" and item["units_sold"] == row.units
            assert item["views"] == row.views


async def test_health_and_low_stock_filters_are_owned(client, db, isolated_redis, sellers):
    before = list((await db.execute(select(ProductInventory.__table__))).all())
    for index, row in enumerate(sellers.rows):
        other = sellers.rows[1 - index]
        health = await get(client, isolated_redis, row, "/seller/analytics/inventory-health")
        assert health == {
            "total_variants": 1,
            "in_stock": 1,
            "low_stock": 1,
            "out_of_stock": 0,
            "total_units": row.available,
        }
        alerts = await get(client, isolated_redis, row, "/seller/inventory/low-stock")
        assert alerts["total"] == 1 and alerts["data"][0]["variant_id"] == str(row.variant.id)
        for params in (
            {"product_id": str(other.product.id)},
            {"q": other.variant.sku},
            {"q": other.product.name},
            {"product_id": str(other.product.id), "q": row.variant.sku},
        ):
            result = await get(
                client,
                isolated_redis,
                row,
                "/seller/inventory",
                low_stock_only=True,
                page=1,
                per_page=1,
                **params,
            )
            assert result["total"] == 0 and result["data"] == []
        own = await get(
            client,
            isolated_redis,
            row,
            "/seller/inventory",
            low_stock_only=True,
            q=row.variant.sku,
            page=1,
            per_page=1,
        )
        assert own["total"] == 1 and own["data"][0]["variant_id"] == str(row.variant.id)
        page_two = await get(
            client,
            isolated_redis,
            row,
            "/seller/inventory",
            low_stock_only=True,
            page=2,
            per_page=1,
        )
        assert page_two["total"] == 1 and page_two["data"] == []
    assert list((await db.execute(select(ProductInventory.__table__))).all()) == before


async def test_seller_claim_and_query_cannot_redirect_aggregates(client, isolated_redis, sellers):
    for index, row in enumerate(sellers.rows):
        other = sellers.rows[1 - index]
        for path in (
            "/seller/analytics/overview",
            "/seller/analytics/revenue",
            "/seller/analytics/top-products",
            "/seller/analytics/inventory-health",
            "/seller/inventory/low-stock",
        ):
            expected = await get(client, isolated_redis, row, path)
            await isolated_redis.flushdb()
            response = await client.get(
                "/api/v1" + path,
                headers=headers(row.user, seller_id=str(other.seller.id)),
                params={"seller_id": str(other.seller.id)},
            )
            assert response.status_code == 200 and response.json() == expected


async def test_analytics_period_filters_work_for_each_seller(client, db, isolated_redis, sellers):
    older = datetime.now(UTC) - timedelta(days=45)
    sellers.order.created_at = older
    for ledger in sellers.ledgers:
        ledger.settled_at = older
    for event in sellers.events:
        event.created_at = older
    await db.commit()
    for row in sellers.rows:
        for period in PERIODS:
            included = period in {"90d", "1y"}
            overview = await get(
                client, isolated_redis, row, "/seller/analytics/overview", period=period
            )
            assert overview["gross_revenue"] == f"{row.gross if included else 0:.2f}"
            assert overview["units_sold"] == (row.units if included else 0)
            assert overview["total_views"] == (row.views if included else 0)
            series = await get(
                client, isolated_redis, row, "/seller/analytics/revenue", period=period
            )
            assert len(series["data"]) == int(included)
            products = await get(
                client, isolated_redis, row, "/seller/analytics/top-products", period=period
            )
            assert products["data"][0]["revenue"] == f"{row.subtotal if included else 0:.2f}"


@pytest.mark.parametrize(
    "stock,reserved,threshold,low,out",
    [
        (8, 0, 10, 1, 0),
        (4, 0, 0, 0, 0),
        (8, 3, 5, 1, 0),
        (0, 0, 0, 0, 1),
        (8, 0, 8, 1, 0),
        (8, 0, 7, 0, 0),
    ],
)
async def test_inventory_health_uses_saved_reorder_point(
    client, db, market, isolated_redis, stock, reserved, threshold, low, out
):
    market.inventory.stock = stock
    market.inventory.reserved = reserved
    market.inventory.reorder_point = threshold
    await db.commit()
    row = SimpleNamespace(user=market.seller_user)
    health = await get(client, isolated_redis, row, "/seller/analytics/inventory-health")
    assert health == {
        "total_variants": 1,
        "in_stock": int(stock > reserved),
        "low_stock": low,
        "out_of_stock": out,
        "total_units": stock - reserved,
    }
    alerts = await get(client, isolated_redis, row, "/seller/inventory/low-stock")
    assert alerts["total"] == low + out


async def test_health_excludes_inactive_and_deleted_products(client, db, market, isolated_redis):
    row = SimpleNamespace(user=market.seller_user)
    market.variant.is_active = False
    await db.commit()
    empty = {
        "total_variants": 0,
        "in_stock": 0,
        "low_stock": 0,
        "out_of_stock": 0,
        "total_units": 0,
    }
    assert await get(client, isolated_redis, row, "/seller/analytics/inventory-health") == empty
    market.variant.is_active = True
    market.product.deleted_at = datetime.now(UTC)
    await db.commit()
    assert await get(client, isolated_redis, row, "/seller/analytics/inventory-health") == empty
    assert (await get(client, isolated_redis, row, "/seller/inventory/low-stock"))["data"] == []
