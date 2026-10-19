"""Payment HTTP regressions using native rows and real guest/account authorization.

Worker scheduling and provider transport are isolated at their external boundaries.
"""

from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import UUID, uuid4

import pytest
from sqlalchemy import func, select
from test_marketplace_regressions import guest_payload
from test_marketplace_regressions import market as marketplace_fixture
from test_resource_ownership import headers

from app.core.config import settings
from app.integrations.payfast import PayFastClient
from app.models.order import Order, OrderItem, OrderStatus, PaymentMethod, SellerOrder
from app.models.payment import Payment, PaymentCallback, PaymentStatus, Refund
from app.models.product import ProductInventory
from app.models.seller import SellerWallet
from app.models.wallet import CommissionLedger, WalletTransaction
from app.services.order_access import create_guest_token
from app.services.order_service import OrderService
from app.services.payment_service import PaymentService

pytestmark = pytest.mark.integration
market = marketplace_fixture
BASE = "/api/v1/payments"
REFUND = {
    "amount": "500.25",
    "reason": "Customer requested a partial refund",
    "idempotency_key": "payment-http-refund-001",
}


@pytest.fixture(autouse=True)
def offline_boundaries(monkeypatch):
    monkeypatch.setattr(settings, "PAYFAST_ENABLED", False)
    transport = AsyncMock(side_effect=AssertionError("Provider transport must remain offline"))
    monkeypatch.setattr(PayFastClient, "_post_form", transport)
    monkeypatch.setattr(PayFastClient, "_get", transport)
    monkeypatch.setattr(OrderService, "_enqueue_cod_timeout", AsyncMock())
    return transport


@pytest.fixture
async def guest_order(db, market):
    market.product.sale_price = Decimal("1200.25")
    await db.commit()
    created = await OrderService(db).create_guest_order(guest_payload(market))
    assert created.total == Decimal("2600.50")
    return created


@pytest.fixture
async def checkout(db, guest_order):
    initiated = await PaymentService(db).initiate(
        guest_order.order_id, guest_token=guest_order.guest_token
    )
    payment = await db.get(Payment, initiated.payment_id)
    order = await db.get(Order, guest_order.order_id)
    return SimpleNamespace(order=order, payment=payment, token=guest_order.guest_token)


@pytest.fixture
async def completed(db, checkout):
    checkout.payment.status = PaymentStatus.completed
    checkout.payment.paid_at = datetime.now(UTC)
    checkout.order.status = OrderStatus.payment_confirmed
    await db.commit()
    return checkout


def capability(checkout):
    return {"X-Guest-Token": checkout.token}


async def snapshot(db, *, include_refunds=True):
    models = (
        Order,
        OrderItem,
        SellerOrder,
        Payment,
        PaymentCallback,
        ProductInventory,
        SellerWallet,
        WalletTransaction,
        CommissionLedger,
    )
    if include_refunds:
        models += (Refund,)
    return {
        model.__tablename__: sorted(
            tuple(map(str, row))
            for row in (await db.execute(select(*model.__table__.columns))).all()
        )
        for model in models
    }


def assert_error(response, status, code, fields=()):
    assert response.status_code == status, response.text
    assert response.json()["error"]["code"] == code
    assert set(fields) <= set(response.json()["error"].get("fields", {}))


async def payment_request(client, action, order_id, auth):
    if action == "initiate":
        return await client.post(BASE + "/initiate", headers=auth, json={"order_id": str(order_id)})
    if action == "status":
        return await client.get(f"{BASE}/{order_id}/status", headers=auth)
    return await client.post(
        f"{BASE}/{order_id}/retry", headers=auth, json={"payment_method": "cod"}
    )


@pytest.mark.parametrize("action", ["initiate", "status", "retry"])
async def test_payment_requires_account_or_guest_capability(client, db, checkout, action):
    before = await snapshot(db)
    response = await payment_request(client, action, checkout.order.id, {})
    assert_error(response, 401, "UNAUTHORIZED")
    assert await snapshot(db) == before


@pytest.mark.parametrize("action", ["initiate", "status", "retry"])
@pytest.mark.parametrize("identity", ["malformed", "other_order", "unrelated_account"])
async def test_wrong_payment_identity_cannot_read_or_mutate(
    client, db, market, checkout, action, identity
):
    control = await payment_request(client, "status", checkout.order.id, capability(checkout))
    assert control.status_code == 200, control.text
    auth = (
        headers(market.buyer)
        if identity == "unrelated_account"
        else {
            "X-Guest-Token": "invalid" if identity == "malformed" else create_guest_token(uuid4())
        }
    )
    before = await snapshot(db)
    response = await payment_request(client, action, checkout.order.id, auth)
    assert_error(response, 404, "NOT_FOUND")
    assert await snapshot(db) == before


