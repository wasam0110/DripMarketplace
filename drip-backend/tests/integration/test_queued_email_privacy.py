"""Legacy queue recipients are checked against committed identity at send time."""

import asyncio
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from arq import Retry
from sqlalchemy.ext.asyncio import async_sessionmaker
from test_preship_deletion import deletion
from test_release_native import db as committed_db

from app.core.config import settings
from app.core.security import (
    create_access_token,
    create_email_verify_token,
    create_password_reset_token,
    hash_password,
)
from app.models.notification import NotificationPreference
from app.models.order import Order, OrderStatus, StoredPaymentMethod
from app.models.seller import Seller, SellerStatus
from app.models.user import User, UserRole
from app.services.account_lifecycle import lock_active_user
from app.services.customer_service import CustomerService
from app.tasks import email_tasks

pytestmark = pytest.mark.integration
db = committed_db
AUTH_JOBS = [
    ("verification_email", create_email_verify_token, "drip-email-verify"),
    ("password_reset_email", create_password_reset_token, "drip-pwd-reset"),
]


@pytest.fixture
async def recipient(db, test_engine, monkeypatch):
    import app.core.database as database

    user = User(
        email="recipient@example.com",
        first_name="Current",
        password_hash=hash_password(deletion().password),
    )
    db.add(user)
    await db.commit()
    monkeypatch.setattr(
        database, "AsyncSessionLocal", async_sessionmaker(test_engine, expire_on_commit=False)
    )
    return user


@pytest.mark.parametrize("kind,make_token,audience", AUTH_JOBS)
async def test_auth_jobs_send_current_identity_and_retry_provider_failure(
    db, recipient, monkeypatch, kind, make_token, audience
):
    sender = AsyncMock(side_effect=[False, True, True])
    monkeypatch.setattr(email_tasks, "send_" + kind, sender)
    task = getattr(email_tasks, "task_send_" + kind)
    token = make_token(str(recipient.id))
    with pytest.raises(Retry) as error:
        await task({"job_try": 2}, recipient.email, "Stale name", token)
    assert error.value.defer_score == 60_000
    await task({}, recipient.email, "Stale name", token)
    assert sender.await_count == 2
    sender.assert_awaited_with(recipient.email, "Current", token)
    # Forgot-password lookup normalizes case; old queued inputs may not.
    await task({}, recipient.email.upper(), "Stale name", token)
    assert sender.await_count == 3


@pytest.mark.parametrize("kind,make_token,audience", AUTH_JOBS)
async def test_auth_jobs_suppress_invalid_expired_wrong_purpose_and_missing_identity(
    recipient, monkeypatch, kind, make_token, audience
):
    sender = AsyncMock(return_value=True)
    monkeypatch.setattr(email_tasks, "send_" + kind, sender)
    task = getattr(email_tasks, "task_send_" + kind)
    expired, _ = create_access_token(
        subject=str(recipient.id),
        role="customer",
        extra_claims={"aud": audience, "exp": datetime.now(UTC) - timedelta(seconds=1)},
    )
    wrong_purpose = (
        create_password_reset_token if kind == "verification_email" else create_email_verify_token
    )(str(recipient.id))
    for token in (
        "broken-token",
        expired,
        wrong_purpose,
        make_token(str(uuid4())),
        make_token("not-a-uuid"),
    ):
        await task({}, recipient.email, "Old name", token)
    await task({}, "wrong@example.com", "Old name", make_token(str(recipient.id)))
    sender.assert_not_awaited()


@pytest.mark.parametrize("kind,make_token,audience", AUTH_JOBS)
async def test_deleted_account_and_reassigned_email_never_receive_queued_auth(
    db, recipient, monkeypatch, kind, make_token, audience
):
    sender = AsyncMock(return_value=True)
    monkeypatch.setattr(email_tasks, "send_" + kind, sender)
    old_email, uid = recipient.email, recipient.id
    token = make_token(str(uid))
    await CustomerService(db).delete_account(uid, deletion())
    db.add(User(email=old_email, first_name="Different person", password_hash="test-only"))
    await db.commit()
    await getattr(email_tasks, "task_send_" + kind)({}, old_email, "Old name", token)
    sender.assert_not_awaited()


