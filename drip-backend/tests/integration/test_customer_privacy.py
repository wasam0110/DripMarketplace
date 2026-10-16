"""Limited customer cleanup, durable external retry and deletion interleavings."""

import asyncio
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker
from test_marketplace_regressions import guest_payload
from test_marketplace_regressions import market as marketplace_fixture
from test_preship_deletion import deletion
from test_release_native import db as committed_db

from app.core.config import settings
from app.core.exceptions import BusinessRuleError, NotFoundError
from app.core.security import create_access_token, hash_password
from app.integrations.supabase_storage import SupabaseStorage
from app.models.notification import Notification, NotificationOutbox, NotificationPreference
from app.models.order import Order, OrderItem, OrderStatus, SellerOrder
from app.models.return_ import Dispute, Return, ReturnStatus
from app.models.review import Review, ReviewImage
from app.models.user import UserAddress
from app.schemas.order import AddToCartRequest
from app.schemas.return_ import CreateReturnRequest, OpenDisputeRequest
from app.schemas.user import CreateAddressRequest, UpdateProfileRequest
from app.services.account_lifecycle import lock_active_user
from app.services.cart_service import CartService
from app.services.customer_privacy import cleanup_deleted_customer
from app.services.customer_service import CustomerService
from app.services.notification_service import NotificationService
from app.services.order_service import OrderService
from app.services.return_service import ReturnService
from app.tasks.notification_tasks import broadcast_notification, deliver_notification_outbox

pytestmark = pytest.mark.integration
market = marketplace_fixture
db = committed_db


@pytest.fixture
def task_sessions(monkeypatch, test_engine):
    import app.core.database as database

    monkeypatch.setattr(
        database, "AsyncSessionLocal", async_sessionmaker(test_engine, expire_on_commit=False)
    )


async def ready_to_delete(db, market):
    market.buyer.password_hash = hash_password(deletion().password)
    created = await OrderService(db).create_guest_order(guest_payload(market))
    order = await db.get(Order, created.order_id)
    order.user_id, order.status = market.buyer.id, OrderStatus.completed
    await db.commit()
    return order


async def test_late_authentication_writes_cannot_restore_deleted_credentials(db, market):
    from datetime import UTC, datetime, timedelta

    from app.repositories.user_repo import SessionRepository, UserRepository

    await ready_to_delete(db, market)
    uid = market.buyer.id
    await CustomerService(db).delete_account(uid, deletion())
    await UserRepository.verify_email(db, uid)
    await UserRepository.update_password(db, uid, "must-not-be-restored")
    await UserRepository.update_last_login(db, uid)
    await UserRepository.set_totp(db, uid, "must-not-be-restored", True)
    await db.commit()
    await db.refresh(market.buyer)
    assert market.buyer.password_hash == "!deleted"
    assert not market.buyer.has_verified_email and not market.buyer.is_2fa_enabled
    assert market.buyer.totp_secret is None and market.buyer.last_login_at is None
    with pytest.raises(NotFoundError):
        await SessionRepository.create(
            db, user_id=uid, token_hash="a" * 64, expires_at=datetime.now(UTC) + timedelta(days=1)
        )


async def test_cache_outage_keeps_cleanup_durable(
    db, market, task_sessions, isolated_redis, monkeypatch
):
    import app.services.customer_privacy as privacy

    await ready_to_delete(db, market)
    uid = market.buyer.id
    key = f"wishlist:{uid}"
    await isolated_redis.sadd(key, "private-test-value")
    real_clear = privacy.clear_customer_cache
    monkeypatch.setattr(
        privacy, "clear_customer_cache", AsyncMock(side_effect=RuntimeError("offline"))
    )
    await CustomerService(db).delete_account(uid, deletion())
    event = await db.scalar(
        select(NotificationOutbox).where(NotificationOutbox.task_name == "cleanup_deleted_customer")
    )
    assert event and event.completed_at is None
    assert await isolated_redis.exists(key)
    event_id = str(event.id)
    await db.rollback()
    monkeypatch.setattr(privacy, "clear_customer_cache", real_clear)
    await deliver_notification_outbox({}, event_id)
    await db.refresh(event)
    assert event.completed_at is not None and not await isolated_redis.exists(key)


