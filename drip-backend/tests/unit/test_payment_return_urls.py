"""Payment return URLs carry an order reference, never guest credentials."""

from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
from uuid import UUID

import pytest

from app.models.order import OrderStatus, PaymentMethod
from app.models.payment import PaymentStatus
from app.services import payment_service as payments


@pytest.mark.asyncio
@pytest.mark.parametrize("account", [False, True])
async def test_initiation_uses_order_specific_return_urls(monkeypatch, account):
    order_id = UUID("11111111-1111-4111-8111-111111111111")
    payment_id = UUID("22222222-2222-4222-8222-222222222222")
    order = SimpleNamespace(
        id=order_id,
        payment_method=PaymentMethod.payfast,
        status=OrderStatus.pending_payment,
        total=Decimal("1250.00"),
        guest_email="guest@example.test",
        guest_phone="03001234567",
        order_number="WHZ-fixture",
        created_at=datetime(2026, 10, 24, tzinfo=UTC),
    )
    payment = SimpleNamespace(
        id=payment_id,
        status=PaymentStatus.pending,
        amount=order.total,
        method="payfast",
        gateway_payload=None,
    )
    order.address = SimpleNamespace(phone="03007654321")
    user_id = UUID("44444444-4444-4444-8444-444444444444") if account else None
    db = SimpleNamespace(
        commit=AsyncMock(),
        add=Mock(),
        refresh=AsyncMock(),
        get=AsyncMock(return_value=SimpleNamespace(email="buyer@example.test", phone=None)),
    )
    service = payments.PaymentService(db)
    service.payment_repo = SimpleNamespace(get_by_order_id=AsyncMock(return_value=payment))
    authorized = AsyncMock(return_value=order)
    monkeypatch.setattr(payments, "authorized_order", authorized)
    monkeypatch.setattr(payments.settings, "FRONTEND_URL", "https://shop.example.test")
    monkeypatch.setattr(payments.settings, "API_BASE_URL", "https://api.example.test")
    provider = SimpleNamespace(
        get_checkout_token=AsyncMock(return_value="one-time-fixture"),
        build_checkout_payload=Mock(return_value={"TOKEN": "one-time-fixture"}),
        base_url="https://provider.example.test/checkout",
    )
    monkeypatch.setattr(payments, "_build_payfast", lambda: provider)
    result = await service.initiate(
        order_id, user_id=user_id, guest_token=None if account else "private-guest-code"
    )
    args = provider.build_checkout_payload.call_args.kwargs
    assert args["success_url"] == f"https://shop.example.test/order/success/{order_id}"
    assert args["failure_url"] == f"https://shop.example.test/payments/{order_id}?payment=failed"
    assert args["checkout_url"] == "https://api.example.test/api/v1/payments/callback/payfast"
    assert "private-guest-code" not in str(args)
    assert "one-time-fixture" not in str(payment.gateway_payload)
    assert args["customer_mobile"] == ("03007654321" if account else "03001234567")
    authorized.assert_awaited_with(
        db, order_id, user_id, None if account else "private-guest-code", lock=True
    )
    assert authorized.await_count == 2
    assert db.commit.await_count == 2
    assert args["basket_id"] == str(result.attempt_id)
    assert result.attempt_id != order_id
