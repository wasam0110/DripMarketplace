"""Manual registration receipts: API permissions, replay and native database races."""

import asyncio
from decimal import Decimal
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.api.v1.admin.brands import record_registration_payment
from app.core.exceptions import BusinessRuleError
from app.core.security import create_access_token
from app.models.notification import NotificationOutbox
from app.models.seller import Seller, SellerStatus
from app.models.user import User, UserRole
from app.schemas.admin import SellerRegistrationPaymentRequest
from app.services.admin_service import AdminService


async def seed_seller(db, status="pending_payment", fee="5000.25"):
    ids = [uuid4() for _ in range(4)]
    for identity, role in zip(
        ids[:3], [UserRole.seller, UserRole.admin, UserRole.admin], strict=True
    ):
        db.add(
            User(
                id=identity,
                email=f"{identity}@example.test",
                password_hash="test-only",
                role=role,
                has_verified_email=True,
            )
        )
    await db.flush()
    db.add(
        Seller(
            id=ids[3],
            user_id=ids[0],
            brand_name="Payment Test Label",
            slug="payment-test-label",
            status=SellerStatus(status),
            registration_fee=Decimal(fee),
        )
    )
    await db.commit()
    return ids


def headers(identity, role="admin"):
    token, _ = create_access_token(subject=str(identity), role=role)
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_registration_receipt_readback_and_identical_replay(client, db):
    _, first_admin, second_admin, seller_id = await seed_seller(db)
    path = f"/api/v1/admin/sellers/{seller_id}"
    payload = {"amount": "5000.25", "reference": "  BANK-123  "}
    response = await client.post(
        path + "/registration-payment", headers=headers(first_admin), json=payload
    )
    assert response.status_code == 200, response.text
    assert response.json() == {"status": "pending_approval"}
    first = (await client.get(path, headers=headers(first_admin))).json()
    assert first["registration_amount_due"] == "0.00"
    assert first["registration_fee"] == "5000.25"
    assert first["registration_payment_reference"] == "BANK-123"
    assert first["registration_paid_by"] == str(first_admin)
    assert first["registration_paid_at"] is not None
    # A later approval is explicit; replaying the receipt must not rewind it.
    await AdminService(db).approve_seller(seller_id, second_admin)
    response = await client.post(
        path + "/registration-payment", headers=headers(second_admin), json=payload
    )
    assert response.json() == {"status": "active"}
    replay = (await client.get(path, headers=headers(second_admin))).json()
    for field in ("registration_paid_at", "registration_paid_by", "registration_payment_reference"):
        assert replay[field] == first[field]
    for changed in (
        {"amount": "5000.24", "reference": "BANK-123"},
        {"amount": "5000.25", "reference": "OTHER-REF"},
    ):
        response = await client.post(
            path + "/registration-payment", headers=headers(second_admin), json=changed
        )
        assert response.status_code == 422


@pytest.mark.asyncio
@pytest.mark.parametrize("amount", ["5000.24", "5000.26", "5000.251", "0"])
async def test_wrong_registration_amount_does_not_record_payment(client, db, amount):
    _, admin_id, _, seller_id = await seed_seller(db)
    path = f"/api/v1/admin/sellers/{seller_id}"
    response = await client.post(
        path + "/registration-payment",
        headers=headers(admin_id),
        json={"amount": amount, "reference": "BANK-123"},
    )
    assert response.status_code == 422
    receipt = (await client.get(path, headers=headers(admin_id))).json()
    assert receipt["status"] == "pending_payment"
    assert receipt["registration_amount_due"] == "5000.25"
    assert receipt["registration_paid_at"] is None


@pytest.mark.asyncio
@pytest.mark.parametrize("status", ["pending_approval", "active", "rejected", "suspended"])
async def test_ineligible_state_does_not_record_payment(client, db, status):
    _, admin_id, _, seller_id = await seed_seller(db, status)
    response = await client.post(
        f"/api/v1/admin/sellers/{seller_id}/registration-payment",
        headers=headers(admin_id),
        json={"amount": "5000.25", "reference": "BANK-123"},
    )
    assert response.status_code == 422
    row = await db.get(Seller, seller_id, populate_existing=True)
    assert row.status.value == status
    assert row.registration_paid_at is None


@pytest.mark.asyncio
async def test_zero_fee_and_partial_legacy_record_are_not_fake_receipts(client, db):
    _, admin_id, _, seller_id = await seed_seller(db, "pending_approval", "0")
    path = f"/api/v1/admin/sellers/{seller_id}"
    receipt = (await client.get(path, headers=headers(admin_id))).json()
    assert receipt["registration_amount_due"] == "0.00"
    assert receipt["registration_paid_at"] is None
    assert (
        await client.post(
            path + "/registration-payment",
            headers=headers(admin_id),
            json={"amount": "0", "reference": "BANK-123"},
        )
    ).status_code == 422
    row = await db.get(Seller, seller_id)
    row.status, row.registration_fee = SellerStatus.pending_payment, Decimal("5000.25")
    row.registration_payment_reference = "LEGACY-PARTIAL"
    await db.commit()
    response = await client.post(
        path + "/registration-payment",
        headers=headers(admin_id),
        json={"amount": "5000.25", "reference": "BANK-123"},
    )
    assert response.status_code == 422
    await db.refresh(row)
    assert row.registration_payment_reference == "LEGACY-PARTIAL"
    assert row.registration_paid_at is None


