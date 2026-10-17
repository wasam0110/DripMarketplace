"""Exact coupon previews agree with authoritative native checkout amounts."""

from decimal import Decimal
from uuid import UUID

import pytest
from sqlalchemy import func, select
from test_marketplace_regressions import ADDRESS
from test_marketplace_regressions import market as marketplace_fixture
from test_resource_ownership import headers

from app.core.exceptions import BusinessRuleError
from app.models.coupon import Coupon, CouponUsage, DiscountType
from app.models.order import Order, SellerOrder
from app.models.product import Product, ProductInventory, ProductVariant, SizeType
from app.models.seller import Seller, SellerStatus
from app.models.user import User, UserRole
from app.services.coupon_service import CouponService

pytestmark = pytest.mark.integration
market = marketplace_fixture


async def setup_coupon(db, market, kind="percentage", value="12.50", price="100.05", minimum="0"):
    market.product.price = Decimal(price)
    market.product.sale_price = None
    coupon = Coupon(
        code="FRACTION",
        discount_type=DiscountType(kind),
        discount_value=Decimal(value),
        min_order_amount=Decimal(minimum),
        max_uses_per_customer=1,
    )
    db.add(coupon)
    await db.commit()
    return coupon


async def preview(client, market, subtotal):
    return await client.post(
        "/api/v1/coupons/validate",
        headers=headers(market.buyer),
        json={"code": "fraction", "subtotal": subtotal},
    )


async def checkout(client, redis, market):
    await redis.hset(f"cart:{market.buyer.id}", str(market.variant.id), 1)
    return await client.post(
        "/api/v1/orders",
        headers=headers(market.buyer),
        json={
            "shipping_address": ADDRESS,
            "payment_method": "cod",
            "coupon_code": "fraction",
        },
    )


@pytest.mark.parametrize(
    "kind,value,price,discount",
    [
        ("percentage", "12.50", "100.05", "12.51"),
        ("percentage", "10.00", "100.05", "10.01"),
        ("percentage", "0.50", "101.00", "0.51"),
        ("fixed", "2.75", "100.05", "2.75"),
        ("fixed", "200.25", "100.05", "100.05"),
    ],
)
async def test_fractional_preview_matches_persisted_checkout(
    kind,
    value,
    price,
    discount,
    db,
    market,
    client,
    isolated_redis,
):
    coupon = await setup_coupon(db, market, kind, value, price)
    response = await preview(client, market, price)
    assert response.status_code == 200, response.text
    expected_net = Decimal(price) - Decimal(discount)
    assert response.json() == {
        "code": "FRACTION",
        "discount_type": kind,
        "discount_value": value,
        "discount_amount": discount,
        "new_subtotal": f"{expected_net:.2f}",
    }
    assert await db.scalar(select(func.count(CouponUsage.id))) == 0
    await db.refresh(coupon)
    assert coupon.uses_count == 0
    created = await checkout(client, isolated_redis, market)
    assert created.status_code == 201, created.text
    order = await db.get(Order, UUID(created.json()["order_id"]))
    seller_order = await db.scalar(select(SellerOrder).where(SellerOrder.order_id == order.id))
    assert order.subtotal == Decimal(price)
    assert order.discount_amount == Decimal(discount)
    assert seller_order.subtotal == expected_net
    assert order.total == expected_net + order.shipping_fee
    assert order.total == Decimal(created.json()["total"])
    await db.refresh(coupon)
    await db.refresh(market.inventory)
    assert coupon.uses_count == 1 and market.inventory.reserved == 1
    assert await db.scalar(select(func.count(CouponUsage.id))) == 1
    repeat = await preview(client, market, price)
    assert repeat.status_code == 422 and "already used" in repeat.text
    assert await db.scalar(select(func.count(CouponUsage.id))) == 1


@pytest.mark.parametrize(
    "subtotal,allowed", [("100.74", False), ("100.75", True), ("100.76", True)]
)
async def test_fractional_minimum_is_identical_for_preview_and_checkout(
    subtotal,
    allowed,
    db,
    market,
    client,
    isolated_redis,
):
    coupon = await setup_coupon(db, market, "fixed", "0.75", subtotal, "100.75")
    response = await preview(client, market, subtotal)
    assert response.status_code == (200 if allowed else 422), response.text
    if not allowed:
        assert "100.75" in response.text
    created = await checkout(client, isolated_redis, market)
    assert created.status_code == (201 if allowed else 422), created.text
    await db.refresh(coupon)
    await db.refresh(market.inventory)
    assert coupon.uses_count == int(allowed)
    assert market.inventory.reserved == int(allowed)
    assert await db.scalar(select(func.count(Order.id))) == int(allowed)
    assert await db.scalar(select(func.count(CouponUsage.id))) == int(allowed)
    if not allowed:
        assert "100.75" in created.text
        assert await isolated_redis.hgetall(f"cart:{market.buyer.id}")


@pytest.mark.parametrize("new_price", ["100.74", "200.05"])
async def test_checkout_rechecks_price_after_successful_preview(
    new_price,
    db,
    market,
    client,
    isolated_redis,
):
    coupon = await setup_coupon(db, market, price="100.75", minimum="100.75")
    estimate = await preview(client, market, "100.75")
    assert estimate.status_code == 200, estimate.text
    assert estimate.json()["discount_amount"] == "12.59"
    market.product.price = Decimal(new_price)
    await db.commit()
    created = await checkout(client, isolated_redis, market)
    await db.refresh(coupon)
    await db.refresh(market.inventory)
    if new_price == "100.74":
        assert created.status_code == 422, created.text
        assert "100.75" in created.text
        assert coupon.uses_count == 0 and market.inventory.reserved == 0
        assert await db.scalar(select(func.count(Order.id))) == 0
        assert await db.scalar(select(func.count(CouponUsage.id))) == 0
        assert await isolated_redis.hgetall(f"cart:{market.buyer.id}")
    else:
        assert created.status_code == 201, created.text
        order = await db.get(Order, UUID(created.json()["order_id"]))
        assert order.subtotal == Decimal("200.05")
        assert order.discount_amount == Decimal("25.01")
        assert order.total == Decimal("175.04") + order.shipping_fee
        assert coupon.uses_count == 1 and market.inventory.reserved == 1
        assert await db.scalar(select(func.count(CouponUsage.id))) == 1