async def test_guest_cod_initiation_is_idempotent_and_status_is_exact(client, db, guest_order):
    auth = {"X-Guest-Token": guest_order.guest_token}
    assert await db.scalar(select(func.count(Payment.id))) == 0
    first = await payment_request(client, "initiate", guest_order.order_id, auth)
    repeated = await payment_request(client, "initiate", guest_order.order_id, auth)
    assert first.status_code == repeated.status_code == 200
    assert first.json() == repeated.json()
    body = first.json()
    assert body == {
        "payment_id": body["payment_id"],
        "method": "cod",
        "checkout_url": None,
        "payfast_payload": None,
        "expires_at": None,
    }
    assert await db.scalar(select(func.count(Payment.id))) == 1
    status = await payment_request(client, "status", guest_order.order_id, auth)
    assert status.status_code == 200, status.text
    assert status.json() == {
        "order_id": str(guest_order.order_id),
        "payment_id": body["payment_id"],
        "status": "pending",
        "method": "cod",
        "amount": "2600.50",
        "gateway_reference": None,
        "paid_at": None,
    }


async def test_authorized_order_without_payment_is_not_found(client, db, guest_order):
    before = await snapshot(db)
    response = await payment_request(
        client, "status", guest_order.order_id, {"X-Guest-Token": guest_order.guest_token}
    )
    assert_error(response, 404, "NOT_FOUND")
    assert await snapshot(db) == before


async def test_account_order_accepts_owner_and_rejects_old_guest_capability(
    client, db, market, checkout
):
    checkout.order.user_id = market.buyer.id
    await db.commit()
    before = await snapshot(db)
    own = await payment_request(client, "status", checkout.order.id, headers(market.buyer))
    assert own.status_code == 200, own.text
    assert own.json()["payment_id"] == str(checkout.payment.id)
    assert own.json()["amount"] == "2600.50"
    guest = await payment_request(client, "status", checkout.order.id, capability(checkout))
    assert_error(guest, 404, "NOT_FOUND")
    assert await snapshot(db) == before


@pytest.mark.parametrize("method", ["bitcoin", "jazzcash", "easypaisa", "card"])
async def test_retry_invalid_or_retired_method_is_validated_with_access(
    client, db, checkout, method
):
    control = await payment_request(client, "status", checkout.order.id, capability(checkout))
    assert control.status_code == 200, control.text
    before = await snapshot(db)
    response = await client.post(
        f"{BASE}/{checkout.order.id}/retry",
        headers=capability(checkout),
        json={"payment_method": method},
    )
    assert_error(response, 422, "VALIDATION_ERROR", ["payment_method"])
    assert await snapshot(db) == before


async def test_failed_online_payment_can_retry_as_cod(client, db, checkout, offline_boundaries):
    checkout.order.status = OrderStatus.pending_payment
    checkout.order.payment_method = PaymentMethod.payfast
    checkout.payment.method = "payfast"
    checkout.payment.status = PaymentStatus.failed
    checkout.payment.failure_reason = "Synthetic failure"
    checkout.payment.gateway_payload = {"synthetic_failed_attempt": True}
    await db.commit()
    response = await payment_request(client, "retry", checkout.order.id, capability(checkout))
    assert response.status_code == 200, response.text
    assert response.json()["payment_id"] == str(checkout.payment.id)
    assert response.json()["method"] == "cod"
    await db.refresh(checkout.order)
    await db.refresh(checkout.payment)
    assert checkout.order.status == OrderStatus.pending_cod_verification
    assert checkout.order.payment_method == PaymentMethod.cod
    assert checkout.payment.method == "cod"
    assert checkout.payment.status == PaymentStatus.pending
    assert checkout.payment.failure_reason is None
    assert checkout.payment.gateway_payload is None
    assert checkout.payment.amount == Decimal("2600.50")
    assert await db.scalar(select(func.count(Payment.id))) == 1
    offline_boundaries.assert_not_awaited()


async def test_retired_stripe_callback_returns_not_found_without_mutation(client, db, checkout):
    before = await snapshot(db)
    response = await client.post(
        BASE + "/callback/stripe",
        json={"type": "payment_intent.succeeded"},
        headers={"stripe-signature": "invalid"},
    )
    assert_error(response, 404, "NOT_FOUND")
    assert await snapshot(db) == before


