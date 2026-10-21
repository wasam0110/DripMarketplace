"""Checkout deduplication/price acceptance on disposable native PostgreSQL schemas."""

import asyncio
import importlib.util
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import func, select, text, update
from sqlalchemy.ext.asyncio import async_sessionmaker
from test_marketplace_regressions import ADDRESS, guest_payload
from test_marketplace_regressions import market as market_fixture
from test_resource_ownership import headers

from app.core.exceptions import ConflictError, NotFoundError
from app.models.order import Order, OrderItem
from app.models.product import Product, ProductInventory
from app.schemas.order import (
    AccountCheckoutQuoteRequest,
    CheckoutOrderRequest,
    GuestCheckoutOrderRequest,
    GuestCheckoutQuoteRequest,
)
from app.services.order_access import guest_token_matches
from app.services.order_service import OrderService

pytestmark = pytest.mark.integration
market = market_fixture


async def accepted_guest(service, data):
    quote = await service.quote_guest_checkout(GuestCheckoutQuoteRequest(items=data.items))
    return GuestCheckoutOrderRequest(
        **data.model_dump(), checkout_key=uuid4(), quote_token=quote.quote_token
    )


async def test_guest_replay_and_recovery_do_not_repeat_side_effects(db, market, monkeypatch):
    enqueue = AsyncMock()
    monkeypatch.setattr(OrderService, "_enqueue_cod_timeout", enqueue)
    service = OrderService(db)
    payload = await accepted_guest(service, guest_payload(market))
    first = await service.create_checkout(payload)
    again = await service.create_checkout(payload)
    recovered = await service.recover_checkout(payload.checkout_key)
    assert first.order_id == again.order_id == recovered.order_id
    assert guest_token_matches(recovered.guest_token, first.order_id)
    assert await db.scalar(select(func.count(Order.id))) == 1
    assert await db.scalar(select(func.count(OrderItem.id))) == 1
    await db.refresh(market.inventory)
    assert market.inventory.reserved == 2
    enqueue.assert_awaited_once()
    with pytest.raises(ConflictError) as error:
        await service.create_checkout(payload.model_copy(update={"notes": "changed"}))
    assert error.value.code == "CHECKOUT_KEY_REUSED"


async def test_account_replays_after_cart_clear_and_recovery_is_owner_scoped(
    db, market, isolated_redis
):
    await isolated_redis.hset(f"cart:{market.buyer.id}", str(market.variant.id), 2)
    service = OrderService(db, isolated_redis)
    quote = await service.quote_account_checkout(AccountCheckoutQuoteRequest(), market.buyer.id)
    payload = CheckoutOrderRequest(
        shipping_address=ADDRESS,
        payment_method="cod",
        checkout_key=uuid4(),
        quote_token=quote.quote_token,
    )
    first = await service.create_checkout(payload, market.buyer.id)
    assert await isolated_redis.hgetall(f"cart:{market.buyer.id}") == {}
    assert (await service.create_checkout(payload, market.buyer.id)).order_id == first.order_id
    for other in (None, market.admin.id):
        with pytest.raises(NotFoundError):
            await service.recover_checkout(payload.checkout_key, other)
    assert (
        await service.recover_checkout(payload.checkout_key, market.buyer.id)
    ).guest_token is None


async def test_price_change_rejected_before_inventory_or_order_write(db, market):
    service = OrderService(db)
    data = guest_payload(market)
    payload = await accepted_guest(service, data)
    await db.execute(
        update(Product).where(Product.id == market.product.id).values(sale_price=Decimal("1300"))
    )
    await db.commit()
    with pytest.raises(ConflictError) as error:
        await service.create_checkout(payload)
    assert error.value.code == "CHECKOUT_QUOTE_CHANGED"
    assert await db.scalar(select(func.count(Order.id))) == 0
    assert await db.scalar(select(ProductInventory.reserved)) == 0
    fresh = await accepted_guest(service, data)
    assert (await service.create_checkout(fresh)).total == Decimal("2800")


