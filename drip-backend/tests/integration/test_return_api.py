"""Return/dispute API checks against real auth and isolated PostgreSQL."""

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from httpx import ASGITransport, AsyncClient
from main import _register_exception_handlers
from sqlalchemy import select

from app.core.security import create_access_token
from app.models.order import (
    Order,
    OrderItem,
    OrderStatus,
    SellerOrder,
    SellerOrderStatus,
    StoredPaymentMethod,
)
from app.models.payment import Payment, PaymentStatus, Refund
from app.models.product import Product, ProductInventory, ProductVariant, SizeType
from app.models.return_ import Dispute, DisputeMessage, Return, ReturnItem
from app.models.seller import Seller, SellerStatus, SellerWallet
from app.models.user import User, UserRole
from app.models.wallet import (
    CommissionLedger,
    RefundAccounting,
    RefundAllocation,
    WalletTransaction,
)
from app.services.order_access import create_guest_token

pytestmark = pytest.mark.integration

REASON = "Item arrived damaged and not as described"
MESSAGE = {"message": "Please review the photos of the damaged item"}
RESOLUTION = {
    "in_favor_of": "customer",
    "resolution_note": "Evidence supports the customer request",
}


@pytest.mark.parametrize(
    ("location", "expected_field"),
    [
        (("body", "body"), "body"),
        (("body", "items", 0, "body"), "items → 0 → body"),
        (("body", "body", "message"), "body → message"),
        (("query", "body"), "query → body"),
        (("path", "body"), "path → body"),
        (("header", "body"), "header → body"),
        (("body",), "request"),
        (("query", "page"), "query → page"),
    ],
)
async def test_validation_error_preserves_real_field_names(location, expected_field):
    application = FastAPI()
    _register_exception_handlers(application)

    @application.post("/validation-probe")
    async def probe():
        raise RequestValidationError(
            [{"type": "value_error", "loc": location, "msg": "Invalid test value"}]
        )

    async with AsyncClient(
        transport=ASGITransport(app=application), base_url="http://testserver"
    ) as http:
        response = await http.post("/validation-probe")
    error(response, 422, "VALIDATION_ERROR", expected_field)
    assert response.json()["error"]["fields"] == {expected_field: "Invalid test value"}


@pytest.fixture
async def case(db):
    """Delivered/collected fixtures; no checkout or payment-provider mocks."""
    users, sellers, headers, products, variants = {}, {}, {}, {}, {}
    for name, role in (
        ("buyer", UserRole.customer),
        ("other", UserRole.customer),
        ("seller", UserRole.seller),
        ("foreign", UserRole.seller),
        ("admin", UserRole.admin),
    ):
        user = User(
            email=f"{name}@example.com",
            first_name=name,
            phone="03001234567",
            role=role,
            has_verified_email=True,
            password_hash="synthetic-only",
        )
        db.add(user)
        users[name] = user
    await db.flush()
    for name, price in (("seller", 1200), ("foreign", 600)):
        seller = Seller(
            user_id=users[name].id,
            brand_name=f"{name} Brand",
            slug=name,
            status=SellerStatus.active,
        )
        db.add(seller)
        await db.flush()
        sellers[name] = seller
        db.add(SellerWallet(seller_id=seller.id, pending_balance=Decimal("1000")))
        product = Product(
            seller_id=seller.id,
            name=f"{name} shirt",
            slug=f"{name}-shirt",
            price=Decimal(price),
            is_published=True,
        )
        db.add(product)
        await db.flush()
        products[name] = product
        variant = ProductVariant(
            product_id=product.id,
            sku=f"WHZ-{name}-M",
            size_type=SizeType.alpha,
            size_value="M",
            colour="Ivory",
        )
        db.add(variant)
        await db.flush()
        variants[name] = variant
        db.add(ProductInventory(variant_id=variant.id, stock=8, reserved=0))
    ids = {}
    for kind in ("account", "guest"):
        subtotal = Decimal("3000" if kind == "account" else "2400")
        order = Order(
            user_id=users["buyer"].id if kind == "account" else None,
            guest_email="guest@example.com" if kind == "guest" else None,
            guest_name="Guest Buyer" if kind == "guest" else None,
            order_number=f"WHZ-RETURN-{kind.upper()}",
            status=OrderStatus.delivered,
            payment_method=StoredPaymentMethod.cod,
            subtotal=subtotal,
            discount_amount=subtotal / 10,
            shipping_fee=Decimal("200"),
            total=subtotal * Decimal(".9") + 200,
        )
        db.add(order)
        await db.flush()
        ids[kind] = {"order": order.id, "seller_orders": {}, "items": {}}
        for name in ("seller", "foreign") if kind == "account" else ("seller",):
            quantity, price = (2, 1200) if name == "seller" else (1, 600)
            seller_order = SellerOrder(
                order_id=order.id,
                seller_id=sellers[name].id,
                status=SellerOrderStatus.delivered,
                subtotal=Decimal(quantity * price) * Decimal(".9"),
                delivered_at=datetime.now(UTC),
            )
            item = OrderItem(
                order_id=order.id,
                seller_id=sellers[name].id,
                product_id=products[name].id,
                variant_id=variants[name].id,
                product_name=products[name].name,
                variant_label="M / Ivory",
                unit_price=Decimal(price),
                quantity=quantity,
                subtotal=Decimal(price * quantity),
            )
            db.add_all([seller_order, item])
            await db.flush()
            ids[kind]["seller_orders"][name] = seller_order.id
            ids[kind]["items"][name] = item.id
        payment = Payment(
            order_id=order.id,
            method="cod",
            status=PaymentStatus.completed,
            amount=order.total,
            paid_at=datetime.now(UTC),
        )
        db.add(payment)
        await db.flush()
        ids[kind]["payment"] = payment.id
    await db.commit()
    for name, user in users.items():
        token, _ = create_access_token(
            subject=str(user.id), role=user.role.value, extra_claims={"ver": user.auth_version}
        )
        headers[name] = {"Authorization": f"Bearer {token}"}
    return {"ids": ids, "headers": headers, "users": {key: user.id for key, user in users.items()}}


