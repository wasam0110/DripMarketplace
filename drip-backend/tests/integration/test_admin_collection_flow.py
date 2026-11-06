"""Local COD evidence and native settlement atomicity/concurrency; no provider writes."""

import asyncio
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker
from test_admin_cod_flow import seed as seed_cod
from test_marketplace_regressions import guest_payload
from test_marketplace_regressions import market as marketplace_fixture
from test_resource_ownership import headers

from app.core.exceptions import BusinessRuleError
from app.models.order import Order, SellerOrder
from app.models.payment import Payment, PaymentCallback, PaymentStatus
from app.models.product import Product, ProductInventory, ProductVariant, SizeType
from app.models.seller import Seller, SellerStatus, SellerWallet
from app.models.user import User, UserRole
from app.models.wallet import CommissionLedger, WalletTransaction
from app.repositories.order_repo import OrderRepository
from app.schemas.order import UpdateSellerOrderRequest
from app.services.admin_service import AdminService
from app.services.commission_service import CommissionService
from app.services.order_service import OrderService
from app.services.payment_service import PaymentService

pytestmark = pytest.mark.integration
market = marketplace_fixture
BASE = "/api/v1/payments"


async def deliver(db, order_id, admin_id):
    await AdminService(db).verify_cod(order_id, admin_id)
    order = await OrderRepository(db).get_by_id(order_id)
    for split in order.seller_orders:
        for values in (
            {"status": "processing"},
            {"status": "shipped", "tracking_number": "TEST-TRACK", "courier_name": "Test courier"},
            {"status": "delivered"},
        ):
            await OrderService(db).update_seller_order_status(
                split.seller_id, split.id, UpdateSellerOrderRequest(**values)
            )


@pytest.fixture
async def collected_order(db, market):
    created = await OrderService(db).create_guest_order(guest_payload(market))
    initiated = await PaymentService(db).initiate(created.order_id, guest_token=created.guest_token)
    await deliver(db, created.order_id, market.admin.id)
    return SimpleNamespace(id=initiated.payment_id, order_id=created.order_id)


async def snapshot(db):
    result = {}
    for model in (
        Payment,
        PaymentCallback,
        Order,
        SellerOrder,
        ProductInventory,
        SellerWallet,
        CommissionLedger,
        WalletTransaction,
    ):
        result[model.__tablename__] = sorted(
            tuple(map(str, row))
            for row in (await db.execute(select(*model.__table__.columns))).all()
        )
    return result


async def read(client, market, payment_id):
    result = await client.get(f"{BASE}/{payment_id}", headers=headers(market.admin))
    assert result.status_code == 200, result.text
    return result.json()


@pytest.mark.parametrize("action", ["list", "detail", "collect"])
@pytest.mark.parametrize("role", ["guest", "buyer", "seller_user", "unverified"])
async def test_collection_permissions(client, db, market, collected_order, role, action):
    if role == "unverified":
        market.admin.has_verified_email = False
        await db.commit()
    auth = (
        {}
        if role == "guest"
        else headers(market.admin if role == "unverified" else getattr(market, role))
    )
    before = await snapshot(db)
    path = BASE if action == "list" else f"{BASE}/{collected_order.id}"
    response = (
        await client.post(path + "/cod-collection", headers=auth, json={"reference": "COD-001"})
        if action == "collect"
        else await client.get(path, headers=auth)
    )
    assert response.status_code in (401, 403)
    assert await snapshot(db) == before