@pytest.mark.parametrize(
    "kind,value,discount,brand_count",
    [
        ("percentage", "12.50", "37.53", 2),
        ("fixed", "500.25", "300.22", 2),
        ("fixed", "0.04", "0.04", 6),
        ("fixed", "600.26", "600.26", 6),
    ],
)
async def test_multi_brand_checkout_conserves_fractional_discount(
    kind,
    value,
    discount,
    brand_count,
    db,
    market,
    client,
    isolated_redis,
):
    coupon = await setup_coupon(db, market, kind, value, "100.05")
    seller_prices = {market.seller.id: Decimal("100.05")}
    inventories = [market.inventory]
    for index in range(brand_count - 1):
        other_user = User(
            email=f"coupon-other-{index}@example.test",
            password_hash="test-only",
            role=UserRole.seller,
            has_verified_email=True,
        )
        db.add(other_user)
        await db.flush()
        other_seller = Seller(
            user_id=other_user.id,
            brand_name=f"Other Coupon Brand {index}",
            slug=f"other-coupon-brand-{index}",
            status=SellerStatus.active,
            total_slots=50,
        )
        db.add(other_seller)
        await db.flush()
        price = Decimal("200.17" if brand_count == 2 else "100.05")
        seller_prices[other_seller.id] = price
        other_product = Product(
            seller_id=other_seller.id,
            name="Other Shirt",
            slug=f"other-shirt-{index}",
            price=price,
            is_published=True,
        )
        db.add(other_product)
        await db.flush()
        other_variant = ProductVariant(
            product_id=other_product.id,
            sku=f"OTHER-COUPON-{index}",
            size_type=SizeType.alpha,
            size_value="M",
            colour="Black",
        )
        db.add(other_variant)
        await db.flush()
        other_inventory = ProductInventory(variant_id=other_variant.id, stock=5, reserved=0)
        db.add(other_inventory)
        inventories.append(other_inventory)
        await isolated_redis.hset(f"cart:{market.buyer.id}", str(other_variant.id), 1)
    await db.commit()
    subtotal = sum(seller_prices.values())
    response = await preview(client, market, str(subtotal))
    assert response.status_code == 200, response.text
    assert response.json()["discount_amount"] == discount
    created = await checkout(client, isolated_redis, market)
    assert created.status_code == 201, created.text
    order = await db.get(Order, UUID(created.json()["order_id"]))
    seller_orders = (
        await db.scalars(select(SellerOrder).where(SellerOrder.order_id == order.id))
    ).all()
    assert {row.seller_id for row in seller_orders} == set(seller_prices)
    assert all(0 <= row.subtotal <= seller_prices[row.seller_id] for row in seller_orders)
    assert order.subtotal == subtotal
    assert order.discount_amount == Decimal(discount)
    assert sum(row.subtotal for row in seller_orders) + order.discount_amount == order.subtotal
    assert order.total == order.subtotal - order.discount_amount + order.shipping_fee
    assert Decimal(response.json()["new_subtotal"]) == order.subtotal - order.discount_amount
    await db.refresh(coupon)
    assert coupon.uses_count == 1
    for inventory in inventories:
        await db.refresh(inventory)
        assert inventory.reserved == 1
    assert await db.scalar(select(func.count(CouponUsage.id))) == 1


@pytest.mark.parametrize(
    "subtotal", ["1.001", "10000000000.00", "NaN", "Infinity", "-Infinity", "0", "-1"]
)
async def test_preview_rejects_invalid_money_without_usage(subtotal, db, market, client):
    coupon = await setup_coupon(db, market)
    response = await preview(client, market, subtotal)
    assert response.status_code == 422, response.text
    await db.refresh(coupon)
    assert coupon.uses_count == 0
    assert await db.scalar(select(func.count(CouponUsage.id))) == 0


@pytest.mark.parametrize("subtotal,allowed", [("100.74", False), ("100.75", True)])
async def test_legacy_apply_helper_keeps_fractional_minimum(subtotal, allowed, db, market):
    coupon = await setup_coupon(db, market, "fixed", "0.75", subtotal, "100.75")
    order = Order(
        order_number="WHZ-COUPON-DIRECT",
        user_id=market.buyer.id,
        status="completed",
        payment_method="cod",
        subtotal=Decimal(subtotal),
        total=Decimal(subtotal),
        shipping_fee=0,
    )
    db.add(order)
    await db.commit()
    if allowed:
        discount = await CouponService(db).apply_to_order(
            "FRACTION", Decimal(subtotal), market.buyer.id, order.id
        )
        assert discount == Decimal("0.75")
        await db.commit()
    else:
        with pytest.raises(BusinessRuleError, match="100.75"):
            await CouponService(db).apply_to_order(
                "FRACTION", Decimal(subtotal), market.buyer.id, order.id
            )
    await db.refresh(coupon)
    assert coupon.uses_count == int(allowed)
    assert await db.scalar(select(func.count(CouponUsage.id))) == int(allowed)