@pytest.mark.asyncio
@pytest.mark.parametrize("role", ["customer", "seller", "guest", "unverified"])
async def test_registration_payment_requires_verified_admin(client, db, role):
    owner, admin_id, _, seller_id = await seed_seller(db)
    if role == "customer":
        user = await db.get(User, owner)
        user.role = UserRole.customer
        await db.commit()
    if role == "unverified":
        user = await db.get(User, admin_id)
        user.has_verified_email = False
        await db.commit()
    auth = (
        {}
        if role == "guest"
        else headers(
            admin_id if role == "unverified" else owner, "admin" if role == "unverified" else role
        )
    )
    response = await client.post(
        f"/api/v1/admin/sellers/{seller_id}/registration-payment",
        headers=auth,
        json={"amount": "5000.25", "reference": "BANK-123"},
    )
    assert response.status_code in {401, 403}
    row = await db.get(Seller, seller_id, populate_existing=True)
    assert row.registration_paid_at is None


async def run_action(db, action, seller_id, admin_id, reference):
    try:
        if action == "payment":
            return await record_registration_payment(
                seller_id,
                SellerRegistrationPaymentRequest(amount="5000.25", reference=reference),
                db,
                {"sub": str(admin_id)},
            )
        if action == "approve":
            return await AdminService(db).approve_seller(seller_id, admin_id)
        return await AdminService(db).reject_seller(
            seller_id, admin_id, "Registration application policy review."
        )
    finally:
        # Request session close also rolls back any remaining read/replay transaction.
        await db.rollback()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "first_action,second_action,reference,rollback_first",
    [
        ("payment", "payment", "BANK-123", False),
        ("payment", "payment", "OTHER-REF", False),
        ("reject", "payment", "BANK-123", False),
        ("payment", "reject", "BANK-123", False),
        ("payment", "approve", "BANK-123", False),
        ("payment", "payment", "BANK-123", True),
    ],
)
async def test_registration_payment_races(
    test_engine, monkeypatch, first_action, second_action, reference, rollback_first
):
    sessions = async_sessionmaker(test_engine, expire_on_commit=False, autoflush=False)
    async with sessions() as seed:
        _, first_admin, second_admin, seller_id = await seed_seller(seed)
    async with sessions() as first, sessions() as second, test_engine.connect() as observer:
        first_pid = await first.scalar(text("SELECT pg_backend_pid()"))
        second_pid = await second.scalar(text("SELECT pg_backend_pid()"))
        cached = await second.get(Seller, seller_id)
        assert cached.registration_paid_at is None
        await first.scalar(select(Seller).where(Seller.id == seller_id).with_for_update())
        if rollback_first:
            monkeypatch.setattr(
                first, "commit", AsyncMock(side_effect=RuntimeError("Injected commit failure"))
            )
        task = asyncio.create_task(
            run_action(second, second_action, seller_id, second_admin, reference)
        )
        try:

            async def wait_for_lock():
                while not await observer.scalar(
                    text("SELECT :first = ANY(pg_blocking_pids(:second))"),
                    {"first": first_pid, "second": second_pid},
                ):
                    assert not task.done()
                    await asyncio.sleep(0.02)

            await asyncio.wait_for(wait_for_lock(), 5)
            if rollback_first:
                with pytest.raises(RuntimeError, match="Injected"):
                    await run_action(first, first_action, seller_id, first_admin, "BANK-123")
            else:
                await run_action(first, first_action, seller_id, first_admin, "BANK-123")
            rejected = first_action == "reject" or (
                second_action == "payment" and reference != "BANK-123"
            )
            if rejected:
                with pytest.raises(BusinessRuleError):
                    await asyncio.wait_for(task, 10)
            else:
                assert isinstance(await asyncio.wait_for(task, 10), dict)
        finally:
            if not task.done():
                task.cancel()
            await asyncio.gather(task, return_exceptions=True)
    async with sessions() as verify:
        saved = await verify.get(Seller, seller_id)
        if first_action == "reject":
            assert saved.status == SellerStatus.rejected
            assert saved.registration_paid_at is None
        else:
            assert saved.registration_paid_by == (second_admin if rollback_first else first_admin)
            assert saved.registration_payment_reference == "BANK-123"
            assert saved.registration_paid_at is not None
            assert (
                saved.status.value
                == {"payment": "pending_approval", "reject": "rejected", "approve": "active"}[
                    second_action
                ]
            )
        notifications = (await verify.scalars(select(NotificationOutbox))).all()
        assert len(notifications) == (
            1 if "reject" in (first_action, second_action) or second_action == "approve" else 0
        )
