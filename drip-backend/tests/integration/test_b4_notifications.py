"""B4 acceptance tests for durable, preference-aware notification delivery."""

from __future__ import annotations

import re
from decimal import Decimal
from html import unescape
from unittest.mock import AsyncMock, call
from urllib.parse import parse_qs, urlparse

import pytest
from arq import Retry
from sqlalchemy import func, select
from test_marketplace_regressions import guest_payload
from test_marketplace_regressions import market as marketplace_fixture

from app.core.exceptions import NotFoundError
from app.models.notification import EmailLog, Notification, NotificationOutbox
from app.models.seller import SellerStatus
from app.models.wallet import Payout, PayoutStatus
from app.schemas.notification import UpdatePreferencesRequest
from app.schemas.order import CancelOrderRequest
from app.schemas.user import UpdateNotificationPreferencesRequest
from app.services.admin_service import AdminService
from app.services.customer_service import CustomerService
from app.services.notification_service import NotificationService
from app.services.order_access import authorized_order
from app.services.order_service import OrderService
from app.services.wallet_service import WalletService
from app.tasks import notification_tasks

pytestmark = pytest.mark.integration
market = marketplace_fixture


def _session_context(db):
    context = AsyncMock()
    context.__aenter__.return_value = db
    return context


async def test_checkout_outbox_publishes_registered_worker_once(db, market, monkeypatch):
    created = await OrderService(db).create_guest_order(guest_payload(market))
    event_key = f"order:{created.order_id}:placed"
    event = await db.scalar(
        select(NotificationOutbox).where(NotificationOutbox.event_key == event_key)
    )
    assert event is not None
    assert event.task_name == "send_order_confirmation"
    assert event.args == [str(created.order_id), event_key]

    from app.core import database

    monkeypatch.setattr(database, "AsyncSessionLocal", lambda: _session_context(db))
    redis = AsyncMock()
    redis.enqueue_job.side_effect = RuntimeError("redis unavailable")
    with pytest.raises(Retry):
        await notification_tasks.dispatch_notification_outbox(
            {"redis": redis, "job_try": 1}
        )
    await db.refresh(event)
    assert event.published_at is None
    assert event.attempts == 1
    assert event.last_error == "RuntimeError"

    redis.enqueue_job.side_effect = None
    await notification_tasks.dispatch_notification_outbox({"redis": redis})
    assert redis.enqueue_job.await_args_list[-1] == call(
        "deliver_notification_outbox",
        str(event.id),
        _job_id=f"notification:{event.id}:0:2",
    )
    await db.refresh(event)
    assert event.published_at is not None
    assert event.attempts == 2

    await notification_tasks.dispatch_notification_outbox({"redis": redis})
    assert redis.enqueue_job.await_count == 2


async def test_email_failure_retries_dedupes_escapes_and_signs_guest_link(
    db, market, monkeypatch
):
    market.product.name = '<script>alert("x")</script>'
    await db.commit()
    created = await OrderService(db).create_guest_order(guest_payload(market))
    event_key = f"order:{created.order_id}:placed"

    from app.core import database
    from app.integrations.resend_client import ResendClient

    monkeypatch.setattr(database, "AsyncSessionLocal", lambda: _session_context(db))
    provider = AsyncMock(side_effect=[RuntimeError("temporary"), "receipt-1"])
    monkeypatch.setattr(ResendClient, "send", provider)

    with pytest.raises(Retry):
        await notification_tasks.send_order_confirmation(
            {"job_try": 1}, str(created.order_id), event_key
        )
    log = await db.scalar(select(EmailLog).where(EmailLog.delivery_key == f"{event_key}:email"))
    assert log.status == "failed"
    assert log.attempts == 1

    await notification_tasks.send_order_confirmation(
        {"job_try": 2}, str(created.order_id), event_key
    )
    await notification_tasks.send_order_confirmation(
        {"job_try": 3}, str(created.order_id), event_key
    )
    await db.refresh(log)
    assert log.status == "sent"
    assert log.resend_id == "receipt-1"
    assert log.attempts == 2
    assert provider.await_count == 2
    assert await db.scalar(select(func.count(EmailLog.id))) == 1

    sent_html = provider.await_args_list[-1].kwargs["html"]
    assert "<script>" not in sent_html
    assert "&lt;script&gt;" in sent_html
    href = unescape(re.search(r'href="([^"]+)"', sent_html).group(1))
    guest_token = parse_qs(urlparse(href).query)["guest_token"][0]
    assert (
        await authorized_order(db, created.order_id, guest_token=guest_token)
    ).id == created.order_id
    with pytest.raises(NotFoundError):
        await authorized_order(db, created.order_id, guest_token="forged")