async def test_failed_deletion_commit_does_not_publish_cleanup(
    db, market, isolated_redis, monkeypatch
):
    await ready_to_delete(db, market)
    uid = market.buyer.id
    review = Review(user_id=uid, product_id=market.product.id, rating=5, body="Still retained")
    db.add(review)
    await db.commit()
    rid = review.id
    await isolated_redis.sadd(f"wishlist:{uid}", "retained")
    monkeypatch.setattr(db, "commit", AsyncMock(side_effect=RuntimeError("commit failed")))
    with pytest.raises(RuntimeError, match="commit failed"):
        await CustomerService(db).delete_account(uid, deletion())
    await db.rollback()
    await db.refresh(market.buyer)
    await db.refresh(review)
    assert market.buyer.deleted_at is None and review.id == rid and review.body == "Still retained"
    assert (
        await db.scalar(
            select(func.count(NotificationOutbox.id)).where(
                NotificationOutbox.task_name == "cleanup_deleted_customer"
            )
        )
        == 0
    )
    assert await isolated_redis.sismember(f"wishlist:{uid}", "retained")


async def test_cleanup_retains_financial_record_and_retries_external_failure(
    db,
    market,
    isolated_redis,
    task_sessions,
    monkeypatch,
):
    order = await ready_to_delete(db, market)
    user_id = market.buyer.id
    storage = SupabaseStorage()
    avatar_path = f"products/{user_id}/{uuid4()}.webp"
    market.buyer.avatar_url = storage.get_public_url(
        settings.SUPABASE_STORAGE_BUCKET_AVATARS, avatar_path
    )
    review = Review(
        user_id=user_id,
        product_id=market.product.id,
        rating=4,
        title="My personal name",
        body="My personal address",
    )
    db.add(review)
    await db.flush()
    review_path = f"products/{review.id}/{uuid4()}.webp"
    db.add(
        ReviewImage(
            review_id=review.id,
            url=storage.get_public_url(settings.SUPABASE_STORAGE_BUCKET_PRODUCTS, review_path),
        )
    )
    db.add(Notification(user_id=user_id, type="test", title="Private", body="Private"))
    db.add(NotificationPreference(user_id=user_id))
    db.add(UserAddress(user_id=user_id, street="Private", city="Lahore", province="Punjab"))
    await db.commit()
    for key in (f"cart:{user_id}", f"wishlist:{user_id}", f"notif_prefs:{user_id}"):
        await isolated_redis.set(key, "test-only")
    await CustomerService(db).delete_account(user_id, deletion())
    for model in (Notification, NotificationPreference, UserAddress):
        assert (
            await db.scalar(select(func.count()).select_from(model).where(model.user_id == user_id))
            == 0
        )
    assert await db.scalar(select(func.count(ReviewImage.id))) == 0
    await db.refresh(review)
    await db.refresh(order)
    assert review.rating == 4 and review.title is None and review.body is None
    assert order.user_id == user_id and order.total == 2600
    assert not await isolated_redis.exists(
        f"cart:{user_id}", f"wishlist:{user_id}", f"notif_prefs:{user_id}"
    )
    event = await db.scalar(
        select(NotificationOutbox).where(NotificationOutbox.task_name == "cleanup_deleted_customer")
    )
    assert event is not None and len(event.args[1]) == 2
    event_id = str(event.id)
    await db.rollback()
    remove = AsyncMock(side_effect=RuntimeError("synthetic provider outage"))
    monkeypatch.setattr(SupabaseStorage, "delete", remove)
    await deliver_notification_outbox({}, event_id)
    await db.refresh(event)
    assert event.completed_at is None and event.last_error == "RuntimeError"
    assert len(event.args[1]) == 2
    await db.rollback()
    remove.side_effect = None
    await deliver_notification_outbox({}, event_id)
    await db.refresh(event)
    assert event.completed_at is not None and event.args[1] == []
    assert remove.await_count == 3  # failed avatar + successful avatar/review retry
    await db.rollback()
    await deliver_notification_outbox({}, event_id)
    assert remove.await_count == 3


async def test_cleanup_never_deletes_unowned_shared_or_external_assets(
    db,
    market,
    task_sessions,
    monkeypatch,
):
    await ready_to_delete(db, market)
    user_id, other_id = market.buyer.id, market.seller_user.id
    storage = SupabaseStorage()
    shared = storage.get_public_url(
        settings.SUPABASE_STORAGE_BUCKET_AVATARS, f"products/{user_id}/{uuid4()}.webp"
    )
    market.seller_user.avatar_url = shared
    await db.commit()
    await CustomerService(db).delete_account(user_id, deletion())
    await db.rollback()
    remove = AsyncMock()
    monkeypatch.setattr(SupabaseStorage, "delete", remove)
    for url in (
        shared,
        storage.get_public_url(settings.SUPABASE_STORAGE_BUCKET_AVATARS, f"products/{user_id}/"),
        "https://outside.example/private.png",
        storage.get_public_url(
            settings.SUPABASE_STORAGE_BUCKET_AVATARS, f"products/{other_id}/{uuid4()}.webp"
        ),
    ):
        with pytest.raises(ValueError, match="manual review"):
            await cleanup_deleted_customer(
                {},
                str(user_id),
                [
                    {
                        "url": url,
                        "owner": str(user_id),
                        "bucket": settings.SUPABASE_STORAGE_BUCKET_AVATARS,
                    }
                ],
            )
    remove.assert_not_awaited()


