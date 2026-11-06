"""Real PostgreSQL refund confirmation, accounting/stock atomicity and session races."""

import asyncio
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import async_sessionmaker
from test_admin_cod_flow import seed
from test_admin_collection_flow import collected_order as collected_order
from test_admin_collection_flow import deliver
from test_marketplace_regressions import market as marketplace_fixture
from test_resource_ownership import headers

from app.core.exceptions import BusinessRuleError, ConflictError
from app.models.order import OrderItem, SellerOrder
from app.models.payment import Payment, PaymentStatus, Refund
from app.models.product import ProductInventory
from app.models.return_ import Return, ReturnItem, ReturnStatus
from app.models.seller import SellerWallet
from app.models.wallet import (
    CommissionLedger,
    RefundAccounting,
    RefundAllocation,
    WalletTransaction,
)
from app.repositories.order_repo import OrderRepository
from app.schemas.payment import RefundRequest
from app.services.commission_service import CommissionService
from app.services.payment_service import PaymentService

pytestmark = pytest.mark.integration
market = marketplace_fixture
BASE = "/api/v1/payments"


@pytest.fixture
async def paid(db, market, collected_order):
    await PaymentService(db).record_cod_collection(
        collected_order.id, market.admin.id, "COD-PAID-001"
    )
    return collected_order


async def state(db):
    result = {}
    for model in (
        Payment,
        Refund,
        ProductInventory,
        Return,
        ReturnItem,
        SellerWallet,
        CommissionLedger,
        RefundAccounting,
        RefundAllocation,
        WalletTransaction,
    ):
        result[model.__tablename__] = sorted(
            tuple(map(str, row))
            for row in (await db.execute(select(*model.__table__.columns))).all()
        )
    return result


async def pending(db, paid, market, amount="500.00", return_id=None, key="refund-request-001"):
    return await PaymentService(db).refund(
        paid.id,
        market.admin.id,
        RefundRequest(amount=amount, reason="Reviewed customer refund", idempotency_key=key),
        return_id=return_id,
    )


async def read(client, market, refund_id):
    result = await client.get(f"{BASE}/refunds/{refund_id}", headers=headers(market.admin))
    assert result.status_code == 200, result.text
    return result.json()


@pytest.mark.parametrize("role", ["guest", "buyer", "seller_user", "unverified"])
async def test_private_refund_permissions(client, db, market, paid, role):
    refund = await pending(db, paid, market)
    if role == "unverified":
        market.admin.has_verified_email = False
        await db.commit()
    auth = (
        {}
        if role == "guest"
        else headers(market.admin if role == "unverified" else getattr(market, role))
    )
    before = await state(db)
    for method, path, payload in (
        ("get", f"{BASE}/refunds", None),
        ("get", f"{BASE}/refunds/{refund.refund_id}", None),
        ("get", f"{BASE}/{paid.id}/refunds", None),
        ("post", f"{BASE}/{paid.id}/refund", {"amount": "1", "reason": "Another refund"}),
        ("post", f"{BASE}/refunds/{refund.refund_id}/confirm", {"reference": "BANK-001"}),
    ):
        response = await getattr(client, method)(
            path, headers=auth, **({"json": payload} if payload else {})
        )
        assert response.status_code in (401, 403)
        assert await state(db) == before


