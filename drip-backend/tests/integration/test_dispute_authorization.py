"""Dispute-message ownership checks against the real API and PostgreSQL."""

from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy import func, select
from test_marketplace_regressions import guest_payload
from test_marketplace_regressions import market as marketplace_fixture

from app.core.exceptions import NotFoundError
from app.core.security import create_access_token
from app.models.order import Order, OrderItem, OrderStatus, SellerOrder, SellerOrderStatus
from app.models.return_ import Dispute, DisputeMessage, DisputeStatus, Return
from app.models.user import User, UserRole
from app.schemas.return_ import (
    AddDisputeMessageRequest,
    AdminReturnActionRequest,
    CreateReturnRequest,
    OpenDisputeRequest,
)
from app.services.order_service import OrderService
from app.services.return_service import ReturnService

pytestmark = [pytest.mark.integration, pytest.mark.security]
market = marketplace_fixture


def auth_headers(account):
    token, _ = create_access_token(
        subject=str(account.id),
        role=account.role.value,
        extra_claims={"ver": account.auth_version},
    )
    return {"Authorization": "Bearer " + token}


@pytest.fixture
async def dispute_case(db, market):
    created = await OrderService(db).create_guest_order(guest_payload(market))
    order = await db.get(Order, created.order_id)
    order.user_id, order.status = market.buyer.id, OrderStatus.delivered
    seller_order = await db.scalar(select(SellerOrder).where(SellerOrder.order_id == order.id))
    seller_order.status = SellerOrderStatus.delivered
    seller_order.delivered_at = datetime.now(UTC)
    await db.commit()
    item = await db.scalar(select(OrderItem).where(OrderItem.order_id == order.id))
    service = ReturnService(db)
    returned = await service.request_return(
        market.buyer.id,
        CreateReturnRequest(
            seller_order_id=seller_order.id,
            reason="Product does not fit",
            items=[{"order_item_id": item.id, "quantity": 1}],
        ),
    )
    await service.reject_return(
        returned.id, market.admin.id, AdminReturnActionRequest(admin_note="Needs more evidence")
    )
    opened = await service.open_dispute(
        returned.id, market.buyer.id, OpenDisputeRequest(message="Please reconsider this return")
    )
    dispute = await db.get(Dispute, opened.id)
    return SimpleNamespace(
        return_id=returned.id,
        dispute=dispute,
        url=f"/api/v1/returns/{returned.id}/dispute/messages",
    )


async def message_count(db, dispute_case):
    return await db.scalar(
        select(func.count(DisputeMessage.id)).where(
            DisputeMessage.dispute_id == dispute_case.dispute.id
        )
    )


@pytest.mark.parametrize("status", [DisputeStatus.open, DisputeStatus.under_review])
async def test_owner_can_reply_and_cannot_spoof_sender(client, db, market, dispute_case, status):
    dispute_case.dispute.status = status
    await db.commit()
    response = await client.post(
        dispute_case.url,
        headers=auth_headers(market.buyer),
        json={"body": "More evidence from the owner", "sender_id": str(market.admin.id)},
    )
    assert response.status_code == 201, response.text
    assert response.json()["sender_id"] == str(market.buyer.id)
    assert response.json()["body"] == "More evidence from the owner"
    assert await message_count(db, dispute_case) == 2
    message = await db.scalar(
        select(DisputeMessage).where(DisputeMessage.body == "More evidence from the owner")
    )
    assert message.sender_id == market.buyer.id


@pytest.mark.parametrize("actor", ["other_customer", "other_seller", "assigned_seller", "admin"])
@pytest.mark.parametrize("status", [DisputeStatus.open, DisputeStatus.closed])
async def test_non_owner_cannot_reply_or_probe_state(
    client, db, market, dispute_case, actor, status
):
    if actor in ("other_customer", "other_seller"):
        account = User(
            email=f"{actor}@example.test",
            password_hash="test-only",
            role=UserRole.customer if actor == "other_customer" else UserRole.seller,
            has_verified_email=True,
        )
        db.add(account)
    else:
        account = market.seller_user if actor == "assigned_seller" else market.admin
    dispute_case.dispute.status = status
    await db.commit()

    for return_id in (dispute_case.return_id, uuid4()):
        response = await client.post(
            f"/api/v1/returns/{return_id}/dispute/messages",
            headers=auth_headers(account),
            json={"body": "Unauthorized message", "sender_id": str(market.buyer.id)},
        )
        assert response.status_code == 404, response.text
        assert response.json()["error"]["code"] == "NOT_FOUND"
        assert response.json()["error"]["message"] == "Return not found."
    assert await message_count(db, dispute_case) == 1
    assert dispute_case.dispute.status == status


@pytest.mark.parametrize(
    "status",
    [DisputeStatus.resolved_customer, DisputeStatus.resolved_seller, DisputeStatus.closed],
)
async def test_owner_cannot_reply_to_terminal_dispute(client, db, market, dispute_case, status):
    dispute_case.dispute.status = status
    await db.commit()
    response = await client.post(
        dispute_case.url,
        headers=auth_headers(market.buyer),
        json={"body": "Too late"},
    )
    assert response.status_code == 422, response.text
    assert response.json()["error"]["code"] == "BUSINESS_RULE_VIOLATION"
    assert await message_count(db, dispute_case) == 1


async def test_reply_requires_authentication(client, db, dispute_case):
    response = await client.post(dispute_case.url, json={"body": "Anonymous message"})
    assert response.status_code == 401, response.text
    assert await message_count(db, dispute_case) == 1


async def test_missing_return_is_not_found(client, db, market, dispute_case):
    response = await client.post(
        f"/api/v1/returns/{uuid4()}/dispute/messages",
        headers=auth_headers(market.buyer),
        json={"body": "Unknown return"},
    )
    assert response.status_code == 404, response.text
    assert response.json()["error"]["message"] == "Return not found."
    assert await message_count(db, dispute_case) == 1


async def test_owned_return_without_dispute_is_not_found(client, db, market, dispute_case):
    original = await db.get(Return, dispute_case.return_id)
    returned = Return(
        order_id=original.order_id,
        seller_order_id=original.seller_order_id,
        user_id=market.buyer.id,
        reason="A separate return without a dispute",
    )
    db.add(returned)
    await db.commit()
    response = await client.post(
        f"/api/v1/returns/{returned.id}/dispute/messages",
        headers=auth_headers(market.buyer),
        json={"body": "No dispute exists"},
    )
    assert response.status_code == 404, response.text
    assert response.json()["error"]["message"] == "Dispute not found."
    assert await message_count(db, dispute_case) == 1


async def test_service_also_enforces_ownership(db, market, dispute_case):
    with pytest.raises(NotFoundError, match="Return not found"):
        await ReturnService(db).add_message(
            dispute_case.return_id,
            market.seller_user.id,
            AddDisputeMessageRequest(body="Cannot bypass the route"),
        )
    assert await message_count(db, dispute_case) == 1


async def test_admin_review_and_resolution_remain_available(client, db, market, dispute_case):
    response = await client.get("/api/v1/admin/disputes", headers=auth_headers(market.admin))
    assert response.status_code == 200, response.text
    assert response.json()["data"][0]["id"] == str(dispute_case.dispute.id)
    assert len(response.json()["data"][0]["messages"]) == 1
    response = await client.post(
        f"/api/v1/admin/disputes/{dispute_case.dispute.id}/resolve",
        headers=auth_headers(market.admin),
        json={
            "in_favor_of": "customer",
            "resolution_note": "Reviewed the evidence and approved the customer claim",
        },
    )
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "resolved_customer"
    assert await message_count(db, dispute_case) == 1
