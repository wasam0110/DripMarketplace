"""Regression tests for backend repair batch 3 dispute outcomes."""

from decimal import Decimal
from uuid import UUID

import pytest
from sqlalchemy import func, select
from test_marketplace_regressions import (
    _fulfil_and_collect_cod,
    _request_single_item_return,
)
from test_marketplace_regressions import market as marketplace_fixture

from app.models.payment import Refund
from app.models.return_ import Dispute, DisputeStatus, Return, ReturnStatus
from app.schemas.return_ import (
    AdminReturnActionRequest,
    OpenDisputeRequest,
    ResolveDisputeRequest,
)
from app.services.payment_service import PaymentService
from app.services.return_service import ReturnService

pytestmark = pytest.mark.integration
market = marketplace_fixture


async def _reject_and_open_dispute(db, market, order, seller_order):
    returned, _ = await _request_single_item_return(
        db,
        market,
        order,
        seller_order,
    )
    service = ReturnService(db)
    await service.reject_return(
        returned.id,
        market.admin.id,
        AdminReturnActionRequest(admin_note="Seller rejected the return"),
    )
    dispute = await service.open_dispute(
        returned.id,
        market.buyer.id,
        OpenDisputeRequest(message="The supplied evidence supports this return"),
    )
    return returned, dispute


async def test_customer_win_reopens_return_and_completes_manual_refund_journey(
    db,
    market,
    isolated_redis,
):
    order, seller_order, payment, wallet = await _fulfil_and_collect_cod(
        db,
        market,
        isolated_redis,
    )
    returned, dispute = await _reject_and_open_dispute(
        db,
        market,
        order,
        seller_order,
    )
    service = ReturnService(db)

    resolution = await service.resolve_dispute(
        dispute.id,
        market.admin.id,
        ResolveDisputeRequest(
            in_favor_of="customer",
            resolution_note="The evidence supports the customer's return claim",
        ),
    )

    stored_return = await db.get(Return, returned.id, populate_existing=True)
    assert resolution.status == DisputeStatus.resolved_customer.value
    assert stored_return.status == ReturnStatus.approved
    assert stored_return.resolved_at is None
    assert await db.scalar(select(func.count(Refund.id))) == 0
    await db.refresh(market.inventory)
    assert market.inventory.stock == 6

    detail = await service.get_admin_return(returned.id)
    assert detail.available_actions == ["mark_received"]
    assert detail.refund is None

    await service.mark_received(
        returned.id,
        market.admin.id,
        AdminReturnActionRequest(admin_note="Returned parcel received"),
    )
    request = await service.process_refund(
        returned.id,
        market.admin.id,
        AdminReturnActionRequest(admin_note="Customer-won dispute refund"),
    )
    refund_id = UUID(request["refund_id"])
    refund = await db.get(Refund, refund_id, populate_existing=True)
    stored_return = await db.get(Return, returned.id, populate_existing=True)
    assert request["status"] == "pending"
    assert refund.gateway_ref is None
    assert refund.processed_at is None
    assert stored_return.status == ReturnStatus.received
    await db.refresh(market.inventory)
    assert market.inventory.stock == 6

    await PaymentService(db).confirm_refund(
        refund_id,
        market.admin.id,
        "B3-REFUND-TRANSFER-001",
    )
    refund = await db.get(Refund, refund_id, populate_existing=True)
    stored_return = await db.get(Return, returned.id, populate_existing=True)
    await db.refresh(wallet)
    await db.refresh(market.inventory)
    assert refund.gateway_ref == "B3-REFUND-TRANSFER-001"
    assert refund.processed_at is not None
    assert stored_return.status == ReturnStatus.refunded
    assert stored_return.resolved_at is not None
    assert payment.status.value == "completed"
    assert wallet.pending_balance == Decimal("1020.00")
    assert market.inventory.stock == 7


async def test_seller_win_keeps_return_rejected_and_creates_no_refund(
    db,
    market,
    isolated_redis,
):
    order, seller_order, _, _ = await _fulfil_and_collect_cod(
        db,
        market,
        isolated_redis,
    )
    returned, dispute = await _reject_and_open_dispute(
        db,
        market,
        order,
        seller_order,
    )
    service = ReturnService(db)

    resolution = await service.resolve_dispute(
        dispute.id,
        market.admin.id,
        ResolveDisputeRequest(
            in_favor_of="seller",
            resolution_note="The seller's rejection is supported by the evidence",
        ),
    )

    stored_dispute = await db.get(Dispute, dispute.id, populate_existing=True)
    stored_return = await db.get(Return, returned.id, populate_existing=True)
    assert resolution.status == DisputeStatus.resolved_seller.value
    assert stored_dispute.status == DisputeStatus.resolved_seller
    assert stored_return.status == ReturnStatus.rejected
    assert (await service.get_admin_return(returned.id)).available_actions == []
    assert await db.scalar(select(func.count(Refund.id))) == 0
