"""Attempt isolation and fail-closed retries with mocked persistence/provider boundaries."""

from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from app.core.exceptions import BusinessRuleError, ExternalServiceError
from app.integrations.payfast import PayFastProtocolError
from app.models.order import OrderStatus, PaymentMethod
from app.models.payment import PaymentStatus
from app.repositories import order_repo
from app.schemas.payment import RetryPaymentRequest
from app.services import payment_service as module


@pytest.fixture
def rig(monkeypatch):
    order = SimpleNamespace(
        id=uuid4(),
        status=OrderStatus.pending_payment,
        payment_method=PaymentMethod.payfast,
        total=Decimal("1250.00"),
        guest_email="guest@example.test",
        guest_phone="03001234567",
        order_number="WHZ-test",
        created_at=datetime.now(UTC),
    )
    payment = SimpleNamespace(
        id=uuid4(),
        order_id=order.id,
        status=PaymentStatus.pending,
        method="payfast",
        amount=order.total,
        currency="PKR",
        gateway_payload=None,
        gateway_reference=None,
        failure_reason=None,
        paid_at=None,
    )
    records = {}

    def add(record):
        if record.id:
            records[record.id] = record

    async def get(model, key):
        return records.get(key)

    db = SimpleNamespace(
        add=Mock(side_effect=add),
        get=AsyncMock(side_effect=get),
        commit=AsyncMock(),
        flush=AsyncMock(),
        refresh=AsyncMock(),
        scalar=AsyncMock(return_value=payment),
    )
    service = module.PaymentService(db)
    service.payment_repo = SimpleNamespace(
        get_by_order_id=AsyncMock(return_value=payment),
        get_by_id=AsyncMock(return_value=payment),
        get_by_gateway_reference=AsyncMock(return_value=None),
    )
    repo = SimpleNamespace(get_by_id=AsyncMock(return_value=order), update_status=AsyncMock())
    monkeypatch.setattr(order_repo, "OrderRepository", lambda _db: repo)
    monkeypatch.setattr(module, "authorized_order", AsyncMock(return_value=order))
    monkeypatch.setattr(module, "queue_notification", AsyncMock())
    provider = SimpleNamespace(
        get_checkout_token=AsyncMock(return_value="private-token"),
        build_checkout_payload=Mock(return_value={"TOKEN": "private-token"}),
        base_url="https://provider.example.test/checkout",
        check_status=AsyncMock(),
        parse_callback=Mock(),
    )
    monkeypatch.setattr(module, "_build_payfast", lambda: provider)
    return SimpleNamespace(
        order=order, payment=payment, records=records, db=db, service=service, provider=provider
    )


async def start(rig):
    return await rig.service.initiate(
        rig.order.id, guest_token="private-guest", customer_ip="192.0.2.1"
    )


def evidence(rig, attempt, status="FAILED", transaction="txn-1"):
    return {
        "basket_id": str(attempt),
        "transaction_id": transaction,
        "status": status,
        "amount": "1250.00",
        "currency": "PKR",
    }


async def fail(rig, attempt):
    rig.provider.check_status.return_value = evidence(rig, attempt)
    await rig.service.reconcile_payfast(rig.order.id)


@pytest.mark.asyncio
async def test_claim_precedes_provider_and_repeated_initiation_is_blocked(rig):
    async def token(**kwargs):
        assert rig.db.commit.await_count == 1
        assert kwargs["basket_id"] in {str(key) for key in rig.records}
        return "private-token"

    rig.provider.get_checkout_token.side_effect = token
    result = await start(rig)
    assert result.attempt_id != rig.order.id
    assert rig.records[result.attempt_id].raw_payload["state"] == "ready"
    assert "private-token" not in str(rig.records[result.attempt_id].raw_payload)
    with pytest.raises(BusinessRuleError, match="reconciliation"):
        await start(rig)
    assert rig.provider.get_checkout_token.await_count == 1


@pytest.mark.asyncio
async def test_lost_token_response_keeps_durable_claim(rig):
    rig.provider.get_checkout_token.side_effect = PayFastProtocolError("unknown")
    with pytest.raises(ExternalServiceError):
        await start(rig)
    assert rig.db.commit.await_count == 1
    assert next(iter(rig.records.values())).raw_payload["state"] == "starting"
    with pytest.raises(BusinessRuleError):
        await start(rig)
    assert rig.provider.get_checkout_token.await_count == 1


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "status",
    [
        PaymentStatus.pending,
        PaymentStatus.processing,
        PaymentStatus.completed,
        PaymentStatus.refunded,
    ],
)
async def test_unresolved_or_paid_retries_never_contact_provider(rig, status):
    rig.payment.status = status
    with pytest.raises(BusinessRuleError):
        await rig.service.retry(
            rig.order.id, None, RetryPaymentRequest(payment_method="payfast"), "guest"
        )
    rig.provider.get_checkout_token.assert_not_awaited()
    rig.provider.check_status.assert_not_awaited()


@pytest.mark.asyncio
async def test_legacy_or_unverified_failed_payment_cannot_retry_or_switch_to_cod(rig):
    rig.payment.status = PaymentStatus.failed
    for method in ["payfast", "cod"]:
        with pytest.raises(BusinessRuleError):
            await rig.service.retry(
                rig.order.id, None, RetryPaymentRequest(payment_method=method), "guest"
            )
    rig.provider.get_checkout_token.assert_not_awaited()


