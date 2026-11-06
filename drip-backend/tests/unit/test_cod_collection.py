"""Collection validation and fail-closed eligibility without external services."""

from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace as Row
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.models.order import OrderStatus, PaymentMethod, SellerOrderStatus
from app.models.payment import PaymentStatus
from app.schemas.payment import CODCollectionRequest
from app.services.payment_service import PaymentService


@pytest.mark.parametrize("reference", ["", "  ", "ab", "a\nb", "ab\x00c", "x" * 256])
def test_bad_reference(reference):
    with pytest.raises(ValidationError):
        CODCollectionRequest(reference=reference)


def test_trimmed_reference_and_legacy_payload():
    request = CODCollectionRequest(reference="  COURIER-001  ")
    assert request.reference == "COURIER-001"
    assert request.expected_amount is None and request.expected_order_updated_at is None


@pytest.mark.parametrize(
    "values",
    [
        {"expected_amount": "0"},
        {"expected_amount": "1.001"},
        {"expected_order_updated_at": "2026-11-01T00:00:00"},
    ],
)
def test_bad_review_version(values):
    with pytest.raises(ValidationError):
        CODCollectionRequest(reference="COD-001", **values)


def eligible():
    seller = uuid4()
    payment = Row(
        method="cod",
        status=PaymentStatus.pending,
        currency="PKR",
        amount=Decimal("1200.25"),
        paid_at=None,
        gateway_reference=None,
    )
    order = Row(
        payment_method=PaymentMethod.cod,
        status=OrderStatus.delivered,
        subtotal=Decimal("1000.25"),
        discount_amount=Decimal("0"),
        shipping_fee=Decimal("200"),
        total=Decimal("1200.25"),
        items=[
            Row(
                seller_id=seller,
                subtotal=Decimal("1000.25"),
                unit_price=Decimal("1000.25"),
                quantity=1,
            )
        ],
        seller_orders=[
            Row(seller_id=seller, subtotal=Decimal("1000.25"), status=SellerOrderStatus.delivered)
        ],
    )
    return payment, order


def test_eligible_full_payment():
    assert not PaymentService._cod_collection_blockers(*eligible())


@pytest.mark.parametrize(
    "target,field,value",
    [
        ("payment", "method", "payfast"),
        ("payment", "currency", "USD"),
        ("payment", "status", PaymentStatus.refunded),
        ("payment", "amount", Decimal("1200")),
        ("payment", "paid_at", datetime.now(UTC)),
        ("payment", "gateway_reference", "OLD"),
        ("order", "payment_method", PaymentMethod.payfast),
        ("order", "status", OrderStatus.processing),
        ("order", "items", []),
        ("order", "seller_orders", []),
        ("order", "shipping_fee", Decimal("199")),
    ],
)
def test_inconsistent_collection_is_blocked(target, field, value):
    payment, order = eligible()
    setattr(payment if target == "payment" else order, field, value)
    assert PaymentService._cod_collection_blockers(payment, order)


def test_partially_cancelled_fulfilment_cannot_collect_full_amount():
    payment, order = eligible()
    order.seller_orders[0].status = SellerOrderStatus.cancelled
    assert PaymentService._cod_collection_blockers(payment, order)


def test_equal_aggregate_does_not_hide_wrong_brand_allocation():
    payment, order = eligible()
    other = uuid4()
    order.items.append(
        Row(seller_id=other, subtotal=Decimal("500"), unit_price=Decimal("500"), quantity=1)
    )
    order.subtotal += Decimal("500")
    order.total += Decimal("500")
    payment.amount = order.total
    order.seller_orders[0].subtotal = Decimal("900.25")
    order.seller_orders.append(
        Row(seller_id=other, subtotal=Decimal("600"), status=SellerOrderStatus.delivered)
    )
    assert PaymentService._cod_collection_blockers(payment, order)
