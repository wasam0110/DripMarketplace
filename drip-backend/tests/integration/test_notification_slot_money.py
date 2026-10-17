"""Stored PKR fractions survive notifications; slot responses match wallet debits."""

from decimal import Decimal
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import func, select
from test_marketplace_regressions import guest_payload
from test_marketplace_regressions import market as marketplace_fixture
from test_resource_ownership import headers

from app.core.exceptions import ExternalServiceError
from app.integrations.resend_client import ResendClient
from app.models.admin import SystemSetting
from app.models.notification import EmailLog, Notification
from app.models.order import Order
from app.models.seller import SellerWallet
from app.models.wallet import Payout, PayoutStatus, WalletTransaction
from app.schemas.notification import UpdatePreferencesRequest
from app.services.notification_service import NotificationService
from app.services.order_service import OrderService

pytestmark = pytest.mark.integration
market = marketplace_fixture


@pytest.mark.parametrize("guest", [False, True])
@pytest.mark.parametrize("retry", [False, True])
async def test_order_money_survives_rendering_and_retries(guest, retry, db, market, monkeypatch):
    market.product.sale_price = Decimal("1000.25")
    await db.commit()
    created = await OrderService(db).create_guest_order(guest_payload(market))
    order = await db.get(Order, created.order_id)
    # Historical stored money may be fractional even though shipping settings are whole PKR.
    order.shipping_fee = Decimal("200.35")
    order.total = Decimal("2200.85")
    if not guest:
        order.user_id = market.buyer.id
        order.guest_email = None
    await db.commit()
    provider = AsyncMock(
        side_effect=[RuntimeError("temporary"), "receipt"] if retry else ["receipt"]
    )
    monkeypatch.setattr(ResendClient, "send", provider)
    service = NotificationService(db)
    if retry:
        with pytest.raises(ExternalServiceError):
            await service.notify_order_placed(order.id)
        log = await db.scalar(select(EmailLog))
        assert log.status == "failed" and log.attempts == 1
    await service.notify_order_placed(order.id)
    await service.notify_order_placed(order.id)
    assert provider.await_count == (2 if retry else 1)
    html = provider.await_args.kwargs["html"]
    assert "PKR 1,000.25 × 2" in html
    assert "PKR 2,000.50" in html
    assert "Shipping fee:</strong> PKR 200.35" in html
    assert "Total:</strong> PKR 2,200.85" in html
    assert ("guest_token=" in html) is guest
    notifications = (await db.scalars(select(Notification))).all()
    assert len(notifications) == (0 if guest else 1)
    if not guest:
        assert notifications[0].user_id == market.buyer.id
        assert notifications[0].body == "Your order of PKR 2,200.85 has been received."
    assert await db.scalar(select(func.count(EmailLog.id))) == 1
    log = await db.scalar(select(EmailLog))
    assert log.status == "sent" and log.attempts == (2 if retry else 1)
    await db.refresh(order)
    assert order.total == Decimal("2200.85") and order.shipping_fee == Decimal("200.35")


@pytest.mark.parametrize("status", ["approved", "completed"])
@pytest.mark.parametrize("amount", ["5000.01", "5000.75"])
async def test_payout_notification_keeps_paisa_without_repeating_or_charging(
    status, amount, db, market
):
    payout = Payout(
        seller_id=market.seller.id,
        amount=Decimal(amount),
        payment_method="bank_transfer",
        payment_detail="Test account",
        status=PayoutStatus(status),
    )
    db.add(payout)
    await db.commit()
    service = NotificationService(db)
    await service.notify_payout(payout.id, status)
    await service.notify_payout(payout.id, status)
    rows = (await db.scalars(select(Notification))).all()
    assert len(rows) == 1 and rows[0].user_id == market.seller_user.id
    assert f"PKR {Decimal(amount):,.2f}" in rows[0].body
    await db.refresh(payout)
    assert payout.amount == Decimal(amount)
    assert await db.scalar(select(func.count(WalletTransaction.id))) == 0


async def test_payout_money_notice_respects_opt_out(db, market):
    service = NotificationService(db)
    await service.update_preferences(
        market.seller_user.id, UpdatePreferencesRequest(payout_notifications=False)
    )
    payout = Payout(
        seller_id=market.seller.id,
        amount=Decimal("5000.75"),
        payment_method="bank_transfer",
        payment_detail="Test account",
        status=PayoutStatus.approved,
    )
    db.add(payout)
    await db.commit()
    await service.notify_payout(payout.id, "approved")
    assert await db.scalar(select(func.count(Notification.id))) == 0


@pytest.mark.parametrize("price", [0, 87])
async def test_slot_quote_and_purchase_match_recorded_wallet_amount(price, db, market, client):
    db.add_all(
        [
            SystemSetting(key="extra_slot_price", value=str(price)),
            SystemSetting(key="registration_fee", value="6000"),
        ]
    )
    wallet = await db.scalar(select(SellerWallet).where(SellerWallet.seller_id == market.seller.id))
    wallet.available_balance = Decimal("500.75")
    await db.commit()
    quote = await client.get("/api/v1/seller/register/slot-price?extra_slots=3")
    assert quote.status_code == 200, quote.text
    assert quote.json() == {
        "registration_fee": "6000.00",
        "base_slots": 50,
        "extra_slots": 3,
        "extra_slot_price": f"{price:.2f}",
        "extra_cost": f"{price * 3:.2f}",
        "total_cost": f"{6000 + price * 3:.2f}",
        "total_slots": 53,
    }
    response = await client.post(
        "/api/v1/seller/slots/purchase",
        headers=headers(market.seller_user),
        json={"quantity": 3, "payment_method": "wallet"},
    )
    assert response.status_code == 200, response.text
    assert response.json()["amount_charged"] == f"{price * 3:.2f}"
    await db.refresh(market.seller)
    await db.refresh(wallet)
    assert wallet.available_balance == Decimal("500.75") - price * 3
    assert market.seller.total_slots == 53
    transaction = await db.scalar(select(WalletTransaction))
    assert transaction.amount == Decimal(price * 3)
    assert transaction.balance_after == wallet.available_balance


async def test_insufficient_slot_balance_reports_paisa_without_mutation(db, market, client):
    db.add(SystemSetting(key="extra_slot_price", value="87"))
    wallet = await db.scalar(select(SellerWallet).where(SellerWallet.seller_id == market.seller.id))
    wallet.available_balance = Decimal("260.99")
    await db.commit()
    response = await client.post(
        "/api/v1/seller/slots/purchase",
        headers=headers(market.seller_user),
        json={"quantity": 3, "payment_method": "wallet"},
    )
    assert response.status_code == 422, response.text
    assert "Need PKR 261.00, have PKR 260.99" in response.text
    await db.refresh(market.seller)
    await db.refresh(wallet)
    assert wallet.available_balance == Decimal("260.99") and market.seller.total_slots == 50
    assert await db.scalar(select(func.count(WalletTransaction.id))) == 0