async def test_changed_quantity_or_payment_rejected_and_guest_key_expiry_never_duplicates(
    db, market
):
    service = OrderService(db)
    payload = await accepted_guest(service, guest_payload(market))
    changed = payload.model_copy(deep=True)
    changed.items[0].quantity = 1
    with pytest.raises(ConflictError):
        await service.create_checkout(changed)
    created = await service.create_checkout(payload)
    await db.execute(
        update(Order)
        .where(Order.id == created.order_id)
        .values(created_at=datetime.now(UTC) - timedelta(days=2))
    )
    await db.commit()
    with pytest.raises(ConflictError) as error:
        await service.create_checkout(payload)
    assert error.value.code == "CHECKOUT_RECOVERY_EXPIRED"
    assert await db.scalar(select(func.count(Order.id))) == 1


async def test_http_creation_requires_guards_and_recovery_uses_body_not_url(client, db, market):
    body = guest_payload(market).model_dump(mode="json")
    assert (await client.post("/api/v1/orders/guest", json=body)).status_code == 422
    quote = await client.post("/api/v1/orders/guest/quote", json={"items": body["items"]})
    assert quote.status_code == 200, quote.text
    key = str(uuid4())
    body.update(checkout_key=key, quote_token=quote.json()["quote_token"])
    first = await client.post("/api/v1/orders/guest", json=body)
    assert first.status_code == 201, first.text
    replay = await client.post("/api/v1/orders/guest", json=body)
    assert replay.status_code == 201, replay.text
    assert replay.json()["order_id"] == first.json()["order_id"]
    recovery = await client.post("/api/v1/orders/guest/recover", json={"checkout_key": key})
    assert recovery.status_code == 200, recovery.text
    assert recovery.json()["order_id"] == first.json()["order_id"]
    denied = await client.post(
        "/api/v1/orders/recover", headers=headers(market.buyer), json={"checkout_key": key}
    )
    assert denied.status_code == 404


async def test_native_concurrent_same_key_has_one_order_and_reservation(test_engine, monkeypatch):
    # Independent sessions and real commits: no shared transaction/savepoint illusion.
    factory = async_sessionmaker(test_engine, expire_on_commit=False)
    monkeypatch.setattr(OrderService, "_enqueue_cod_timeout", AsyncMock())
    async with factory() as seed:
        seeded = await market_fixture.__wrapped__(seed)
        variant_id = seeded.variant.id
        payload = await accepted_guest(OrderService(seed), guest_payload(seeded))
    gate = asyncio.Event()

    async def submit():
        async with factory() as session:
            await gate.wait()
            try:
                return await OrderService(session).create_checkout(payload)
            except ConflictError as error:
                assert error.code == "CHECKOUT_IN_PROGRESS"
                return None

    tasks = [asyncio.create_task(submit()) for _ in range(2)]
    gate.set()
    results = await asyncio.gather(*tasks)
    ids = {result.order_id for result in results if result}
    assert len(ids) == 1
    async with factory() as session:
        replay = await OrderService(session).create_checkout(payload)
        assert replay.order_id in ids
        assert await session.scalar(select(func.count(Order.id))) == 1
        assert (
            await session.scalar(
                select(ProductInventory.reserved).where(ProductInventory.variant_id == variant_id)
            )
            == 2
        )


