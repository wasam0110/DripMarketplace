"""Native PostgreSQL release checks using independent committed transactions."""

import asyncio
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker
from test_marketplace_regressions import guest_payload
from test_marketplace_regressions import market as marketplace_fixture

from app.core.exceptions import BusinessRuleError
from app.models.order import Order, OrderStatus, PaymentMethod, SellerOrder, SellerOrderStatus
from app.models.payment import Payment, PaymentStatus, Refund
from app.models.seller import SellerBankAccount, SellerWallet
from app.models.wallet import CommissionLedger, Payout, WalletTransaction, WalletTxType
from app.repositories.inventory_repo import InventoryRepository
from app.repositories.notification_repo import NotificationRepository
from app.schemas.payment import RefundRequest
from app.schemas.wallet import WithdrawalRequest
from app.services.commission_service import CommissionService
from app.services.order_service import OrderService
from app.services.payment_service import PaymentService
from app.services.wallet_service import WalletService

pytestmark = pytest.mark.integration
market = marketplace_fixture


@pytest.fixture
async def db(test_engine):
    # Unlike the normal SAVEPOINT fixture, other connections must see commits.
    async with async_sessionmaker(test_engine, expire_on_commit=False)() as session:
        yield session


async def race(engine, action, count=2):
    ready = asyncio.Event()

    async def run():
        async with async_sessionmaker(engine, expire_on_commit=False)() as session:
            await ready.wait()
            return await action(session)

    tasks = [asyncio.create_task(run()) for _ in range(count)]
    ready.set()
    return await asyncio.wait_for(asyncio.gather(*tasks, return_exceptions=True), timeout=30)


async def test_competing_stock_reservations_do_not_oversell(db, market, test_engine):
    async def reserve(session):
        result = await InventoryRepository(session).reserve(market.variant.id, 6)
        await session.commit()
        return result

    results = await race(test_engine, reserve)
    assert sorted(results) == [False, True]
    await db.refresh(market.inventory)
    assert (market.inventory.stock, market.inventory.reserved) == (8, 6)


async def test_competing_withdrawals_cannot_spend_same_balance(db, market, test_engine):
    wallet = await db.scalar(select(SellerWallet).where(SellerWallet.seller_id == market.seller.id))
    wallet.available_balance = Decimal("1000")
    bank = SellerBankAccount(
        seller_id=market.seller.id,
        bank_name="Test Bank",
        account_title="Test Seller",
        account_number="TEST-ACCOUNT",
    )
    db.add(bank)
    await db.commit()
    payload = WithdrawalRequest(amount=750, bank_account_id=bank.id)
    results = await race(
        test_engine,
        lambda session: WalletService(session).request_withdrawal(market.seller.id, payload),
    )
    assert sum(isinstance(value, BusinessRuleError) for value in results) == 1, results
    assert sum(not isinstance(value, Exception) for value in results) == 1, results
    await db.refresh(wallet)
    assert wallet.available_balance == Decimal("250")
    assert await db.scalar(select(func.count(Payout.id))) == 1


async def paid_order(db, market):
    created = await OrderService(db).create_guest_order(guest_payload(market))
    initiated = await PaymentService(db).initiate(created.order_id, guest_token=created.guest_token)
    payment = await db.get(Payment, initiated.payment_id)
    payment.status = PaymentStatus.completed
    so = await db.scalar(select(SellerOrder).where(SellerOrder.order_id == created.order_id))
    so.status = SellerOrderStatus.delivered
    await db.commit()
    return created, payment, so


async def test_concurrent_settlement_and_release_are_once_only(
    db, market, test_engine, monkeypatch
):
    from app.core import database
    from app.tasks.wallet_tasks import move_pending_to_available

    _, _, so = await paid_order(db, market)
    results = await race(test_engine, lambda session: CommissionService(session).settle(so.id))
    assert results == [None, None]
    assert await db.scalar(select(func.count(CommissionLedger.id))) == 1
    ledger = await db.scalar(select(CommissionLedger))
    ledger.settled_at = datetime.now(UTC) - timedelta(days=10)
    await db.commit()
    monkeypatch.setattr(
        database, "_session_factory", async_sessionmaker(test_engine, expire_on_commit=False)
    )
    await asyncio.wait_for(
        asyncio.gather(move_pending_to_available({}), move_pending_to_available({})), 30
    )
    wallet = await db.scalar(select(SellerWallet).where(SellerWallet.seller_id == market.seller.id))
    assert (wallet.pending_balance, wallet.available_balance) == (Decimal("0"), Decimal("2040"))
    assert (
        await db.scalar(
            select(func.count(WalletTransaction.id)).where(
                WalletTransaction.type == WalletTxType.credit_adjustment
            )
        )
        == 1
    )


async def test_concurrent_refund_confirmation_reverses_once(db, market, test_engine):
    _, payment, so = await paid_order(db, market)
    await CommissionService(db).settle(so.id)
    refund = await PaymentService(db).refund(
        payment.id,
        market.admin.id,
        RefundRequest(amount=600, reason="Partial refund", idempotency_key="race-refund"),
    )
    results = await race(
        test_engine,
        lambda session: PaymentService(session).confirm_refund(
            refund.refund_id, market.admin.id, "TEST-REFUND-RECEIPT"
        ),
    )
    assert all(not isinstance(value, Exception) for value in results), results
    wallet = await db.scalar(
        select(SellerWallet)
        .where(SellerWallet.seller_id == market.seller.id)
        .execution_options(populate_existing=True)
    )
    assert wallet.pending_balance == Decimal("1530")
    assert (
        await db.scalar(select(func.count(Refund.id)).where(Refund.processed_at.isnot(None))) == 1
    )


