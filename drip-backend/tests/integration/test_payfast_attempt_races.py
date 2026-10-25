"""Real committed sessions in a disposable PostgreSQL schema; provider transport is mocked."""

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
import pytest_asyncio
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker
from test_payment_api import checkout as checkout_fixture
from test_payment_api import guest_order as guest_order_fixture
from test_payment_api import market as market_fixture
from test_payment_api import offline_boundaries as offline_fixture

from app.core.exceptions import BusinessRuleError
from app.models.order import OrderStatus, PaymentMethod
from app.models.payment import PaymentCallback
from app.schemas.payment import RetryPaymentRequest
from app.services import payment_service as module

pytestmark = pytest.mark.integration
checkout = checkout_fixture
guest_order = guest_order_fixture
market = market_fixture
offline_boundaries = offline_fixture


@pytest_asyncio.fixture
async def db(test_engine):
    # Unlike HTTP fixtures, these commits must be visible to the competing connection.
    async with async_sessionmaker(test_engine, expire_on_commit=False)() as session:
        yield session


@pytest.mark.parametrize("retry", [False, True])
async def test_two_sessions_cannot_issue_two_active_attempts(
    test_engine, db, checkout, monkeypatch, retry
):
    checkout.order.status = OrderStatus.pending_payment
    checkout.order.payment_method = PaymentMethod.payfast
    checkout.payment.method = "payfast"
    await db.commit()
    provider = SimpleNamespace(
        base_url="https://provider.example.test/checkout",
        get_checkout_token=AsyncMock(return_value="fixture-token"),
        build_checkout_payload=Mock(return_value={"TOKEN": "fixture-token"}),
        check_status=AsyncMock(),
    )
    monkeypatch.setattr(module, "_build_payfast", lambda: provider)
    service = module.PaymentService(db)
    if retry:
        initial = await service.initiate(
            checkout.order.id, guest_token=checkout.token, customer_ip="192.0.2.1"
        )
        provider.check_status.return_value = {
            "basket_id": str(initial.attempt_id),
            "transaction_id": "failed-txn",
            "status": "FAILED",
            "amount": str(checkout.payment.amount),
            "currency": "PKR",
        }
        await service.reconcile_payfast(checkout.order.id)
    entered, release = asyncio.Event(), asyncio.Event()

    async def token(**kwargs):
        entered.set()
        await asyncio.wait_for(release.wait(), timeout=10)
        return "fixture-token"

    provider.get_checkout_token.side_effect = token
    factory = async_sessionmaker(test_engine, expire_on_commit=False)

    async def attempt():
        async with factory() as session:
            current = module.PaymentService(session)
            if retry:
                return await current.retry(
                    checkout.order.id,
                    None,
                    RetryPaymentRequest(payment_method="payfast"),
                    checkout.token,
                    "192.0.2.1",
                )
            return await current.initiate(
                checkout.order.id, guest_token=checkout.token, customer_ip="192.0.2.1"
            )

    first = asyncio.create_task(attempt())
    try:
        await asyncio.wait_for(entered.wait(), timeout=10)
        with pytest.raises(BusinessRuleError):
            await asyncio.wait_for(attempt(), timeout=5)
    finally:
        release.set()
        await asyncio.wait_for(first, timeout=10)
    expected = 2 if retry else 1
    assert provider.get_checkout_token.await_count == expected
    assert (
        await db.scalar(
            select(func.count(PaymentCallback.id)).where(
                PaymentCallback.payment_id == checkout.payment.id,
                PaymentCallback.gateway == "payfast_attempt",
            )
        )
        == expected
    )