@pytest.mark.asyncio
async def test_retry_requires_fresh_terminal_evidence_and_new_attempt(rig):
    first = await start(rig)
    await fail(rig, first.attempt_id)
    assert rig.records[first.attempt_id].is_verified
    second = await rig.service.retry(
        rig.order.id, None, RetryPaymentRequest(payment_method="payfast"), "guest", "192.0.2.1"
    )
    assert second.attempt_id != first.attempt_id
    assert rig.provider.check_status.await_count == 2
    assert rig.records[first.attempt_id].raw_payload["state"] == "failed"
    assert rig.records[second.attempt_id].raw_payload["state"] == "ready"
    with pytest.raises(BusinessRuleError):
        await rig.service.retry(
            rig.order.id, None, RetryPaymentRequest(payment_method="payfast"), "guest"
        )
    assert rig.provider.get_checkout_token.await_count == 2


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "change",
    [{"status": "PENDING"}, {"amount": "999"}, {"transaction_id": "other"}, {"basket_id": "other"}],
)
async def test_changed_or_mismatched_retry_evidence_does_not_start_again(rig, change):
    first = await start(rig)
    await fail(rig, first.attempt_id)
    rig.provider.check_status.return_value = {**evidence(rig, first.attempt_id), **change}
    with pytest.raises(BusinessRuleError):
        await rig.service.retry(
            rig.order.id, None, RetryPaymentRequest(payment_method="payfast"), "guest"
        )
    assert rig.provider.get_checkout_token.await_count == 1


@pytest.mark.asyncio
async def test_fresh_success_is_saved_instead_of_retry(rig):
    first = await start(rig)
    await fail(rig, first.attempt_id)
    rig.provider.check_status.return_value = evidence(rig, first.attempt_id, "COMPLETED")
    with pytest.raises(BusinessRuleError):
        await rig.service.retry(
            rig.order.id, None, RetryPaymentRequest(payment_method="payfast"), "guest"
        )
    assert rig.payment.status == PaymentStatus.completed
    assert rig.provider.get_checkout_token.await_count == 1


def callback(rig, attempt, status="failed"):
    rig.provider.parse_callback.return_value = {
        "order_id": str(attempt),
        "amount": Decimal("1250"),
        "currency": "PKR",
        "txn_id": "txn-1",
        "status": status,
        "raw": {"fixture": True},
    }


@pytest.mark.asyncio
async def test_failed_callback_cannot_bypass_provider_check(rig):
    first = await start(rig)
    callback(rig, first.attempt_id)
    rig.provider.check_status.return_value = evidence(rig, first.attempt_id, "PENDING")
    with pytest.raises(BusinessRuleError):
        await rig.service.handle_payfast_callback({})
    assert rig.payment.status == PaymentStatus.pending
    assert not rig.records[first.attempt_id].is_verified


@pytest.mark.asyncio
async def test_old_callback_never_changes_new_attempt(rig):
    first = await start(rig)
    await fail(rig, first.attempt_id)
    second = await rig.service.retry(
        rig.order.id, None, RetryPaymentRequest(payment_method="payfast"), "guest", "192.0.2.1"
    )
    callback(rig, first.attempt_id, "completed")
    before = rig.provider.check_status.await_count
    with pytest.raises(BusinessRuleError, match="Stale"):
        await rig.service.handle_payfast_callback({})
    assert rig.provider.check_status.await_count == before
    assert rig.payment.status == PaymentStatus.pending
    assert rig.payment.gateway_payload["active_attempt_id"] == str(second.attempt_id)


@pytest.mark.asyncio
async def test_cancellation_while_token_is_issued_prevents_handoff(rig):
    async def token(**kwargs):
        rig.order.status = OrderStatus.cancelled
        return "private-token"

    rig.provider.get_checkout_token.side_effect = token
    with pytest.raises(BusinessRuleError, match="changed"):
        await start(rig)


@pytest.mark.asyncio
async def test_conflicting_provider_statuses_never_authorize_retry(rig):
    first = await start(rig)
    await fail(rig, first.attempt_id)
    rig.provider.check_status.return_value = {
        **evidence(rig, first.attempt_id),
        "status_code": "PAID",
    }
    with pytest.raises(BusinessRuleError):
        await rig.service.retry(
            rig.order.id, None, RetryPaymentRequest(payment_method="payfast"), "guest"
        )
    assert rig.provider.get_checkout_token.await_count == 1


@pytest.mark.asyncio
async def test_failure_cannot_regress_a_completed_attempt(rig):
    first = await start(rig)
    rig.provider.check_status.return_value = evidence(rig, first.attempt_id, "COMPLETED")
    await rig.service.reconcile_payfast(rig.order.id)
    await fail(rig, first.attempt_id)
    assert rig.payment.status == PaymentStatus.completed
    assert rig.records[first.attempt_id].raw_payload["state"] == "completed"


@pytest.mark.asyncio
async def test_callback_refreshes_prelock_cached_payment(rig):
    first = await start(rig)
    await fail(rig, first.attempt_id)
    old_payload = rig.payment.gateway_payload
    second = await rig.service.retry(
        rig.order.id, None, RetryPaymentRequest(payment_method="payfast"), "guest", "192.0.2.1"
    )
    current_payload = rig.payment.gateway_payload
    rig.payment.gateway_payload = old_payload

    async def refresh(value):
        if value is rig.payment:
            value.gateway_payload = current_payload

    rig.db.refresh.side_effect = refresh
    callback(rig, first.attempt_id)
    with pytest.raises(BusinessRuleError, match="Stale"):
        await rig.service.handle_payfast_callback({})
    assert rig.payment.gateway_payload["active_attempt_id"] == str(second.attempt_id)