async def test_completed_auth_actions_and_redis_outage(db, recipient, isolated_redis, monkeypatch):
    verify = AsyncMock(return_value=True)
    reset = AsyncMock(return_value=True)
    monkeypatch.setattr(email_tasks, "send_verification_email", verify)
    monkeypatch.setattr(email_tasks, "send_password_reset_email", reset)
    recipient.has_verified_email = True
    await db.commit()
    await email_tasks.task_send_verification_email(
        {}, recipient.email, "Old", create_email_verify_token(str(recipient.id))
    )
    token = create_password_reset_token(str(recipient.id))
    key = "password-reset-used:" + sha256(token.encode()).hexdigest()
    await isolated_redis.set(key, "1", ex=3600)
    await email_tasks.task_send_password_reset_email({}, recipient.email, "Old", token)
    verify.assert_not_awaited()
    reset.assert_not_awaited()
    await isolated_redis.delete(key)
    with monkeypatch.context() as patch:
        patch.setattr(isolated_redis, "exists", AsyncMock(side_effect=ConnectionError("offline")))
        with pytest.raises(Retry):
            await email_tasks.task_send_password_reset_email({}, recipient.email, "Old", token)
    reset.assert_not_awaited()
    await email_tasks.task_send_password_reset_email({}, recipient.email, "Old", token)
    reset.assert_awaited_once()


@pytest.mark.parametrize("kind,make_token,audience", AUTH_JOBS)
@pytest.mark.parametrize("first", ["delete", "email"])
async def test_email_deletion_race_serializes_provider_handoff(
    db, recipient, test_engine, monkeypatch, kind, make_token, audience, first
):
    uid, email = recipient.id, recipient.email
    token = make_token(str(uid))
    started, release = asyncio.Event(), asyncio.Event()

    async def send(*args):
        started.set()
        await release.wait()
        return True

    sender = AsyncMock(side_effect=send)
    monkeypatch.setattr(email_tasks, "send_" + kind, sender)
    factory = async_sessionmaker(test_engine, expire_on_commit=False)
    task = getattr(email_tasks, "task_send_" + kind)

    async def remove():
        async with factory() as session:
            await CustomerService(session).delete_account(uid, deletion())

    pending = None
    sending = None
    try:
        if first == "delete":
            async with factory() as winner:
                await lock_active_user(winner, uid)
                pending = asyncio.create_task(task({}, email, "Old", token))
                await asyncio.sleep(0.1)
                assert not pending.done()
                await CustomerService(winner).delete_account(uid, deletion())
                await asyncio.wait_for(pending, timeout=10)
            sender.assert_not_awaited()
        else:
            sending = asyncio.create_task(task({}, email, "Old", token))
            await asyncio.wait_for(started.wait(), timeout=10)
            pending = asyncio.create_task(remove())
            await asyncio.sleep(0.1)
            assert not pending.done()
            release.set()
            await asyncio.wait_for(sending, timeout=10)
            await asyncio.wait_for(pending, timeout=10)
            sender.assert_awaited_once()
        await db.refresh(recipient)
        assert recipient.deleted_at is not None
    finally:
        release.set()
        for job in (pending, sending):
            if job is not None and not job.done():
                job.cancel()
                await asyncio.gather(job, return_exceptions=True)


ORDER_JOBS = [
    ("order_confirmation", "send_order_confirmation_email", (100, [])),
    ("shipping_notification", "send_shipping_notification_email", ("T1", "TCS", "Brand")),
    ("cod_timeout", "send_cod_timeout_email", ()),
]


