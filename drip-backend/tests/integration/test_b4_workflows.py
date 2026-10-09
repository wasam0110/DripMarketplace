"""B4 seller-return, admin-dispute, and guest-capability workflows."""

from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from sqlalchemy import func, select
from test_marketplace_regressions import (
    _fulfil_and_collect_cod,
    _request_single_item_return,
    actor_headers,
    guest_payload,
)
from test_marketplace_regressions import market as marketplace_fixture

from app.models.order import Order, OrderItem, OrderStatus, SellerOrder, SellerOrderStatus
from app.models.return_ import DisputeMessage, Return
from app.models.seller import Seller, SellerStatus
from app.models.user import User, UserRole
from app.schemas.return_ import AdminReturnActionRequest, OpenDisputeRequest
from app.services.order_access import create_guest_token
from app.services.order_service import OrderService
from app.services.return_service import ReturnService

pytestmark = [pytest.mark.integration, pytest.mark.security]
market = marketplace_fixture


async def _competitor_seller(db):
    account = User(
        email=f"competitor-{uuid4()}@example.test",
        password_hash="test-only",
        role=UserRole.seller,
        has_verified_email=True,
    )
    db.add(account)
    await db.flush()
    seller = Seller(
        user_id=account.id,
        brand_name=f"Competitor {uuid4()}",
        slug=f"competitor-{uuid4()}",
        status=SellerStatus.active,
        total_slots=50,
    )
    db.add(seller)
    await db.commit()
    return account, seller


async def test_seller_return_queue_detail_and_owned_lifecycle(
    client, db, market, isolated_redis
):
    order, seller_order, _, _ = await _fulfil_and_collect_cod(
        db, market, isolated_redis
    )
    returned, order_item = await _request_single_item_return(
        db, market, order, seller_order
    )
    headers = actor_headers(market.seller_user)
    other_account, _ = await _competitor_seller(db)

    queue = await client.get("/api/v1/seller/returns", headers=headers)
    assert queue.status_code == 200, queue.text
    assert queue.json()["total"] == 1
    assert queue.json()["data"][0]["id"] == str(returned.id)

    detail_url = f"/api/v1/seller/returns/{returned.id}"
    detail = await client.get(detail_url, headers=headers)
    assert detail.status_code == 200, detail.text
    body = detail.json()
    assert body["order_number"] == order.order_number
    assert body["available_actions"] == ["approve", "reject"]
    assert body["items"][0]["order_item_id"] == str(order_item.id)
    assert body["items"][0]["product_name"] == "Linen Shirt"
    assert body["items"][0]["purchased_quantity"] == 2
    assert body["items"][0]["requested_quantity"] == 1

    assert (
        await client.get(detail_url, headers=actor_headers(market.buyer))
    ).status_code == 403
    assert (
        await client.get(detail_url, headers=actor_headers(other_account))
    ).status_code == 404
    assert (
        await client.post(
            detail_url + "/reject",
            headers=actor_headers(other_account),
            json={"admin_note": "Unauthorized decision"},
        )
    ).status_code == 404

    approved = await client.post(
        detail_url + "/approve", headers=headers, json={"admin_note": "Accepted"}
    )
    assert approved.status_code == 200, approved.text
    assert (await client.get(detail_url, headers=headers)).json()[
        "available_actions"
    ] == ["mark_received"]

    received = await client.post(
        detail_url + "/received",
        headers=headers,
        json={"admin_note": "Parcel received"},
    )
    assert received.status_code == 200, received.text
    body = (await client.get(detail_url, headers=headers)).json()
    assert body["status"] == "received"
    assert body["available_actions"] == []

    # Financial mutations remain administrator-only.
    denied_refund = await client.post(
        f"/api/v1/admin/returns/{returned.id}/refund", headers=headers, json={}
    )
    assert denied_refund.status_code == 403


async def test_seller_can_reject_owned_return_and_customer_can_dispute(
    client, db, market, isolated_redis
):
    order, seller_order, _, _ = await _fulfil_and_collect_cod(
        db, market, isolated_redis
    )
    returned, _ = await _request_single_item_return(db, market, order, seller_order)
    response = await client.post(
        f"/api/v1/seller/returns/{returned.id}/reject",
        headers=actor_headers(market.seller_user),
        json={"admin_note": "Evidence does not show a product defect"},
    )
    assert response.status_code == 200, response.text
    dispute = await client.post(
        f"/api/v1/returns/{returned.id}/dispute",
        headers=actor_headers(market.buyer),
        json={"message": "Please review the photographs and reconsider the rejection"},
    )
    assert dispute.status_code == 201, dispute.text