def payload(case, *, guest=False, quantity=1):
    order = case["ids"]["guest" if guest else "account"]
    return {
        "seller_order_id": str(order["seller_orders"]["seller"]),
        "reason": REASON,
        "items": [{"order_item_id": str(order["items"]["seller"]), "quantity": quantity}],
    }


async def request_return(client, case, *, guest=False, quantity=1):
    headers = (
        {"X-Guest-Token": create_guest_token(case["ids"]["guest"]["order"])}
        if guest
        else case["headers"]["buyer"]
    )
    response = await client.post(
        "/api/v1/returns/guest" if guest else "/api/v1/returns",
        headers=headers,
        json=payload(case, guest=guest, quantity=quantity),
    )
    assert response.status_code == 201, response.text
    return response.json()


@pytest.fixture
async def requested(client, case):
    return await request_return(client, case)


async def snapshot(db, *, financial=False):
    models = (
        Order,
        OrderItem,
        SellerOrder,
        ProductInventory,
        Payment,
        Refund,
        SellerWallet,
        CommissionLedger,
        WalletTransaction,
        RefundAccounting,
        RefundAllocation,
    )
    if not financial:
        models += (Return, ReturnItem, Dispute, DisputeMessage)
    state = {}
    for model in models:
        rows = (await db.execute(select(*model.__table__.columns))).all()
        state[model.__tablename__] = sorted(tuple(str(value) for value in row) for row in rows)
    return state


def error(response, status, code, field=None):
    assert response.status_code == status, response.text
    body = response.json()["error"]
    assert body["code"] == code
    if field is not None:
        assert field in body["fields"], body


def admin_requests(return_id, dispute_id):
    return [
        ("GET", "/admin/returns", None),
        ("GET", f"/admin/returns/{return_id}", None),
        *[
            ("POST", f"/admin/returns/{return_id}/{action}", {})
            for action in ("approve", "reject", "received", "refund")
        ],
        ("GET", "/admin/disputes", None),
        ("GET", f"/admin/disputes/{dispute_id}", None),
        ("POST", f"/admin/disputes/{dispute_id}/messages", {"body": "Evidence reviewed"}),
        ("POST", f"/admin/disputes/{dispute_id}/resolve", RESOLUTION),
    ]