async def test_concurrent_payment_callbacks_preserve_one_transition(
    db, market, test_engine, monkeypatch
):
    import app.services.payment_service as module
    from app.integrations.payfast import PayFastClient

    created = await OrderService(db).create_guest_order(guest_payload(market))
    order = await db.get(Order, created.order_id)
    order.payment_method, order.status = PaymentMethod.payfast, OrderStatus.pending_payment
    await db.commit()
    gateway = PayFastClient("test-merchant", "test-secret")
    monkeypatch.setattr(module, "_build_payfast", lambda: gateway)
    initiated = await PaymentService(db).initiate(order.id, guest_token=created.guest_token)
    data = {
        "order_id": str(order.id),
        "amount": "2600.00",
        "currency": "PKR",
        "payment_status": "PAID",
        "transaction_id": "race-txn",
    }
    data["signature"] = gateway._sign(data)
    assert await race(
        test_engine, lambda session: PaymentService(session).handle_payfast_callback(data)
    ) == [None, None]
    await db.refresh(order)
    assert order.status == OrderStatus.payment_confirmed
    assert (await db.get(Payment, initiated.payment_id)).status == PaymentStatus.completed


async def test_expiry_workers_release_reservation_once(db, market, test_engine, monkeypatch):
    from app.core import database
    from app.tasks.order_tasks import expire_pending_orders

    created = await OrderService(db).create_guest_order(guest_payload(market))
    order = await db.get(Order, created.order_id)
    order.created_at = datetime.now(UTC) - timedelta(days=1)
    await db.commit()
    monkeypatch.setattr(
        database, "_session_factory", async_sessionmaker(test_engine, expire_on_commit=False)
    )
    await asyncio.wait_for(asyncio.gather(expire_pending_orders({}), expire_pending_orders({})), 30)
    await db.refresh(order)
    await db.refresh(market.inventory)
    assert order.status == OrderStatus.cancelled
    assert (market.inventory.stock, market.inventory.reserved) == (8, 0)


async def test_notification_read_archive_and_ownership(db, market, test_engine, monkeypatch):
    from app.core import database
    from app.tasks.cleanup_tasks import archive_old_notifications

    old = datetime.now(UTC) - timedelta(days=100)
    repo = NotificationRepository(db)
    read = await repo.create(
        user_id=market.buyer.id, type="test", title="Read", body="Body", created_at=old
    )
    unread = await repo.create(
        user_id=market.buyer.id, type="test", title="Unread", body="Body", created_at=old
    )
    assert not await repo.mark_read(read.id, market.admin.id)
    assert await repo.mark_read(read.id, market.buyer.id)
    await db.commit()
    await db.refresh(read)
    stamp = read.read_at
    assert stamp is not None
    await repo.mark_read(read.id, market.buyer.id)
    await db.commit()
    await db.refresh(read)
    assert read.read_at == stamp
    monkeypatch.setattr(
        database, "_session_factory", async_sessionmaker(test_engine, expire_on_commit=False)
    )
    await archive_old_notifications({})
    rows, total = await repo.list_by_user(market.buyer.id)
    assert total == 1 and rows[0].id == unread.id
    assert await repo.unread_count(market.buyer.id) == 1
    assert await repo.mark_all_read(market.buyer.id) == 1
    await db.commit()
    await db.refresh(unread)
    assert unread.read_at is not None


async def test_fresh_migrations_round_trip_and_all_model_columns(test_engine):
    from alembic import command
    from alembic.config import Config

    from app.models.base import Base

    config = Config("alembic.ini")
    # test_engine has a unique disposable schema; never touch public tables.
    async with test_engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)

        def migrations(sync_connection):
            config.attributes["connection"] = sync_connection
            command.upgrade(config, "head")
            command.downgrade(config, "012_marketplace_gaps")
            command.upgrade(config, "head")

        await connection.run_sync(migrations)
        for table in Base.metadata.sorted_tables:
            await connection.execute(select(table).limit(0))


async def test_native_worker_startup_health_and_shutdown(monkeypatch):
    import os

    from sqlalchemy import text

    from app.api.v1.health import health_check
    from app.core import database, redis
    from app.core.config import settings
    from app.tasks import worker

    if not os.environ.get("TEST_DATABASE_URL") or not os.environ.get("TEST_REDIS_URL"):
        pytest.skip("Both dedicated test service URLs are required")
    monkeypatch.setattr(settings, "REDIS_URL", os.environ["TEST_REDIS_URL"])
    monkeypatch.setattr(worker, "configure_logging", lambda: None)
    await worker.startup({})
    try:
        assert (await health_check()).status == "ok"
        async with database.AsyncSessionLocal() as session, database.atomic(session):
            assert await session.scalar(text("SELECT 1")) == 1
    finally:
        await worker.shutdown({})
    assert database._session_factory is None and redis._redis is None