async def test_admin_dispute_detail_reply_and_terminal_state(
    client, db, market, isolated_redis
):
    order, seller_order, _, _ = await _fulfil_and_collect_cod(
        db, market, isolated_redis
    )
    returned, _ = await _request_single_item_return(db, market, order, seller_order)
    service = ReturnService(db)
    await service.reject_return(
        returned.id,
        market.admin.id,
        AdminReturnActionRequest(admin_note="More evidence is required"),
    )
    opened = await service.open_dispute(
        returned.id,
        market.buyer.id,
        OpenDisputeRequest(message="The submitted photographs show the damaged fabric"),
    )
    url = f"/api/v1/admin/disputes/{opened.id}"
    headers = actor_headers(market.admin)

    assert (await client.get(url, headers=actor_headers(market.buyer))).status_code == 403
    assert (
        await client.get(url, headers=actor_headers(market.seller_user))
    ).status_code == 403
    assert (await client.get(f"/api/v1/admin/disputes/{uuid4()}", headers=headers)).status_code == 404

    detail = await client.get(url, headers=headers)
    assert detail.status_code == 200, detail.text
    assert detail.json()["status"] == "open"
    assert len(detail.json()["messages"]) == 1

    reply = await client.post(
        url + "/messages",
        headers=headers,
        json={"body": "The administrator is reviewing the supplied evidence"},
    )
    assert reply.status_code == 201, reply.text
    assert reply.json()["sender_id"] == str(market.admin.id)
    detail = (await client.get(url, headers=headers)).json()
    assert detail["status"] == "under_review"
    assert len(detail["messages"]) == 2

    customer_view = await client.get(
        f"/api/v1/returns/{returned.id}/dispute",
        headers=actor_headers(market.buyer),
    )
    assert customer_view.status_code == 200
    assert customer_view.json()["messages"][-1]["body"].startswith("The administrator")

    resolved = await client.post(
        url + "/resolve",
        headers=headers,
        json={
            "in_favor_of": "customer",
            "resolution_note": "The photographic evidence supports the customer's claim",
        },
    )
    assert resolved.status_code == 200, resolved.text
    count_before = await db.scalar(
        select(func.count(DisputeMessage.id)).where(
            DisputeMessage.dispute_id == opened.id
        )
    )
    terminal_reply = await client.post(
        url + "/messages", headers=headers, json={"body": "This should not be saved"}
    )
    assert terminal_reply.status_code == 422
    assert await db.scalar(
        select(func.count(DisputeMessage.id)).where(
            DisputeMessage.dispute_id == opened.id
        )
    ) == count_before


async def test_guest_capability_can_cancel_only_its_order(client, db, market):
    created = await OrderService(db).create_guest_order(guest_payload(market))
    url = f"/api/v1/orders/{created.order_id}/cancel"
    payload = {"reason": "Guest changed their mind before dispatch"}

    assert (await client.post(url, json=payload)).status_code == 401
    assert (
        await client.post(url, json=payload, headers={"X-Guest-Token": "forged"})
    ).status_code == 404
    assert (
        await client.post(
            url,
            json=payload,
            headers={"X-Guest-Token": create_guest_token(uuid4())},
        )
    ).status_code == 404
    assert (
        await client.post(url, json=payload, headers=actor_headers(market.buyer))
    ).status_code == 404

    response = await client.post(
        url, json=payload, headers={"X-Guest-Token": created.guest_token}
    )
    assert response.status_code == 200, response.text
    order = await db.get(Order, created.order_id)
    assert order.status == OrderStatus.cancelled
    await db.refresh(market.inventory)
    assert market.inventory.reserved == 0


async def test_guest_capability_can_create_and_read_only_its_return(
    client, db, market
):
    created = await OrderService(db).create_guest_order(guest_payload(market))
    order = await db.get(Order, created.order_id)
    order.status = OrderStatus.delivered
    seller_order = await db.scalar(
        select(SellerOrder).where(SellerOrder.order_id == order.id)
    )
    seller_order.status = SellerOrderStatus.delivered
    seller_order.delivered_at = datetime.now(UTC)
    order_item = await db.scalar(select(OrderItem).where(OrderItem.order_id == order.id))
    await db.commit()

    payload = {
        "seller_order_id": str(seller_order.id),
        "reason": "The guest order arrived with damaged fabric",
        "items": [
            {
                "order_item_id": str(order_item.id),
                "quantity": 1,
                "reason": "Fabric is torn",
            }
        ],
    }
    assert (await client.post("/api/v1/returns/guest", json=payload)).status_code == 401
    assert (
        await client.post(
            "/api/v1/returns/guest",
            json=payload,
            headers={"X-Guest-Token": "forged"},
        )
    ).status_code == 404
    assert (
        await client.post(
            "/api/v1/returns/guest",
            json=payload,
            headers={"X-Guest-Token": create_guest_token(uuid4())},
        )
    ).status_code == 404

    created_return = await client.post(
        "/api/v1/returns/guest",
        json=payload,
        headers={"X-Guest-Token": created.guest_token},
    )
    assert created_return.status_code == 201, created_return.text
    return_id = UUID(created_return.json()["id"])
    stored = await db.get(Return, return_id)
    assert stored.user_id is None
    detail_url = f"/api/v1/returns/guest/{return_id}"

    assert (await client.get(detail_url)).status_code == 401
    assert (
        await client.get(detail_url, headers={"X-Guest-Token": "forged"})
    ).status_code == 404
    detail = await client.get(
        detail_url, headers={"X-Guest-Token": created.guest_token}
    )
    assert detail.status_code == 200, detail.text
    assert detail.json()["id"] == str(return_id)
    assert (
        await client.get(
            f"/api/v1/returns/{return_id}", headers=actor_headers(market.buyer)
        )
    ).status_code == 404

    admin_detail = await client.get(
        f"/api/v1/admin/returns/{return_id}", headers=actor_headers(market.admin)
    )
    assert admin_detail.status_code == 200, admin_detail.text
    assert admin_detail.json()["customer"]["is_guest"] is True
    assert admin_detail.json()["customer"]["user_id"] is None
    assert admin_detail.json()["customer"]["email"] == "guest@example.com"
    assert (
        await client.get(
            f"/api/v1/seller/returns/{return_id}",
            headers=actor_headers(market.seller_user),
        )
    ).status_code == 200