async def test_direct_partial_then_full_refund_preserves_stock(client, db, market, paid):
    before = await state(db)
    first = await pending(db, paid, market)
    assert (await PaymentService(db).get_admin_refund(first.refund_id)).refund_id == first.refund_id
    detail = await read(client, market, first.refund_id)
    assert detail["currency"] == "PKR" and detail["can_confirm_refund"]
    listed = await client.get(f"{BASE}/refunds?status=pending", headers=headers(market.admin))
    assert listed.json()["per_page"] == 25 and listed.json()["total_pages"] == 1
    for table in before:
        if table != "refunds":
            assert (await state(db))[table] == before[table]
    payload = {
        "reference": "  BANK-001  ",
        "expected_amount": detail["amount"],
        "expected_payment_id": str(paid.id),
        "expected_return_id": None,
    }
    response = await client.post(
        f"{BASE}/refunds/{first.refund_id}/confirm", headers=headers(market.admin), json=payload
    )
    assert response.status_code == 200, response.text
    saved = await read(client, market, first.refund_id)
    assert saved["status"] == "completed" and saved["confirmed_by"] == str(market.admin.id)
    assert saved["transfer_reference"] == "BANK-001" and saved["accounting"]["reconciled"]
    assert Decimal(saved["accounting"]["recovered_amount"]) == Decimal("425")
    after = await state(db)
    repeat = await client.post(
        f"{BASE}/refunds/{first.refund_id}/confirm", headers=headers(market.admin), json=payload
    )
    assert repeat.json() == response.json() and await state(db) == after
    second = await pending(db, paid, market, "2100", key="refund-request-002")
    await PaymentService(db).confirm_refund(second.refund_id, market.admin.id, "BANK-002")
    payment = await db.get(Payment, paid.id)
    assert payment.status == PaymentStatus.refunded
    wallet = (await db.scalars(select(SellerWallet))).one()
    assert wallet.pending_balance == 0 and wallet.available_balance == 0
    assert (await state(db))["product_inventory"] == before["product_inventory"]
    history = await client.get(f"{BASE}/{paid.id}/refunds", headers=headers(market.admin))
    assert history.json()["completed_refund_amount"] == "2600.00"
    assert history.json()["remaining_refundable_amount"] == "0.00"
    assert not history.json()["can_request_refund"]


async def test_request_idempotency_and_stale_remaining(client, db, market, paid):
    payload = {
        "amount": "500.25",
        "reason": "Reviewed customer refund",
        "idempotency_key": "request-stable-001",
        "expected_remaining_amount": "2600",
    }
    path = f"{BASE}/{paid.id}/refund"
    first = await client.post(path, headers=headers(market.admin), json=payload)
    assert first.status_code == 200, first.text
    after = await state(db)
    repeated = await client.post(path, headers=headers(market.admin), json=payload)
    assert repeated.json() == first.json() and await state(db) == after
    stale = await client.post(
        path,
        headers=headers(market.admin),
        json={**payload, "idempotency_key": "request-stable-002"},
    )
    assert stale.status_code == 409 and await state(db) == after


@pytest.fixture
async def linked(db, market, paid):
    split = await db.scalar(select(SellerOrder).where(SellerOrder.order_id == paid.order_id))
    item = await db.scalar(select(OrderItem).where(OrderItem.order_id == paid.order_id))
    returned = Return(
        order_id=paid.order_id,
        seller_order_id=split.id,
        status=ReturnStatus.received,
        reason="Returned product",
    )
    db.add(returned)
    await db.flush()
    line = ReturnItem(return_id=returned.id, order_item_id=item.id, quantity=1)
    db.add(line)
    await db.commit()
    refund = await pending(db, paid, market, "1200", returned.id)
    return SimpleNamespace(
        refund_id=refund.refund_id,
        return_id=returned.id,
        item_id=item.id,
        line_id=line.id,
        split_id=split.id,
    )


async def test_return_confirmation_restock_is_exactly_once(db, market, paid, linked):
    before = await state(db)
    await PaymentService(db).confirm_refund(linked.refund_id, market.admin.id, "RETURN-001")
    returned = await db.get(Return, linked.return_id)
    assert returned.status == ReturnStatus.refunded
    inventory = (await db.scalars(select(ProductInventory))).one()
    assert inventory.stock == 7 and inventory.reserved == 0
    after = await state(db)
    assert after["product_inventory"] != before["product_inventory"]
    await PaymentService(db).confirm_refund(linked.refund_id, market.admin.id, "RETURN-001")
    assert await state(db) == after
    with pytest.raises(BusinessRuleError, match="different reference"):
        await PaymentService(db).confirm_refund(linked.refund_id, market.admin.id, "OTHER-REF")