async def test_deleted_user_cannot_be_recreated_by_late_writes_or_queued_notices(
    db,
    market,
    client,
    isolated_redis,
    task_sessions,
    monkeypatch,
):
    order = await ready_to_delete(db, market)
    user_id, order_id, variant_id = market.buyer.id, order.id, market.variant.id
    token, _ = create_access_token(subject=str(user_id), role="customer")
    await CustomerService(db).delete_account(user_id, deletion())
    response = await client.get(
        "/api/v1/customers/me", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 401
    actions = [
        lambda: CustomerService(db).update_profile(
            user_id, UpdateProfileRequest(first_name="Resurrected")
        ),
        lambda: CustomerService(db).create_address(
            user_id, CreateAddressRequest(street="New street", city="Lahore", province="Punjab")
        ),
        lambda: CartService(db, isolated_redis).add_item(
            user_id, AddToCartRequest(variant_id=variant_id, quantity=1)
        ),
        lambda: CustomerService(db).add_to_wishlist(user_id, market.product.id),
        lambda: NotificationService(db).get_preferences(user_id),
    ]
    for action in actions:
        with pytest.raises(NotFoundError):
            await action()
    send = AsyncMock(side_effect=AssertionError("Deleted customer must not receive email"))
    monkeypatch.setattr(NotificationService, "send_email", send)
    await NotificationService(db).notify_order_placed(order_id)
    await NotificationService(db).notify_order_status(order_id, "delivered")
    await db.rollback()
    await broadcast_notification(
        {}, [str(user_id)], "Queued before deletion", "Private", None, "privacy-test"
    )
    assert (
        await db.scalar(select(func.count(Notification.id)).where(Notification.user_id == user_id))
        == 0
    )
    send.assert_not_awaited()


@pytest.mark.parametrize("operation", ["return", "dispute"])
@pytest.mark.parametrize("first", ["delete", "case"])
async def test_deletion_and_new_case_serialize(test_engine, db, market, operation, first):
    order = await ready_to_delete(db, market)
    uid, oid = market.buyer.id, order.id
    so = await db.scalar(select(SellerOrder).where(SellerOrder.order_id == oid))
    item = await db.scalar(select(OrderItem).where(OrderItem.order_id == oid))
    payload = CreateReturnRequest(
        seller_order_id=so.id,
        reason="Product does not fit",
        items=[{"order_item_id": item.id, "quantity": 1}],
    )
    ret = Return(
        order_id=oid,
        seller_order_id=so.id,
        user_id=uid,
        status=ReturnStatus.rejected,
        reason="Previously rejected",
    )
    db.add(ret)
    await db.commit()
    rid = ret.id

    async def case(session):
        service = ReturnService(session)
        if operation == "return":
            return await service.request_return(uid, payload)
        return await service.open_dispute(
            rid, uid, OpenDisputeRequest(message="Please review my rejected return")
        )

    async def remove(session):
        return await CustomerService(session).delete_account(uid, deletion())

    actions = {"delete": remove, "case": case}
    second = "case" if first == "delete" else "delete"
    factory = async_sessionmaker(test_engine, expire_on_commit=False)
    async with factory() as winner:
        await lock_active_user(winner, uid)

        async def competing():
            async with factory() as session:
                return await actions[second](session)

        pending = asyncio.create_task(competing())
        try:
            await asyncio.sleep(0.1)
            assert not pending.done(), "Competing operation bypassed the account lock"
            await actions[first](winner)
            with pytest.raises(NotFoundError if first == "delete" else BusinessRuleError):
                await asyncio.wait_for(pending, timeout=10)
        finally:
            if not pending.done():
                pending.cancel()
                await asyncio.gather(pending, return_exceptions=True)
    await db.refresh(market.buyer)
    assert (market.buyer.deleted_at is not None) == (first == "delete")
    model = Return if operation == "return" else Dispute
    active = await db.scalar(
        select(func.count())
        .select_from(model)
        .where(
            model.user_id == uid,
            model.status != ReturnStatus.rejected if model is Return else model.user_id == uid,
        )
    )
    assert active == (0 if first == "delete" else 1)