async def test_migration_021_round_trip_preserves_historical_order(db, market, monkeypatch):
    created = await OrderService(db).create_guest_order(guest_payload(market))
    path = Path(__file__).parents[2] / "alembic" / "versions" / "021_checkout_safeguards.py"
    spec = importlib.util.spec_from_file_location("checkout_migration", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    connection = await db.connection()

    def migrate(sync_connection):
        monkeypatch.setattr(module, "op", Operations(MigrationContext.configure(sync_connection)))
        module.downgrade()
        module.upgrade()

    await connection.run_sync(migrate)
    row = (
        await db.execute(
            text("SELECT total, checkout_key_hash FROM orders WHERE id = :id"),
            {"id": created.order_id},
        )
    ).one()
    assert row.total == Decimal("2600")
    assert row.checkout_key_hash is None


async def test_post_commit_response_failure_can_be_recovered(db, market, monkeypatch):
    service = OrderService(db)
    payload = await accepted_guest(service, guest_payload(market))
    original = service.create_guest_order

    async def lose_response(*args, **kwargs):
        await original(*args, **kwargs)
        raise RuntimeError("Simulated lost response after commit")

    monkeypatch.setattr(service, "create_guest_order", lose_response)
    with pytest.raises(RuntimeError, match="lost response"):
        await service.create_checkout(payload)
    recovered = await service.recover_checkout(payload.checkout_key)
    # Successful replay must not revalidate an expired quote or invoke the builder.
    monkeypatch.setattr(
        "app.services.checkout_safety.verify_quote", lambda *args: pytest.fail("Revalidated replay")
    )
    assert (await service.create_checkout(payload)).order_id == recovered.order_id
    assert await db.scalar(select(func.count(Order.id))) == 1
    assert await db.scalar(select(ProductInventory.reserved)) == 2


async def test_failure_after_reservation_rolls_back_and_key_can_retry(db, market, monkeypatch):
    service = OrderService(db)
    payload = await accepted_guest(service, guest_payload(market))
    original = service.inv_repo.reserve

    async def fail_after_reservation(*args, **kwargs):
        assert await original(*args, **kwargs)
        raise RuntimeError("Simulated reservation failure")

    monkeypatch.setattr(service.inv_repo, "reserve", fail_after_reservation)
    with pytest.raises(RuntimeError, match="reservation failure"):
        await service.create_checkout(payload)
    assert await db.scalar(select(func.count(Order.id))) == 0
    assert await db.scalar(select(ProductInventory.reserved)) == 0
    monkeypatch.setattr(service.inv_repo, "reserve", original)
    await service.create_checkout(payload)
    assert await db.scalar(select(func.count(Order.id))) == 1
    assert await db.scalar(select(ProductInventory.reserved)) == 2


async def test_coupon_change_requires_acceptance_and_replay_consumes_once(
    db, market, isolated_redis
):
    from app.models.coupon import Coupon, CouponUsage, DiscountType

    buyer_id = market.buyer.id
    await isolated_redis.hset(f"cart:{buyer_id}", str(market.variant.id), 2)
    coupon = Coupon(
        code="ACCEPT",
        discount_type=DiscountType.fixed,
        discount_value=Decimal("100"),
        max_uses_per_customer=1,
    )
    db.add(coupon)
    await db.commit()
    service = OrderService(db, isolated_redis)
    request = AccountCheckoutQuoteRequest(coupon_code="ACCEPT")
    quote = await service.quote_account_checkout(request, buyer_id)
    payload = CheckoutOrderRequest(
        shipping_address=ADDRESS,
        payment_method="cod",
        coupon_code="ACCEPT",
        checkout_key=uuid4(),
        quote_token=quote.quote_token,
    )
    # Simulate another transaction changing the coupon while this identity map is stale.
    await db.execute(
        update(Coupon)
        .where(Coupon.id == coupon.id)
        .values(discount_value=Decimal("200"))
        .execution_options(synchronize_session=False)
    )
    await db.commit()
    with pytest.raises(ConflictError) as error:
        await service.create_checkout(payload, buyer_id)
    assert error.value.code == "CHECKOUT_QUOTE_CHANGED"
    assert await db.scalar(select(func.count(CouponUsage.id))) == 0
    quote = await service.quote_account_checkout(request, buyer_id)
    payload = payload.model_copy(update={"quote_token": quote.quote_token})
    first = await service.create_checkout(payload, buyer_id)
    assert (await service.create_checkout(payload, buyer_id)).order_id == first.order_id
    assert first.total == Decimal("2400")
    assert await db.scalar(select(func.count(CouponUsage.id))) == 1
    assert await db.scalar(select(Coupon.uses_count)) == 1
