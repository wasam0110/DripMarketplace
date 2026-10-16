"""Deletion preserves financial identity and refuses unsafe self-service requests."""

import pytest
from sqlalchemy import select
from test_marketplace_regressions import guest_payload
from test_marketplace_regressions import market as marketplace_fixture

from app.core.exceptions import BusinessRuleError
from app.core.security import hash_password
from app.models.order import Order, OrderStatus
from app.models.user import UserAddress
from app.schemas.user import DeleteAccountRequest
from app.services.customer_service import CustomerService
from app.services.order_service import OrderService

pytestmark = pytest.mark.integration
market = marketplace_fixture


def deletion():
    return DeleteAccountRequest(password="SecretPass123!", confirm_phrase="DELETE MY ACCOUNT")


@pytest.mark.parametrize("status", [
    OrderStatus.pending_payment, OrderStatus.payment_confirmed,
    OrderStatus.pending_cod_verification, OrderStatus.processing, OrderStatus.shipped,
])
async def test_deletion_blocks_every_active_order_state(db, market, status):
    market.buyer.password_hash = hash_password(deletion().password)
    created = await OrderService(db).create_guest_order(guest_payload(market))
    order = await db.get(Order, created.order_id)
    order.user_id, order.status = market.buyer.id, status
    await db.commit()
    with pytest.raises(BusinessRuleError, match="active order"):
        await CustomerService(db).delete_account(market.buyer.id, deletion())
    assert market.buyer.deleted_at is None


@pytest.mark.parametrize("account", ["admin", "seller_user"])
async def test_privileged_accounts_require_managed_offboarding(db, market, account):
    user = getattr(market, account)
    with pytest.raises(BusinessRuleError, match="managed offboarding"):
        await CustomerService(db).delete_account(user.id, deletion())
    assert user.deleted_at is None


async def test_google_only_deletion_requires_reauthentication(db, market):
    market.buyer.password_hash = None
    market.buyer.google_id = "test-google-subject"
    await db.commit()
    with pytest.raises(BusinessRuleError, match="Set a password"):
        await CustomerService(db).delete_account(market.buyer.id, deletion())


async def test_deletion_clears_profile_but_retains_completed_order(db, market):
    user = market.buyer
    user.password_hash = hash_password(deletion().password)
    user.first_name, user.last_name, user.phone = "Test", "Customer", "03001234567"
    user.google_id = "test-linked-google"
    user.avatar_url = "https://example.test/avatar.webp"
    db.add(UserAddress(user_id=user.id, street="Test street", city="Lahore", province="Punjab"))
    created = await OrderService(db).create_guest_order(guest_payload(market))
    order = await db.get(Order, created.order_id)
    order.user_id, order.status = user.id, OrderStatus.completed
    await db.commit()
    old_version = user.auth_version
    await CustomerService(db).delete_account(user.id, deletion())
    await db.refresh(user)
    await db.refresh(order)
    assert user.deleted_at is not None and user.auth_version == old_version + 1
    assert user.email == f"deleted_{user.id}@wearhowz.deleted"
    assert user.password_hash == "!deleted"
    assert all(getattr(user, field) is None for field in (
        "first_name", "last_name", "phone", "google_id", "avatar_url", "totp_secret",
    ))
    assert order.user_id == user.id and order.status == OrderStatus.completed
    assert await db.scalar(select(UserAddress.id).where(UserAddress.user_id == user.id)) is None