async def test_private_reads_and_exact_collection_once(client, db, market, collected_order):
    before = await snapshot(db)
    detail = await read(client, market, collected_order.id)
    assert detail["can_record_cod_collection"] is True
    assert not detail["collection_blockers"] and detail["collection_recorded_by"] is None
    assert not ({"gateway_payload", "callbacks", "guest_token", "guest_email"} & detail.keys())
    listed = await client.get(
        BASE + "?method=cod&status=pending&page=1", headers=headers(market.admin)
    )
    assert listed.status_code == 200
    assert listed.json()["per_page"] == 25 and listed.json()["total_pages"] == 1
    assert await snapshot(db) == before
    payload = {
        "reference": "  COURIER-001  ",
        "expected_amount": detail["amount"],
        "expected_order_updated_at": detail["order_updated_at"],
    }
    response = await client.post(
        f"{BASE}/{collected_order.id}/cod-collection", headers=headers(market.admin), json=payload
    )
    assert response.status_code == 200, response.text
    receipt = response.json()
    assert receipt["recorded_by"] == str(market.admin.id)
    assert receipt["reference"] == "COURIER-001" and receipt["paid_at"]
    assert Decimal(receipt["amount"]) == Decimal("2600")
    assert receipt["order_id"] == str(collected_order.order_id)
    saved = await read(client, market, collected_order.id)
    assert saved["status"] == "completed" and not saved["can_record_cod_collection"]
    assert saved["paid_at"] == receipt["paid_at"]
    after = await snapshot(db)
    assert after["product_inventory"] == before["product_inventory"]
    ledger = (await db.scalars(select(CommissionLedger))).one()
    assert ledger.gross_amount == Decimal("2400")
    wallet = (await db.scalars(select(SellerWallet))).one()
    assert wallet.pending_balance == Decimal("2040") and wallet.available_balance == 0
    callbacks = (await db.scalars(select(PaymentCallback))).all()
    assert len(callbacks) == 1 and callbacks[0].gateway == "cod_collection"
    repeat = await client.post(
        f"{BASE}/{collected_order.id}/cod-collection", headers=headers(market.admin), json=payload
    )
    assert repeat.status_code == 200 and repeat.json() == receipt
    assert await snapshot(db) == after
    conflict = await client.post(
        f"{BASE}/{collected_order.id}/cod-collection",
        headers=headers(market.admin),
        json={"reference": "DIFFERENT-REF"},
    )
    assert conflict.status_code == 422 and await snapshot(db) == after


@pytest.mark.parametrize("kind", ["amount", "version", "currency", "checkout", "split", "method"])
async def test_stale_or_inconsistent_no_collection(client, db, market, collected_order, kind):
    detail = await read(client, market, collected_order.id)
    payment = await db.get(Payment, collected_order.id)
    order = await OrderRepository(db).get_by_id(payment.order_id)
    payload = {
        "reference": "TEST-001",
        "expected_amount": detail["amount"],
        "expected_order_updated_at": detail["order_updated_at"],
    }
    if kind == "amount":
        payload["expected_amount"] = "1.00"
    elif kind == "version":
        payload["expected_order_updated_at"] = "2000-01-01T00:00:00Z"
    elif kind == "currency":
        payment.currency = "USD"
    elif kind == "checkout":
        payment.amount -= Decimal("0.01")
        payload["expected_amount"] = str(payment.amount)
    elif kind == "split":
        order.seller_orders[0].status = "returned"
    elif kind == "method":
        payment.method = "payfast"
    await db.commit()
    before = await snapshot(db)
    response = await client.post(
        f"{BASE}/{payment.id}/cod-collection", headers=headers(market.admin), json=payload
    )
    assert response.status_code == (409 if kind in ("amount", "version") else 422), response.text
    assert await snapshot(db) == before


async def test_audit_and_wallet_roll_back_if_settlement_fails(
    db, market, collected_order, monkeypatch
):
    before = await snapshot(db)
    original = CommissionService.settle

    async def fail_after_settlement(self, *args, **kwargs):
        await original(self, *args, **kwargs)
        raise RuntimeError("Synthetic failure after wallet credit")

    monkeypatch.setattr(CommissionService, "settle", fail_after_settlement)
    with pytest.raises(RuntimeError, match="Synthetic failure"):
        await PaymentService(db).record_cod_collection(
            collected_order.id, market.admin.id, "COD-ROLLBACK"
        )
    await db.rollback()
    assert await snapshot(db) == before


