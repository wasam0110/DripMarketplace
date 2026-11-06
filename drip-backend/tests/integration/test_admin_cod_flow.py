"""Native COD transitions, inventory/outbox atomicity and independent-session races."""

import asyncio
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import async_sessionmaker
from test_marketplace_regressions import guest_payload
from test_marketplace_regressions import market as marketplace_fixture
from test_resource_ownership import headers

from app.core.exceptions import BusinessRuleError, ConflictError
from app.models.admin import SystemSetting
from app.models.notification import NotificationOutbox
from app.models.order import Order, OrderStatus, OrderStatusHistory, SellerOrder, SellerOrderStatus
from app.models.product import Product, ProductInventory, ProductVariant, SizeType
from app.models.seller import Seller, SellerStatus, SellerWallet
from app.models.user import User, UserRole
from app.models.wallet import CommissionLedger
from app.repositories.order_repo import OrderRepository
from app.services.admin_service import AdminService
from app.services.order_service import OrderService
from app.tasks.order_tasks import cod_verification_timeout, expire_pending_orders

pytestmark = pytest.mark.integration
market = marketplace_fixture
BASE = "/api/v1/admin/cod-queue"


@pytest.fixture
async def cod(db, market):
    created = await OrderService(db).create_guest_order(guest_payload(market))
    return SimpleNamespace(id=created.order_id, market=market)


async def state(db):
    result = {}
    for model in (
        Order,
        SellerOrder,
        OrderStatusHistory,
        ProductInventory,
        CommissionLedger,
        SellerWallet,
        NotificationOutbox,
    ):
        result[model.__tablename__] = sorted(
            tuple(map(str, row))
            for row in (await db.execute(select(*model.__table__.columns))).all()
        )
    return result


async def review(client, admin):
    response = await client.get(BASE, headers=headers(admin))
    assert response.status_code == 200, response.text
    return response.json()[0]


@pytest.mark.parametrize("action", ["list", "verify", "cancel"])
@pytest.mark.parametrize("role", ["guest", "buyer", "seller_user", "unverified"])
async def test_permissions(client, db, market, cod, role, action):
    if role == "unverified":
        market.admin.has_verified_email = False
        await db.commit()
    auth = (
        {}
        if role == "guest"
        else headers(market.admin if role == "unverified" else getattr(market, role))
    )
    before = await state(db)
    result = (
        await client.get(BASE, headers=auth)
        if action == "list"
        else await client.post(
            f"{BASE}/{cod.id}/{action}", headers=auth, json={"note": "Reviewed synthetic order"}
        )
    )
    assert result.status_code in (401, 403)
    assert await state(db) == before


@pytest.mark.parametrize("action", ["verify", "cancel"])
async def test_decision_is_once_and_keeps_money_and_physical_stock(client, db, market, cod, action):
    row = await review(client, market.admin)
    before = await state(db)
    payload = {
        "note": "Customer contacted and checked",
        "expected_updated_at": row["updated_at"],
        "expected_expires_at": row["expires_at"],
    }
    result = await client.post(
        f"{BASE}/{cod.id}/{action}", headers=headers(market.admin), json=payload
    )
    assert result.status_code == 200, result.text
    expected = "processing" if action == "verify" else "cancelled"
    assert result.json()["order_id"] == str(cod.id) and result.json()["status"] == expected
    detail = await client.get(f"/api/v1/admin/orders/{cod.id}", headers=headers(market.admin))
    assert detail.json()["status"] == expected and detail.json()["payment_method"] == "cod"
    await db.refresh(market.inventory)
    assert market.inventory.stock == 8 and market.inventory.reserved == (
        2 if action == "verify" else 0
    )
    assert (await client.get(BASE, headers=headers(market.admin))).json() == []
    after = await state(db)
    for table in ("commission_ledger", "seller_wallets"):
        assert after[table] == before[table]
    second = await client.post(
        f"{BASE}/{cod.id}/{action}", headers=headers(market.admin), json=payload
    )
    assert second.status_code == 422
    assert await state(db) == after
    outbox = (
        await db.scalars(
            select(NotificationOutbox).where(
                NotificationOutbox.event_key == f"order:{cod.id}:status:{expected}"
            )
        )
    ).all()
    assert len(outbox) == 1
    history = (
        await db.scalars(
            select(OrderStatusHistory).where(
                OrderStatusHistory.order_id == cod.id, OrderStatusHistory.new_status == expected
            )
        )
    ).all()
    assert len(history) == 1 and history[0].changed_by == market.admin.id


