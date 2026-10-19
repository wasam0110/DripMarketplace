"""Canonical origins reach persisted notification and payment flows, providers mocked."""

from html import unescape
from unittest.mock import AsyncMock
from urllib.parse import parse_qs, urlsplit

import pytest
from sqlalchemy import func, select
from test_marketplace_regressions import guest_payload
from test_marketplace_regressions import market as marketplace_fixture

from app.core.config import settings
from app.integrations.payfast import PayFastClient
from app.integrations.resend_client import ResendClient
from app.models.notification import EmailLog
from app.models.order import Order, OrderStatus, PaymentMethod
from app.models.payment import Payment, PaymentStatus
from app.services import payment_service
from app.services.notification_service import NotificationService
from app.services.order_access import guest_token_matches
from app.services.order_service import OrderService
from app.services.payment_service import PaymentService

pytestmark = pytest.mark.integration
market = marketplace_fixture


@pytest.mark.parametrize("guest", [False, True])
@pytest.mark.parametrize("event", ["placed", "shipped"])
async def test_order_links_keep_canonical_origin_and_scoped_capability(
    guest,
    event,
    db,
    market,
    monkeypatch,
):
    monkeypatch.setattr(settings, "FRONTEND_URL", "https://shop.example.test/")
    monkeypatch.setattr(settings, "ALLOWED_ORIGINS", ["https://admin.example.test"])
    created = await OrderService(db).create_guest_order(guest_payload(market))
    order = await db.get(Order, created.order_id)
    if not guest:
        order.user_id, order.guest_email = market.buyer.id, None
        await db.commit()
    sender = AsyncMock(return_value="test-receipt")
    monkeypatch.setattr(ResendClient, "send", sender)
    service = NotificationService(db)
    for _ in range(2):
        if event == "placed":
            await service.notify_order_placed(order.id)
        else:
            await service.notify_order_status(order.id, event)
    assert sender.await_count == 1
    html = sender.await_args.kwargs["html"]
    link = unescape(html.split('href="', 1)[1].split('"', 1)[0])
    parsed = urlsplit(link)
    assert (parsed.scheme, parsed.netloc, parsed.path) == (
        "https",
        "shop.example.test",
        f"/orders/{order.id}",
    )
    query = parse_qs(parsed.query)
    if guest:
        assert set(query) == {"guest_token"}
        assert guest_token_matches(query["guest_token"][0], order.id)
        assert not guest_token_matches(query["guest_token"][0], market.product.id)
    else:
        assert query == {}
    assert await db.scalar(select(func.count(EmailLog.id))) == 1


@pytest.mark.parametrize("trailing_slash", ["", "/"])
async def test_payfast_form_uses_canonical_separate_origins(
    trailing_slash,
    db,
    market,
    monkeypatch,
):
    monkeypatch.setattr(settings, "FRONTEND_URL", "https://shop.example.test" + trailing_slash)
    monkeypatch.setattr(settings, "API_BASE_URL", "https://api.example.test" + trailing_slash)
    monkeypatch.setattr(settings, "ALLOWED_ORIGINS", [])
    created = await OrderService(db).create_guest_order(guest_payload(market))
    order = await db.get(Order, created.order_id)
    order.payment_method, order.status = PaymentMethod.payfast, OrderStatus.pending_payment
    await db.commit()
    gateway = PayFastClient("test-merchant", "test-secret")
    token = AsyncMock(return_value="synthetic-token")
    monkeypatch.setattr(gateway, "get_checkout_token", token)
    monkeypatch.setattr(payment_service, "_build_payfast", lambda: gateway)
    initialized = await PaymentService(db).initiate(order.id, guest_token=created.guest_token)
    form = initialized.payfast_payload
    assert form["SUCCESS_URL"] == f"https://shop.example.test/order/success/{order.id}"
    assert form["FAILURE_URL"] == "https://shop.example.test/checkout?payment=failed"
    assert form["CHECKOUT_URL"] == "https://api.example.test/api/v1/payments/callback/payfast"
    assert form["TXNAMT"] == f"{order.total:.2f}"
    assert form["CURRENCY_CODE"] == "PKR"
    token.assert_awaited_once_with(basket_id=str(order.id), amount=order.total)
    payment = await db.get(Payment, initialized.payment_id)
    assert payment.amount == order.total and payment.status == PaymentStatus.pending
    assert "synthetic-token" not in str(payment.gateway_payload)