@pytest.mark.parametrize(
    "actor,status,code",
    [(None, 401, "UNAUTHORIZED"), ("buyer", 403, "FORBIDDEN"), ("seller_user", 403, "FORBIDDEN")],
)
@pytest.mark.parametrize("action", ["gateway", "list", "refund"])
async def test_admin_payment_routes_require_admin(
    client, db, market, completed, actor, status, code, action
):
    auth = headers(getattr(market, actor)) if actor else {}
    before = await snapshot(db)
    if action == "gateway":
        response = await client.get(BASE + "/gateway-status", headers=auth)
    elif action == "list":
        response = await client.get(BASE, headers=auth)
    else:
        response = await client.post(
            f"{BASE}/{completed.payment.id}/refund", headers=auth, json=REFUND
        )
    assert_error(response, status, code)
    assert await snapshot(db) == before


async def test_admin_gateway_status_reports_disabled_payfast_and_active_cod(client, market):
    response = await client.get(BASE + "/gateway-status", headers=headers(market.admin))
    assert response.status_code == 200, response.text
    assert response.json() == {"payfast": "disabled_pending_verification", "cod": "active"}


@pytest.mark.parametrize(
    "filters,included",
    [({}, True), ({"status": "completed", "method": "cod"}, True), ({"status": "pending"}, False)],
)
async def test_admin_payment_listing_filters_actual_rows(
    client, market, completed, filters, included
):
    response = await client.get(BASE, headers=headers(market.admin), params=filters)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["total"] == int(included)
    assert body["page"] == 1
    assert [row["id"] for row in body["data"]] == ([str(completed.payment.id)] if included else [])
    if included:
        assert body["data"][0]["order_id"] == str(completed.order.id)
        assert body["data"][0]["amount"] == "2600.50"


@pytest.mark.parametrize(
    "query,field",
    [
        ({"status": "unknown"}, "query → status"),
        ({"method": "bitcoin"}, "query → method"),
        ({"page": 0}, "query → page"),
    ],
)
async def test_admin_payment_filter_validation_is_authenticated(
    client, db, market, completed, query, field
):
    before = await snapshot(db)
    response = await client.get(BASE, headers=headers(market.admin), params=query)
    assert_error(response, 422, "VALIDATION_ERROR", [field])
    assert await snapshot(db) == before


@pytest.mark.parametrize(
    "changes,field",
    [({"reason": "bad"}, "reason"), ({"amount": "0"}, "amount"), ({"amount": "500.001"}, "amount")],
)
async def test_refund_validation_uses_admin_and_completed_payment(
    client, db, market, completed, changes, field
):
    control = await client.get(BASE, headers=headers(market.admin))
    assert control.status_code == 200, control.text
    before = await snapshot(db)
    response = await client.post(
        f"{BASE}/{completed.payment.id}/refund",
        headers=headers(market.admin),
        json={**REFUND, **changes},
    )
    assert_error(response, 422, "VALIDATION_ERROR", [field])
    assert await snapshot(db) == before


async def test_admin_refund_request_is_pending_idempotent_and_has_no_transfer_effect(
    client, db, market, completed
):
    before = await snapshot(db, include_refunds=False)
    path = f"{BASE}/{completed.payment.id}/refund"
    first = await client.post(path, headers=headers(market.admin), json=REFUND)
    repeated = await client.post(path, headers=headers(market.admin), json=REFUND)
    assert first.status_code == repeated.status_code == 200
    assert first.json() == repeated.json()
    body = first.json()
    assert body["amount"] == "500.25"
    assert body["status"] == "pending"
    assert body["processed_at"] is None
    assert body["gateway_ref"] is None
    assert body["payment_id"] == str(completed.payment.id)
    stored = await db.get(Refund, UUID(body["refund_id"]))
    assert stored.requested_by == market.admin.id
    assert stored.processed_by is None
    assert stored.idempotency_key == REFUND["idempotency_key"]
    assert await db.scalar(select(func.count(Refund.id))) == 1
    assert await snapshot(db, include_refunds=False) == before


@pytest.mark.parametrize("case", ["over_remaining", "changed_idempotent_request"])
async def test_refund_business_rejection_has_no_extra_financial_effect(
    client, db, market, completed, case
):
    path = f"{BASE}/{completed.payment.id}/refund"
    created = await client.post(path, headers=headers(market.admin), json=REFUND)
    assert created.status_code == 200, created.text
    payload = (
        {**REFUND, "amount": "2600.50", "idempotency_key": "another-refund-key"}
        if case == "over_remaining"
        else {**REFUND, "amount": "501.25"}
    )
    before = await snapshot(db)
    response = await client.post(path, headers=headers(market.admin), json=payload)
    assert_error(response, 422, "BUSINESS_RULE_VIOLATION")
    assert await snapshot(db) == before