@pytest.mark.parametrize("kind,provider,extra", ORDER_JOBS)
@pytest.mark.parametrize("guest", [False, True])
async def test_legacy_order_emails_require_the_current_order_recipient(
    db, recipient, monkeypatch, kind, provider, extra, guest
):
    email = "guest@example.com" if guest else recipient.email
    order = Order(
        order_number="WHZ-PRIVACY",
        user_id=None if guest else recipient.id,
        guest_email=email if guest else None,
        guest_name="Current guest" if guest else None,
        status=OrderStatus.completed,
        subtotal=100,
        total=100,
        payment_method=StoredPaymentMethod.cod,
    )
    db.add(order)
    await db.commit()
    sender = AsyncMock(return_value=True)
    monkeypatch.setattr(email_tasks, provider, sender)
    task = getattr(email_tasks, "task_send_" + kind)
    await task({}, email, "Stale", "MISSING", *extra)
    await task({}, "someone-else@example.com", "Stale", order.order_number, *extra)
    sender.assert_not_awaited()
    await task({}, email, "Stale", order.order_number, *extra)
    sender.assert_awaited_once_with(
        email, "Current guest" if guest else "Current", order.order_number, *extra
    )
    sender.reset_mock()
    if not guest:
        await CustomerService(db).delete_account(recipient.id, deletion())
        db.add(User(email=email, password_hash="test-only"))
        await db.commit()
        await task({}, email, "Stale", order.order_number, *extra)
        sender.assert_not_awaited()


async def test_legacy_seller_approval_requires_active_matching_brand(db, recipient, monkeypatch):
    recipient.role = UserRole.seller
    seller = Seller(
        user_id=recipient.id, brand_name="Brand", slug="brand", status=SellerStatus.active
    )
    db.add(seller)
    await db.commit()
    sender = AsyncMock(return_value=True)
    monkeypatch.setattr(email_tasks, "send_seller_approved_email", sender)
    task = email_tasks.task_send_seller_approved
    await task({}, recipient.email, "Other brand", "https://untrusted.invalid")
    await task({}, "other@example.com", "Brand", "https://untrusted.invalid")
    sender.assert_not_awaited()
    await task({}, recipient.email, "Brand", "https://untrusted.invalid")
    sender.assert_awaited_once_with(
        recipient.email, "Brand", f"{settings.FRONTEND_URL}/seller/dashboard"
    )
    sender.reset_mock()
    seller.status = SellerStatus.suspended
    await db.commit()
    await task({}, recipient.email, "Brand", "https://untrusted.invalid")
    seller.status = SellerStatus.active
    seller.deleted_at = datetime.now(UTC)
    await db.commit()
    await task({}, recipient.email, "Brand", "https://untrusted.invalid")
    seller.deleted_at = None
    recipient.deleted_at = datetime.now(UTC)
    await db.commit()
    await task({}, recipient.email, "Brand", "https://untrusted.invalid")
    sender.assert_not_awaited()


@pytest.mark.parametrize("kind,provider,extra", ORDER_JOBS[1:])
async def test_legacy_order_updates_respect_database_and_legacy_opt_out(
    db, recipient, monkeypatch, isolated_redis, kind, provider, extra
):
    order = Order(
        order_number="WHZ-OPT-OUT",
        user_id=recipient.id,
        status=OrderStatus.completed,
        subtotal=100,
        total=100,
        payment_method=StoredPaymentMethod.cod,
    )
    db.add(order)
    await db.commit()
    sender = AsyncMock(return_value=True)
    monkeypatch.setattr(email_tasks, provider, sender)
    task = getattr(email_tasks, "task_send_" + kind)
    await isolated_redis.hset(f"notif_prefs:{recipient.id}", "email_order_updates", "false")
    await task({}, recipient.email, "Old", order.order_number, *extra)
    sender.assert_not_awaited()
    await isolated_redis.delete(f"notif_prefs:{recipient.id}")
    db.add(
        NotificationPreference(
            user_id=recipient.id, order_updates_email=False, legacy_imported=True
        )
    )
    await db.commit()
    await task({}, recipient.email, "Old", order.order_number, *extra)
    sender.assert_not_awaited()