async def test_canonical_preferences_enforce_optional_order_updates(
    db, market, monkeypatch
):
    created = await OrderService(db).create_guest_order(guest_payload(market))
    order = await authorized_order(db, created.order_id, guest_token=created.guest_token)
    order.user_id = market.buyer.id
    await db.commit()

    response = await CustomerService(db).update_notification_prefs(
        market.buyer.id,
        UpdateNotificationPreferencesRequest(
            email_order_updates=False,
            email_promotions=False,
            email_new_arrivals=True,
            sms_order_updates=True,
            whatsapp_order_updates=False,
        ),
    )
    canonical = await NotificationService(db).get_preferences(market.buyer.id)
    assert response.email_order_updates is canonical.order_updates_email is False
    assert response.email_promotions is canonical.promotions_email is False
    assert response.email_new_arrivals is canonical.email_new_arrivals is True
    assert response.sms_order_updates is canonical.sms_order_updates is True
    assert response.whatsapp_order_updates is canonical.whatsapp_order_updates is False
    await NotificationService(db).update_preferences(
        market.buyer.id, UpdatePreferencesRequest(order_updates_push=False)
    )

    from app.integrations.resend_client import ResendClient

    provider = AsyncMock(return_value="receipt")
    monkeypatch.setattr(ResendClient, "send", provider)
    service = NotificationService(db)
    await service.notify_order_status(created.order_id, "shipped")
    assert await db.scalar(select(func.count(Notification.id))) == 0
    assert await db.scalar(select(func.count(EmailLog.id))) == 0

    # Placement confirmations are required transactional notices, not marketing.
    await service.notify_order_placed(created.order_id)
    assert await db.scalar(select(func.count(Notification.id))) == 1
    assert await db.scalar(select(func.count(EmailLog.id))) == 1
    assert provider.await_count == 1


async def test_business_operations_create_payout_seller_and_status_events(db, market):
    created = await OrderService(db).create_guest_order(guest_payload(market))
    await OrderService(db).cancel_order(
        created.order_id,
        None,
        CancelOrderRequest(reason="Changed my mind"),
        created.guest_token,
    )

    market.seller.status = SellerStatus.pending_approval
    await db.commit()
    admin = AdminService(db)
    await admin.approve_seller(market.seller.id, market.admin.id)
    market.seller.status = SellerStatus.pending_approval
    await db.commit()
    await admin.reject_seller(market.seller.id, market.admin.id, "Incomplete documents")

    payouts = [
        Payout(
            seller_id=market.seller.id,
            amount=Decimal("500"),
            payment_method="bank_transfer",
            payment_detail=f"Account {index}",
            status=status,
        )
        for index, status in enumerate(
            [PayoutStatus.requested, PayoutStatus.requested, PayoutStatus.approved], start=1
        )
    ]
    db.add_all(payouts)
    await db.commit()
    wallet = WalletService(db)
    await wallet.admin_approve_payout(payouts[0].id, market.admin.id)
    await wallet.admin_reject_payout(payouts[1].id, market.admin.id, "Invalid details")
    await wallet.admin_complete_payout(
        payouts[2].id, market.admin.id, "bank-reference"
    )

    events = list((await db.scalars(select(NotificationOutbox))).all())
    keyed = {event.event_key: event.task_name for event in events}
    assert keyed[f"order:{created.order_id}:status:cancelled"] == "send_order_status_update"
    assert keyed[f"seller:{market.seller.id}:decision:approved"] == "notify_seller_decision"
    assert keyed[f"seller:{market.seller.id}:decision:rejected"] == "notify_seller_decision"
    assert keyed[f"payout:{payouts[0].id}:status:approved"] == "send_payout_notification"
    assert keyed[f"payout:{payouts[1].id}:status:rejected"] == "send_payout_notification"
    assert keyed[f"payout:{payouts[2].id}:status:completed"] == "send_payout_notification"