async def test_protected_endpoints_require_exact_auth(client, db, case, requested):
    return_id = requested["id"]
    requests = [
        ("POST", "/returns", payload(case)),
        ("GET", "/returns", None),
        ("GET", f"/returns/{return_id}", None),
        ("POST", f"/returns/{return_id}/dispute", MESSAGE),
        ("GET", f"/returns/{return_id}/dispute", None),
        ("POST", f"/returns/{return_id}/dispute/messages", {"body": "Evidence"}),
        ("POST", "/returns/guest", payload(case, guest=True)),
        ("GET", f"/returns/guest/{return_id}", None),
        ("GET", "/seller/returns", None),
        ("GET", f"/seller/returns/{return_id}", None),
        *[
            ("POST", f"/seller/returns/{return_id}/{action}", {})
            for action in ("approve", "reject", "received")
        ],
        *admin_requests(return_id, uuid4()),
    ]
    before = await snapshot(db)
    for method, path, body in requests:
        response = await client.request(method, "/api/v1" + path, json=body)
        error(response, 401, "UNAUTHORIZED")
        assert await snapshot(db) == before


@pytest.mark.parametrize("role", ["buyer", "seller"])
async def test_admin_endpoints_reject_non_admin_roles(client, db, case, requested, role):
    before = await snapshot(db)
    for method, path, body in admin_requests(requested["id"], uuid4()):
        response = await client.request(
            method, "/api/v1" + path, headers=case["headers"][role], json=body
        )
        error(response, 403, "FORBIDDEN")
        assert await snapshot(db) == before


@pytest.mark.parametrize(
    ("role", "method", "path", "body", "field"),
    [
        ("buyer", "POST", "/returns", {"reason": "bad"}, "reason"),
        ("buyer", "POST", "/returns", {"items": []}, "items"),
        ("buyer", "GET", "/returns?page=0", None, "query → page"),
        ("buyer", "POST", "/returns/{id}/dispute", {"message": "bad"}, "message"),
        ("buyer", "POST", "/returns/{id}/dispute/messages", {"body": ""}, "body"),
        ("admin", "GET", "/admin/returns?status=unknown", None, "query → status"),
        ("admin", "GET", "/admin/disputes?status=unknown", None, "query → status"),
        (
            "admin",
            "POST",
            "/admin/disputes/{id}/resolve",
            {**RESOLUTION, "in_favor_of": "nobody"},
            "in_favor_of",
        ),
    ],
)
async def test_authenticated_validation(
    client, db, case, requested, role, method, path, body, field
):
    before = await snapshot(db)
    if path == "/returns":
        body = {**payload(case), **body}
    response = await client.request(
        method,
        "/api/v1" + path.format(id=requested["id"]),
        headers=case["headers"][role],
        json=body,
    )
    error(response, 422, "VALIDATION_ERROR", field)
    if path.endswith("/dispute/messages"):
        assert (
            response.json()["error"]["fields"][field] == "String should have at least 1 character"
        )
    assert await snapshot(db) == before


@pytest.mark.parametrize("kind", ["duplicate", "foreign_item", "missing_item", "over_quantity"])
async def test_invalid_return_items_cannot_change_state(client, db, case, kind):
    body = payload(case)
    if kind == "duplicate":
        body["items"] *= 2
    elif kind == "foreign_item":
        body["items"][0]["order_item_id"] = str(case["ids"]["account"]["items"]["foreign"])
    elif kind == "missing_item":
        body["items"][0]["order_item_id"] = str(uuid4())
    else:
        body["items"][0]["quantity"] = 3
    before = await snapshot(db)
    response = await client.post("/api/v1/returns", headers=case["headers"]["buyer"], json=body)
    error(response, 422, "BUSINESS_RULE_VIOLATION")
    assert await snapshot(db) == before


@pytest.mark.parametrize("status", ["processing", "cancelled"])
async def test_non_delivered_orders_cannot_be_returned(client, db, case, status):
    order = await db.get(Order, case["ids"]["account"]["order"])
    order.status = OrderStatus(status)
    await db.commit()
    before = await snapshot(db)
    response = await client.post(
        "/api/v1/returns", headers=case["headers"]["buyer"], json=payload(case)
    )
    error(response, 422, "BUSINESS_RULE_VIOLATION")
    assert await snapshot(db) == before