async def test_expired_is_visible_cancel_only(client, db, market, cod):
    order = await db.get(Order, cod.id)
    order.created_at = datetime.now(UTC) - timedelta(hours=2)
    await db.commit()
    row = await review(client, market.admin)
    assert row["minutes_remaining"] == 0
    before = await state(db)
    response = await client.post(f"{BASE}/{cod.id}/verify", headers=headers(market.admin), json={})
    assert response.status_code == 422
    assert await state(db) == before
    assert (
        await client.post(
            f"{BASE}/{cod.id}/cancel",
            headers=headers(market.admin),
            json={"note": "Expired after customer did not respond"},
        )
    ).status_code == 200


@pytest.mark.parametrize("changed", ["version", "policy", "method", "split"])
async def test_preflight_changes_are_rejected(client, db, market, cod, changed):
    row = await review(client, market.admin)
    order = await db.get(Order, cod.id)
    if changed == "version":
        order.updated_at = datetime.now(UTC) + timedelta(seconds=1)
    if changed == "policy":
        db.add(SystemSetting(key="cod_timeout_minutes", value="60"))
    if changed == "method":
        order.payment_method = "payfast"
    if changed == "split":
        split = await db.scalar(select(SellerOrder).where(SellerOrder.order_id == cod.id))
        split.status = SellerOrderStatus.shipped
    await db.commit()
    before = await state(db)
    response = await client.post(
        f"{BASE}/{cod.id}/verify",
        headers=headers(market.admin),
        json={"expected_updated_at": row["updated_at"], "expected_expires_at": row["expires_at"]},
    )
    assert response.status_code == (409 if changed in ("version", "policy") else 422), response.text
    assert await state(db) == before
    if changed == "method":
        assert (await client.get(BASE, headers=headers(market.admin))).json() == []


async def test_inconsistent_release_rolls_back(db, market, cod):
    market.inventory.reserved = 1
    await db.commit()
    before = await state(db)
    with pytest.raises(BusinessRuleError, match="inventory is inconsistent"):
        await AdminService(db).cancel_cod(cod.id, market.admin.id)
    await db.rollback()
    assert await state(db) == before


async def test_outbox_failure_rolls_back_all_changes(db, market, cod, monkeypatch):
    import app.services.admin_service as module

    before = await state(db)
    original = module.queue_notification

    async def fail(*args):
        await original(*args)
        raise RuntimeError("synthetic outbox failure")

    monkeypatch.setattr(module, "queue_notification", fail)
    with pytest.raises(RuntimeError):
        await AdminService(db).cancel_cod(cod.id, market.admin.id)
    await db.rollback()
    assert await state(db) == before


@pytest.mark.parametrize("worker", ["timeout", "sweep"])
async def test_expiry_worker_releases_once(db, market, cod, monkeypatch, worker):
    import app.core.database as database

    order = await db.get(Order, cod.id)
    order.created_at = datetime.now(UTC) - timedelta(hours=2)
    await db.commit()

    class Context:
        async def __aenter__(self):
            return db

        async def __aexit__(self, *args):
            return False

    monkeypatch.setattr(database, "AsyncSessionLocal", Context)
    run = (
        (lambda: cod_verification_timeout({}, str(cod.id)))
        if worker == "timeout"
        else (lambda: expire_pending_orders({}))
    )
    await run()
    after = await state(db)
    await run()
    assert await state(db) == after
    await db.refresh(market.inventory)
    assert market.inventory.stock == 8 and market.inventory.reserved == 0


async def seed(sessions, expired=False):
    async with sessions() as db:
        actor = User(
            email=f"actor-{uuid4()}@example.test",
            password_hash="synthetic-only",
            role=UserRole.admin,
            has_verified_email=True,
        )
        owner = User(
            email=f"owner-{uuid4()}@example.test",
            password_hash="synthetic-only",
            role=UserRole.seller,
            has_verified_email=True,
        )
        db.add_all([actor, owner])
        await db.flush()
        seller = Seller(
            user_id=owner.id,
            brand_name="Race Brand",
            slug=f"race-{uuid4().hex}",
            status=SellerStatus.active,
            total_slots=50,
        )
        db.add(seller)
        await db.flush()
        db.add(SellerWallet(seller_id=seller.id))
        product = Product(
            seller_id=seller.id,
            name="Race shirt",
            slug=f"race-{uuid4().hex}",
            price=Decimal("1500"),
            is_published=True,
        )
        db.add(product)
        await db.flush()
        variant = ProductVariant(
            product_id=product.id,
            sku=f"RACE-{uuid4().hex}",
            size_type=SizeType.alpha,
            size_value="M",
            colour="Ivory",
        )
        db.add(variant)
        await db.flush()
        inventory = ProductInventory(variant_id=variant.id, stock=8, reserved=0)
        db.add(inventory)
        await db.commit()
        fake_market = SimpleNamespace(variant=variant)
        created = await OrderService(db).create_guest_order(guest_payload(fake_market))
        order = await db.get(Order, created.order_id)
        if expired:
            order.created_at = datetime.now(UTC) - timedelta(hours=2)
        await db.commit()
        return SimpleNamespace(id=created.order_id, admin=actor.id, inventory=inventory.id)