@pytest.mark.parametrize("references", [("SAME-001", "SAME-001"), ("FIRST-001", "SECOND-001")])
async def test_independent_admin_collections_settle_once(test_engine, references):
    sessions = async_sessionmaker(test_engine, expire_on_commit=False)
    world = await seed_cod(sessions)
    async with sessions() as db:
        order = await OrderRepository(db).get_by_id(world.id)
        payment = Payment(order_id=order.id, method="cod", amount=order.total, currency="PKR")
        db.add(payment)
        await db.commit()
        await deliver(db, order.id, world.admin)
        payment_id = payment.id
    ready, count = asyncio.Event(), 0

    async def collect(reference):
        nonlocal count
        async with sessions() as db:
            cached = await db.get(Payment, payment_id)
            assert cached.status == PaymentStatus.pending
            count += 1
            if count == 2:
                ready.set()
            await ready.wait()
            try:
                return await PaymentService(db).record_cod_collection(
                    payment_id, world.admin, reference
                )
            except BusinessRuleError:
                await db.rollback()
                return None

    results = await asyncio.wait_for(asyncio.gather(*(collect(ref) for ref in references)), 20)
    successes = [row for row in results if row is not None]
    assert len(successes) == (2 if references[0] == references[1] else 1)
    if len(successes) == 2:
        assert successes[0] == successes[1]
    async with sessions() as db:
        assert len((await db.scalars(select(CommissionLedger))).all()) == 1
        assert len((await db.scalars(select(PaymentCallback))).all()) == 1
        wallet = (await db.scalars(select(SellerWallet))).one()
        assert wallet.pending_balance == Decimal("2550") and wallet.available_balance == 0


async def test_missing_payment_is_not_found(client, market):
    response = await client.get(f"{BASE}/{uuid4()}", headers=headers(market.admin))
    assert response.status_code == 404


@pytest.mark.parametrize("fail_second", [False, True])
async def test_multi_brand_allocation_is_atomic(db, market, monkeypatch, fail_second):
    owner = User(
        email="second-brand@example.test",
        password_hash="test-only",
        role=UserRole.seller,
        has_verified_email=True,
    )
    db.add(owner)
    await db.flush()
    seller = Seller(
        user_id=owner.id,
        brand_name="Second brand",
        slug="second-brand",
        status=SellerStatus.active,
        total_slots=50,
    )
    db.add(seller)
    await db.flush()
    db.add(SellerWallet(seller_id=seller.id))
    product = Product(
        seller_id=seller.id,
        name="Second shirt",
        slug="second-shirt",
        price=Decimal("750.25"),
        is_published=True,
    )
    db.add(product)
    await db.flush()
    variant = ProductVariant(
        product_id=product.id,
        sku="SECOND-M",
        size_type=SizeType.alpha,
        size_value="M",
        colour="Ivory",
    )
    db.add(variant)
    await db.flush()
    db.add(ProductInventory(variant_id=variant.id, stock=5, reserved=0))
    await db.commit()
    payload = guest_payload(market)
    values = payload.model_dump()
    values["items"].append({"variant_id": variant.id, "quantity": 1})
    created = await OrderService(db).create_guest_order(type(payload).model_validate(values))
    initiated = await PaymentService(db).initiate(created.order_id, guest_token=created.guest_token)
    await deliver(db, created.order_id, market.admin.id)
    before = await snapshot(db)
    original, calls = CommissionService.settle, []

    async def settle(self, seller_order_id, **kwargs):
        await original(self, seller_order_id, **kwargs)
        calls.append(seller_order_id)
        if fail_second and len(calls) == 2:
            raise RuntimeError("Second brand failed after credit")

    monkeypatch.setattr(CommissionService, "settle", settle)
    if fail_second:
        with pytest.raises(RuntimeError, match="Second brand"):
            await PaymentService(db).record_cod_collection(
                initiated.payment_id, market.admin.id, "MULTI-001"
            )
        await db.rollback()
        assert len(calls) == 2 and await snapshot(db) == before
        return
    receipt = await PaymentService(db).record_cod_collection(
        initiated.payment_id, market.admin.id, "MULTI-001"
    )
    assert receipt.amount == created.total and len(calls) == 2
    wallets = {row.seller_id: row for row in (await db.scalars(select(SellerWallet))).all()}
    assert wallets[market.seller.id].pending_balance == Decimal("2040")
    assert wallets[seller.id].pending_balance == Decimal("637.71")
    assert all(row.available_balance == 0 for row in wallets.values())
    ledgers = (await db.scalars(select(CommissionLedger))).all()
    assert len(ledgers) == 2
    assert sum(row.gross_amount for row in ledgers) == Decimal("3150.25")
    assert (await snapshot(db))["product_inventory"] == before["product_inventory"]
    after = await snapshot(db)
    await PaymentService(db).record_cod_collection(
        initiated.payment_id, market.admin.id, "MULTI-001"
    )
    assert await snapshot(db) == after and len(calls) == 2