@pytest.mark.parametrize(
    "kind", ["amount", "payment", "link", "status", "quantity", "zero", "inventory", "prior"]
)
async def test_invalid_review_or_return_has_no_side_effects(client, db, market, paid, linked, kind):
    payload = {
        "reference": "BANK-BLOCKED",
        "expected_amount": "1200",
        "expected_payment_id": str(paid.id),
        "expected_return_id": str(linked.return_id),
    }
    if kind == "amount":
        payload["expected_amount"] = "1200.01"
    elif kind == "payment":
        payload["expected_payment_id"] = str(uuid4())
    elif kind == "link":
        payload["expected_return_id"] = None
    elif kind == "status":
        (await db.get(Return, linked.return_id)).status = ReturnStatus.approved
    elif kind in ("quantity", "zero"):
        (await db.get(ReturnItem, linked.line_id)).quantity = 3 if kind == "quantity" else 0
    elif kind == "inventory":
        await db.execute(delete(ProductInventory))
    elif kind == "prior":
        old = Return(
            order_id=paid.order_id,
            seller_order_id=linked.split_id,
            status=ReturnStatus.refunded,
            reason="Legacy previously credited return",
        )
        db.add(old)
        await db.flush()
        db.add(ReturnItem(return_id=old.id, order_item_id=linked.item_id, quantity=2))
    await db.commit()
    before = await state(db)
    response = await client.post(
        f"{BASE}/refunds/{linked.refund_id}/confirm", headers=headers(market.admin), json=payload
    )
    assert response.status_code == (409 if kind in ("amount", "payment", "link") else 422), (
        response.text
    )
    assert await state(db) == before


async def test_accounting_failure_rolls_back_return_stock_and_transfer(
    db, market, paid, linked, monkeypatch
):
    before = await state(db)
    original = CommissionService.reverse_for_refund

    async def fail(self, *args, **kwargs):
        await original(self, *args, **kwargs)
        raise RuntimeError("Synthetic accounting failure")

    monkeypatch.setattr(CommissionService, "reverse_for_refund", fail)
    with pytest.raises(RuntimeError, match="Synthetic"):
        await PaymentService(db).confirm_refund(linked.refund_id, market.admin.id, "ROLLBACK-001")
    await db.rollback()
    assert await state(db) == before


@pytest.mark.parametrize("same_reference", [True, False])
async def test_independent_confirmation_sessions_are_once(test_engine, same_reference):
    sessions = async_sessionmaker(test_engine, expire_on_commit=False)
    world = await seed(sessions)
    async with sessions() as db:
        order = await OrderRepository(db).get_by_id(world.id)
        payment = Payment(order_id=order.id, method="cod", amount=order.total, currency="PKR")
        db.add(payment)
        await db.commit()
        await deliver(db, order.id, world.admin)
        await PaymentService(db).record_cod_collection(payment.id, world.admin, "COLLECT-001")
        refund = await PaymentService(db).refund(
            payment.id,
            world.admin,
            RefundRequest(
                amount="1500", reason="Concurrent manual refund", idempotency_key="race-refund-001"
            ),
        )
        refund_id = refund.refund_id
    ready, count = asyncio.Event(), 0

    async def confirm(index):
        nonlocal count
        async with sessions() as db:
            cached = await db.get(Refund, refund_id)
            assert cached.processed_at is None
            count += 1
            if count == 2:
                ready.set()
            await ready.wait()
            try:
                return await PaymentService(db).confirm_refund(
                    refund_id, world.admin, "SAME-REF" if same_reference else f"REF-{index}"
                )
            except (BusinessRuleError, ConflictError):
                await db.rollback()
                return None

    results = await asyncio.wait_for(asyncio.gather(confirm(0), confirm(1)), 20)
    assert len([row for row in results if row]) == (2 if same_reference else 1)
    async with sessions() as db:
        assert len((await db.scalars(select(RefundAccounting))).all()) == 1
        wallet = (await db.scalars(select(SellerWallet))).one()
        assert wallet.pending_balance == Decimal("1275")