@pytest.mark.parametrize(
    "actions", [("verify", "verify"), ("cancel", "cancel"), ("verify", "cancel")]
)
async def test_independent_preloaded_decisions_have_one_winner(test_engine, actions):
    sessions = async_sessionmaker(test_engine, expire_on_commit=False)
    world = await seed(sessions)
    ready, count = asyncio.Event(), 0

    async def act(action):
        nonlocal count
        async with sessions() as db:
            held = await OrderRepository(db).get_by_id(world.id)
            assert held.status == OrderStatus.pending_cod_verification
            count += 1
            if count == 2:
                ready.set()
            await ready.wait()
            try:
                return await getattr(AdminService(db), f"{action}_cod")(world.id, world.admin)
            except (BusinessRuleError, ConflictError):
                await db.rollback()
                return None

    results = await asyncio.wait_for(
        asyncio.gather(*(act(action) for action in actions)), timeout=20
    )
    winners = [value for value in results if value is not None]
    assert len(winners) == 1
    async with sessions() as db:
        inventory = await db.get(ProductInventory, world.inventory)
        assert inventory.stock == 8 and inventory.reserved == (
            0 if winners[0]["status"] == "cancelled" else 2
        )
        assert (
            len(
                (
                    await db.scalars(
                        select(NotificationOutbox).where(
                            NotificationOutbox.event_key.like(f"order:{world.id}:status:%")
                        )
                    )
                ).all()
            )
            == 1
        )


async def test_timeout_waits_then_discards_preloaded_pending_state(test_engine, monkeypatch):
    import app.core.database as database
    import app.services.admin_service as module

    sessions = async_sessionmaker(test_engine, expire_on_commit=False)
    world = await seed(sessions, expired=True)
    async with sessions() as db:
        inventory = await db.get(ProductInventory, world.inventory)
        inventory.reserved = 4  # Two units also held by an unrelated synthetic reservation.
        await db.commit()
    worker_db = sessions()
    held = await OrderRepository(worker_db).get_by_id(world.id)
    assert held.status == OrderStatus.pending_cod_verification
    pid = await worker_db.scalar(text("select pg_backend_pid()"))
    monkeypatch.setattr(database, "AsyncSessionLocal", lambda: worker_db)
    paused, finish = asyncio.Event(), asyncio.Event()
    original = module.queue_notification

    async def pause(*args):
        await original(*args)
        paused.set()
        await finish.wait()

    monkeypatch.setattr(module, "queue_notification", pause)

    async def cancel():
        async with sessions() as db:
            return await AdminService(db).cancel_cod(world.id, world.admin)

    admin_task = asyncio.create_task(cancel())
    await asyncio.wait_for(paused.wait(), timeout=10)
    timeout_task = asyncio.create_task(cod_verification_timeout({}, str(world.id)))
    try:
        async with sessions() as observer:

            async def blocked():
                while not await observer.scalar(
                    text("select cardinality(pg_blocking_pids(:pid)) > 0"), {"pid": pid}
                ):
                    await asyncio.sleep(0.02)

            await asyncio.wait_for(blocked(), timeout=10)
    finally:
        finish.set()
    await asyncio.wait_for(asyncio.gather(admin_task, timeout_task), timeout=20)
    async with sessions() as db:
        inventory = await db.get(ProductInventory, world.inventory)
        assert inventory.reserved == 2 and inventory.stock == 8
        assert (
            len(
                (
                    await db.scalars(
                        select(NotificationOutbox).where(
                            NotificationOutbox.event_key.like(f"order:{world.id}:status:%")
                        )
                    )
                ).all()
            )
            == 1
        )
        history = (
            await db.scalars(
                select(OrderStatusHistory).where(
                    OrderStatusHistory.order_id == world.id,
                    OrderStatusHistory.new_status == "cancelled",
                )
            )
        ).all()
        assert len(history) == 1