async def test_return_customer_and_seller_isolation(client, db, case, requested):
    return_id = requested["id"]
    before = await snapshot(db)
    response = await client.post(
        "/api/v1/returns", headers=case["headers"]["other"], json=payload(case)
    )
    error(response, 403, "FORBIDDEN")
    for path, role in (("/returns", "other"), ("/seller/returns", "foreign")):
        response = await client.get("/api/v1" + path, headers=case["headers"][role])
        assert response.status_code == 200, response.text
        assert response.json()["data"] == []
    for method, path, role, body in [
        ("GET", f"/returns/{return_id}", "other", None),
        ("POST", f"/returns/{return_id}/dispute", "other", MESSAGE),
        ("GET", f"/returns/{return_id}/dispute", "other", None),
        ("POST", f"/returns/{return_id}/dispute/messages", "other", {"body": "Evidence"}),
        ("GET", f"/seller/returns/{return_id}", "foreign", None),
        *[
            ("POST", f"/seller/returns/{return_id}/{action}", "foreign", {})
            for action in ("approve", "reject", "received")
        ],
    ]:
        response = await client.request(
            method, "/api/v1" + path, headers=case["headers"][role], json=body
        )
        error(response, 404, "NOT_FOUND")
        assert await snapshot(db) == before
    response = await client.get(f"/api/v1/returns/{return_id}", headers=case["headers"]["buyer"])
    assert response.status_code == 200
    assert response.json()["items"][0]["quantity"] == 1
    for path, role in (
        ("/returns", "buyer"),
        ("/seller/returns", "seller"),
        ("/admin/returns", "admin"),
    ):
        response = await client.get("/api/v1" + path, headers=case["headers"][role])
        assert response.status_code == 200, response.text
        assert [row["id"] for row in response.json()["data"]] == [return_id]
    response = await client.get(
        f"/api/v1/seller/returns/{return_id}", headers=case["headers"]["seller"]
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert Decimal(body["estimated_refund_amount"]) == Decimal("1080")
    assert body["available_actions"] == ["approve", "reject"]
    assert "customer" not in body and "payment_id" not in body
    assert await snapshot(db) == before


async def test_cumulative_return_quantities_are_bounded(client, db, case, requested):
    await request_return(client, case)
    before = await snapshot(db)
    response = await client.post(
        "/api/v1/returns", headers=case["headers"]["buyer"], json=payload(case)
    )
    error(response, 422, "BUSINESS_RULE_VIOLATION")
    assert await snapshot(db) == before


@pytest.mark.parametrize("actor", ["admin", "seller"])
async def test_return_lifecycle_and_pending_refund_replay(client, db, case, requested, actor):
    return_id = requested["id"]
    prefix = "/admin" if actor == "admin" else "/seller"
    financial_before = await snapshot(db, financial=True)
    # Receipt cannot skip approval.
    before = await snapshot(db)
    response = await client.post(
        f"/api/v1{prefix}/returns/{return_id}/received",
        headers=case["headers"][actor],
        json={},
    )
    error(response, 422, "BUSINESS_RULE_VIOLATION")
    assert await snapshot(db) == before
    for action, expected in (("approve", "approved"), ("received", "received")):
        response = await client.post(
            f"/api/v1{prefix}/returns/{return_id}/{action}",
            headers=case["headers"][actor],
            json={},
        )
        assert response.status_code == 200, response.text
        state = await db.scalar(select(Return.status).where(Return.id == UUID(return_id)))
        assert state.value == expected
        before = await snapshot(db)
        replay = await client.post(
            f"/api/v1{prefix}/returns/{return_id}/{action}",
            headers=case["headers"][actor],
            json={},
        )
        error(replay, 422, "BUSINESS_RULE_VIOLATION")
        assert await snapshot(db) == before
    assert await snapshot(db, financial=True) == financial_before
    detail = await client.get(
        f"/api/v1/admin/returns/{return_id}", headers=case["headers"]["admin"]
    )
    assert detail.status_code == 200, detail.text
    assert detail.json()["available_actions"] == ["request_refund"]
    assert detail.json()["customer"]["email"] == "buyer@example.com"
    assert Decimal(detail.json()["estimated_refund_amount"]) == Decimal("1080")
    path = f"/api/v1/admin/returns/{return_id}/refund"
    response = await client.post(path, headers=case["headers"]["admin"], json={})
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "pending"
    refund_id = response.json()["refund_id"]
    refund = await db.get(Refund, UUID(refund_id))
    assert refund.return_id == UUID(return_id)
    assert refund.amount == Decimal("1080")
    assert refund.processed_at is None and refund.gateway_ref is None
    after = await snapshot(db, financial=True)
    assert {key: value for key, value in after.items() if key != "refunds"} == {
        key: value for key, value in financial_before.items() if key != "refunds"
    }
    before = await snapshot(db)
    replay = await client.post(path, headers=case["headers"]["admin"], json={})
    assert replay.status_code == 200, replay.text
    assert replay.json()["refund_id"] == refund_id
    assert await snapshot(db) == before
    response = await client.post(
        path, headers=case["headers"]["admin"], json={"admin_note": "Changed refund reason"}
    )
    error(response, 422, "BUSINESS_RULE_VIOLATION")
    assert await snapshot(db) == before
    detail = await client.get(
        f"/api/v1/admin/returns/{return_id}", headers=case["headers"]["admin"]
    )
    assert detail.status_code == 200
    assert detail.json()["status"] == "received"
    assert detail.json()["refund"]["status"] == "pending"
    assert detail.json()["available_actions"] == []


@pytest.mark.parametrize("favor", ["customer", "seller"])
async def test_dispute_messages_resolution_and_replays(client, db, case, requested, favor):
    return_id = requested["id"]
    response = await client.post(
        f"/api/v1/seller/returns/{return_id}/reject",
        headers=case["headers"]["seller"],
        json={},
    )
    assert response.status_code == 200
    path = f"/api/v1/returns/{return_id}/dispute"
    response = await client.post(path, headers=case["headers"]["buyer"], json=MESSAGE)
    assert response.status_code == 201, response.text
    dispute_id = response.json()["id"]
    assert response.json()["messages"][0]["body"] == MESSAGE["message"]
    before = await snapshot(db)
    response = await client.post(path, headers=case["headers"]["buyer"], json=MESSAGE)
    error(response, 422, "BUSINESS_RULE_VIOLATION")
    assert await snapshot(db) == before
    response = await client.get(path, headers=case["headers"]["other"])
    error(response, 404, "NOT_FOUND")
    response = await client.post(
        path + "/messages", headers=case["headers"]["buyer"], json={"body": "Further evidence"}
    )
    assert response.status_code == 201
    assert response.json()["sender_id"] == str(case["users"]["buyer"])
    admin_path = f"/api/v1/admin/disputes/{dispute_id}"
    response = await client.post(
        admin_path + "/messages", headers=case["headers"]["admin"], json={"body": "Review started"}
    )
    assert response.status_code == 201
    response = await client.get(admin_path, headers=case["headers"]["admin"])
    assert response.status_code == 200
    assert response.json()["status"] == "under_review"
    assert len(response.json()["messages"]) == 3
    response = await client.get(
        "/api/v1/admin/disputes?status=under_review", headers=case["headers"]["admin"]
    )
    assert response.status_code == 200
    assert [row["id"] for row in response.json()["data"]] == [dispute_id]
    resolution = {**RESOLUTION, "in_favor_of": favor}
    response = await client.post(
        admin_path + "/resolve", headers=case["headers"]["admin"], json=resolution
    )
    assert response.status_code == 200, response.text
    assert response.json()["status"] == f"resolved_{favor}"
    assert response.json()["resolved_at"] is not None
    state = await db.scalar(select(Return.status).where(Return.id == UUID(return_id)))
    assert state.value == ("approved" if favor == "customer" else "rejected")
    before = await snapshot(db)
    response = await client.post(
        admin_path + "/resolve", headers=case["headers"]["admin"], json=resolution
    )
    error(response, 422, "BUSINESS_RULE_VIOLATION")
    for message_path, role in ((path + "/messages", "buyer"), (admin_path + "/messages", "admin")):
        response = await client.post(
            message_path, headers=case["headers"][role], json={"body": "Late message"}
        )
        error(response, 422, "BUSINESS_RULE_VIOLATION")
    assert await snapshot(db) == before


async def test_guest_return_capability_is_order_scoped(client, db, case):
    created = await request_return(client, case, guest=True)
    path = f"/api/v1/returns/guest/{created['id']}"
    headers = {"X-Guest-Token": create_guest_token(case["ids"]["guest"]["order"])}
    response = await client.get(path, headers=headers)
    assert response.status_code == 200
    before = await snapshot(db)
    for token in ("forged", create_guest_token(case["ids"]["account"]["order"])):
        response = await client.get(path, headers={"X-Guest-Token": token})
        error(response, 404, "NOT_FOUND")
    response = await client.post(
        "/api/v1/returns/guest",
        headers={"X-Guest-Token": create_guest_token(case["ids"]["account"]["order"])},
        json=payload(case),
    )
    error(response, 404, "NOT_FOUND")
    response = await client.get(
        f"/api/v1/returns/{created['id']}", headers=case["headers"]["buyer"]
    )
    error(response, 404, "NOT_FOUND")
    assert await snapshot(db) == before
