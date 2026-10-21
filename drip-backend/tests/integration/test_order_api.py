"""Order, cart, coupon and seller-order API checks against isolated PostgreSQL."""

from decimal import Decimal
from unittest.mock import AsyncMock
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select

from app.core.config import settings
from app.core.security import create_access_token
from app.models.coupon import Coupon, CouponUsage, DiscountType
from app.models.order import Order, OrderItem, OrderStatus, SellerOrder
from app.models.product import Product, ProductInventory, ProductVariant, SizeType
from app.models.seller import Seller, SellerStatus
from app.models.user import User, UserRole
from app.services.order_service import OrderService

pytestmark = pytest.mark.integration

ADDRESS = {
    "recipient_name": "Ali Khan",
    "phone": "03001234567",
    "street": "House 5, Street 12",
    "city": "Karachi",
    "province": "Sindh",
}
ORDER_PAYLOAD = {"shipping_address": ADDRESS, "payment_method": "cod"}


@pytest.fixture
async def shop(db, monkeypatch):
    """Use real authentication, inventory and service logic; stub only scheduling."""
    monkeypatch.setattr(OrderService, "_enqueue_cod_timeout", AsyncMock())
    monkeypatch.setattr(settings, "PAYFAST_ENABLED", False)
    users = {}
    for name, role in (
        ("buyer", UserRole.customer),
        ("other", UserRole.customer),
        ("seller", UserRole.seller),
        ("foreign_seller", UserRole.seller),
        ("admin", UserRole.admin),
    ):
        user = User(
            email=f"{name}@example.com",
            role=role,
            password_hash="synthetic-only",
            has_verified_email=True,
        )
        db.add(user)
        users[name] = user
    await db.flush()
    sellers = {}
    for name in ("seller", "foreign_seller"):
        seller = Seller(
            user_id=users[name].id,
            brand_name=name,
            slug=name.replace("_", "-"),
            status=SellerStatus.active,
        )
        db.add(seller)
        sellers[name] = seller
    await db.flush()
    product = Product(
        seller_id=sellers["seller"].id,
        name="Test shirt",
        slug="test-shirt",
        price=Decimal("1500"),
        sale_price=Decimal("1200"),
        is_published=True,
    )
    db.add(product)
    await db.flush()
    variant = ProductVariant(
        product_id=product.id,
        sku="WHZ-ORDER-M",
        size_type=SizeType.alpha,
        size_value="M",
        colour="Ivory",
    )
    db.add(variant)
    await db.flush()
    inventory = ProductInventory(variant_id=variant.id, stock=8, reserved=0)
    coupon = Coupon(
        code="SAVE10",
        discount_type=DiscountType.percentage,
        discount_value=Decimal("10"),
        min_order_amount=Decimal("1000"),
    )
    db.add_all([inventory, coupon])
    await db.commit()
    headers = {}
    for name, user in users.items():
        token, _ = create_access_token(
            subject=str(user.id),
            role=user.role.value,
            extra_claims={"ver": user.auth_version},
        )
        headers[name] = {"Authorization": f"Bearer {token}"}
    return {
        "users": users,
        "sellers": sellers,
        "headers": headers,
        "variant": variant,
        "inventory": inventory,
        "coupon": coupon,
    }


async def snapshot(db):
    """Compare persisted order/accounting rows, not merely response codes."""
    state = {}
    for model in (Order, OrderItem, SellerOrder, ProductInventory, Coupon, CouponUsage):
        rows = (await db.execute(select(*model.__table__.columns))).all()
        state[model.__tablename__] = sorted(tuple(str(value) for value in row) for row in rows)
    return state


def error(response, status, code, field=None):
    assert response.status_code == status, response.text
    body = response.json()["error"]
    assert body["code"] == code
    if field is not None:
        assert field in body["fields"], body


def guest_payload(shop, quantity=2):
    return {
        **ORDER_PAYLOAD,
        "guest_email": "guest@example.com",
        "guest_name": "Guest Buyer",
        "guest_phone": "03001234567",
        "items": [{"variant_id": str(shop["variant"].id), "quantity": quantity}],
    }


async def create_order(client, shop, *, guest=False, coupon=False):
    if guest:
        payload = guest_payload(shop)
        quote = await client.post("/api/v1/orders/guest/quote", json={"items": payload["items"]})
        assert quote.status_code == 200, quote.text
        response = await client.post(
            "/api/v1/orders/guest",
            json={
                **payload,
                "checkout_key": str(uuid4()),
                "quote_token": quote.json()["quote_token"],
            },
        )
    else:
        response = await client.post(
            "/api/v1/cart",
            headers=shop["headers"]["buyer"],
            json={"variant_id": str(shop["variant"].id), "quantity": 2},
        )
        assert response.status_code == 200, response.text
        payload = {**ORDER_PAYLOAD, **({"coupon_code": "SAVE10"} if coupon else {})}
        quote = await client.post(
            "/api/v1/orders/quote", headers=shop["headers"]["buyer"], json=payload
        )
        assert quote.status_code == 200, quote.text
        response = await client.post(
            "/api/v1/orders",
            headers=shop["headers"]["buyer"],
            json={
                **payload,
                "checkout_key": str(uuid4()),
                "quote_token": quote.json()["quote_token"],
            },
        )
    assert response.status_code == 201, response.text
    return response.json()


@pytest.mark.parametrize(
    ("method", "path", "payload"),
    [
        ("POST", "/orders", ORDER_PAYLOAD),
        ("GET", "/orders", None),
        ("GET", "/orders/{id}", None),
        ("GET", "/orders/number/WHZ-UNKNOWN", None),
        ("POST", "/orders/{id}/cancel", {"reason": "Changed mind"}),
        ("POST", "/coupons/validate", {"code": "SAVE10", "subtotal": 1200}),
        ("GET", "/seller/orders", None),
        ("GET", "/seller/orders/{id}", None),
        ("PUT", "/seller/orders/{id}/status", {"status": "processing"}),
        ("GET", "/cart", None),
        ("POST", "/cart", {"variant_id": str(uuid4()), "quantity": 1}),
        ("PATCH", "/cart/{id}", {"quantity": 2}),
        ("DELETE", "/cart/{id}", None),
        ("POST", "/cart/clear", None),
        ("POST", "/cart/sync", {"items": []}),
    ],
)
async def test_missing_auth_is_exact_401(client, db, shop, method, path, payload):
    before = await snapshot(db)
    response = await client.request(method, "/api/v1" + path.format(id=uuid4()), json=payload)
    error(response, 401, "UNAUTHORIZED")
    assert await snapshot(db) == before


@pytest.mark.parametrize(
    ("role", "method", "path", "payload", "field"),
    [
        (
            "buyer",
            "POST",
            "/orders",
            {**ORDER_PAYLOAD, "payment_method": "bitcoin"},
            "payment_method",
        ),
        ("buyer", "POST", "/orders", {"payment_method": "cod"}, "shipping_address"),
        ("buyer", "GET", "/orders?page=0", None, "query → page"),
        ("buyer", "POST", "/coupons/validate", {"code": "SAVE10", "subtotal": 0}, "subtotal"),
        ("buyer", "POST", "/cart", {"quantity": 0}, "quantity"),
        ("buyer", "POST", "/cart", {"quantity": 101}, "quantity"),
        ("buyer", "PATCH", "/cart/{id}", {"quantity": -1}, "quantity"),
        ("buyer", "PATCH", "/cart/{id}", {"quantity": 101}, "quantity"),
        ("seller", "GET", "/seller/orders?status=unknown", None, "query → status"),
        ("seller", "GET", "/seller/orders?page=0", None, "query → page"),
        ("seller", "PUT", "/seller/orders/{id}/status", {"status": "invalid"}, "status"),
    ],
)
async def test_authenticated_validation(client, db, shop, role, method, path, payload, field):
    before = await snapshot(db)
    if path == "/cart":
        payload = {**payload, "variant_id": str(shop["variant"].id)}
    response = await client.request(
        method,
        "/api/v1" + path.format(id=shop["variant"].id),
        headers=shop["headers"][role],
        json=payload,
    )
    error(response, 422, "VALIDATION_ERROR", field)
    assert await snapshot(db) == before
    cart = await client.get("/api/v1/cart", headers=shop["headers"]["buyer"])
    assert cart.status_code == 200
    assert cart.json()["items"] == []


@pytest.mark.parametrize(
    ("patch", "field"),
    [
        ({"items": []}, "items"),
        ({"guest_phone": "123"}, "guest_phone"),
        ({"guest_email": "invalid"}, "guest_email"),
    ],
)
async def test_guest_checkout_validation(client, db, shop, patch, field):
    before = await snapshot(db)
    response = await client.post("/api/v1/orders/guest", json={**guest_payload(shop), **patch})
    error(response, 422, "VALIDATION_ERROR", field)
    assert await snapshot(db) == before


async def test_cart_lifecycle_and_account_isolation(client, db, shop):
    headers = shop["headers"]["buyer"]
    variant = str(shop["variant"].id)
    before = await snapshot(db)
    response = await client.get("/api/v1/cart", headers=headers)
    assert response.status_code == 200
    assert response.json()["items"] == []
    for quantity, expected in ((2, 2), (1, 3)):
        response = await client.post(
            "/api/v1/cart", headers=headers, json={"variant_id": variant, "quantity": quantity}
        )
        assert response.status_code == 200, response.text
        assert response.json()["item_count"] == expected
        assert Decimal(response.json()["subtotal"]) == 1200 * expected
    other = await client.get("/api/v1/cart", headers=shop["headers"]["other"])
    assert other.status_code == 200
    assert other.json()["items"] == []
    response = await client.patch(f"/api/v1/cart/{variant}", headers=headers, json={"quantity": 4})
    assert response.status_code == 200
    assert response.json()["item_count"] == 4
    response = await client.post(
        "/api/v1/cart/sync",
        headers=headers,
        json={"items": [{"variant_id": variant, "quantity": 2}]},
    )
    assert response.status_code == 200
    assert response.json()["item_count"] == 4
    response = await client.patch(f"/api/v1/cart/{variant}", headers=headers, json={"quantity": 0})
    assert response.status_code == 200
    assert response.json()["items"] == []
    await client.post("/api/v1/cart", headers=headers, json={"variant_id": variant, "quantity": 1})
    response = await client.delete(f"/api/v1/cart/{variant}", headers=headers)
    assert response.status_code == 204
    await client.post("/api/v1/cart", headers=headers, json={"variant_id": variant, "quantity": 1})
    response = await client.post("/api/v1/cart/clear", headers=headers)
    assert response.status_code == 204
    response = await client.get("/api/v1/cart", headers=headers)
    assert response.json()["items"] == []
    assert await snapshot(db) == before


@pytest.mark.parametrize("missing", [False, True])
async def test_rejected_cart_add_preserves_state(client, db, shop, missing):
    before = await snapshot(db)
    response = await client.post(
        "/api/v1/cart",
        headers=shop["headers"]["buyer"],
        json={"variant_id": str(uuid4() if missing else shop["variant"].id), "quantity": 9},
    )
    error(response, 404 if missing else 422, "NOT_FOUND" if missing else "BUSINESS_RULE_VIOLATION")
    response = await client.get("/api/v1/cart", headers=shop["headers"]["buyer"])
    assert response.status_code == 200
    assert response.json()["items"] == []
    assert await snapshot(db) == before


async def test_checkout_cancellation_releases_reservation_once(client, db, shop):
    created = await create_order(client, shop)
    order_id = UUID(created["order_id"])
    order = await db.get(Order, order_id)
    await db.refresh(shop["inventory"])
    assert order.user_id == shop["users"]["buyer"].id
    assert order.status == OrderStatus.pending_cod_verification
    assert order.subtotal == Decimal("2400")
    assert order.total == order.subtotal + order.shipping_fee
    assert Decimal(created["total"]) == order.total
    assert (shop["inventory"].stock, shop["inventory"].reserved) == (8, 2)
    cart = await client.get("/api/v1/cart", headers=shop["headers"]["buyer"])
    assert cart.json()["items"] == []
    response = await client.get(f"/api/v1/orders/{order_id}", headers=shop["headers"]["buyer"])
    assert response.status_code == 200
    assert response.json()["items"][0]["quantity"] == 2
    response = await client.get("/api/v1/orders", headers=shop["headers"]["buyer"])
    assert response.status_code == 200
    assert [row["id"] for row in response.json()["data"]] == [str(order_id)]
    response = await client.post(
        f"/api/v1/orders/{order_id}/cancel",
        headers=shop["headers"]["buyer"],
        json={"reason": "Changed mind"},
    )
    assert response.status_code == 200, response.text
    await db.refresh(order)
    await db.refresh(shop["inventory"])
    assert order.status == OrderStatus.cancelled
    assert (shop["inventory"].stock, shop["inventory"].reserved) == (8, 0)
    before = await snapshot(db)
    replay = await client.post(
        f"/api/v1/orders/{order_id}/cancel",
        headers=shop["headers"]["buyer"],
        json={},
    )
    error(replay, 422, "BUSINESS_RULE_VIOLATION")
    assert await snapshot(db) == before


async def test_guest_capability_and_email_is_not_authorization(client, db, shop):
    created = await create_order(client, shop, guest=True)
    order_id = created["order_id"]
    headers = {"X-Guest-Token": created["guest_token"]}
    before = await snapshot(db)
    for path in (f"/orders/{order_id}", f"/orders/number/{created['order_number']}"):
        allowed = await client.get("/api/v1" + path, headers=headers)
        assert allowed.status_code == 200, allowed.text
        assert allowed.json()["id"] == order_id
        denied = await client.get("/api/v1" + path, params={"email": "guest@example.com"})
        error(denied, 401, "UNAUTHORIZED")
        denied = await client.get("/api/v1" + path, headers={"X-Guest-Token": "forged"})
        error(denied, 404, "NOT_FOUND")
    assert await snapshot(db) == before
    response = await client.post(f"/api/v1/orders/{order_id}/cancel", headers=headers, json={})
    assert response.status_code == 200
    await db.refresh(shop["inventory"])
    assert shop["inventory"].reserved == 0


async def test_guest_quote_has_no_order_or_stock_side_effects(client, db, shop):
    before = await snapshot(db)
    response = await client.post(
        "/api/v1/orders/guest/quote", json={"items": guest_payload(shop)["items"]}
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["item_count"] == 2
    assert Decimal(body["subtotal"]) == Decimal("2400")
    assert Decimal(body["total"]) == Decimal("2400") + Decimal(body["shipping_fee"])
    assert body["currency"] == "PKR"
    assert body["will_revalidate_on_order"] is True
    assert await snapshot(db) == before


async def test_empty_cart_and_disabled_payfast_fail_without_writes(client, db, shop):
    before = await snapshot(db)
    payload = {**guest_payload(shop), "payment_method": "payfast"}
    auth = shop["headers"]["buyer"]
    await client.post(
        "/api/v1/cart",
        headers=auth,
        json={
            "variant_id": str(shop["variant"].id),
            "quantity": 1,
        },
    )
    quote = await client.post("/api/v1/orders/quote", headers=auth, json={})
    assert quote.status_code == 200, quote.text
    await client.post("/api/v1/cart/clear", headers=auth)
    response = await client.post(
        "/api/v1/orders",
        headers=auth,
        json={
            **ORDER_PAYLOAD,
            "checkout_key": str(uuid4()),
            "quote_token": quote.json()["quote_token"],
        },
    )
    error(response, 422, "BUSINESS_RULE_VIOLATION")
    assert await snapshot(db) == before
    quote = await client.post("/api/v1/orders/guest/quote", json=payload)
    assert quote.status_code == 200, quote.text
    response = await client.post(
        "/api/v1/orders/guest",
        json={
            **payload,
            "checkout_key": str(uuid4()),
            "quote_token": quote.json()["quote_token"],
        },
    )
    error(response, 422, "BUSINESS_RULE_VIOLATION")
    assert await snapshot(db) == before


async def test_coupon_preview_checkout_and_usage_limit(client, db, shop):
    headers = shop["headers"]["buyer"]
    before = await snapshot(db)
    response = await client.post(
        "/api/v1/coupons/validate",
        headers=headers,
        json={"code": "save10", "subtotal": "2400.00"},
    )
    assert response.status_code == 200, response.text
    assert Decimal(response.json()["discount_amount"]) == Decimal("240")
    assert Decimal(response.json()["new_subtotal"]) == Decimal("2160")
    assert await snapshot(db) == before
    created = await create_order(client, shop, coupon=True)
    order = await db.get(Order, UUID(created["order_id"]))
    assert order.discount_amount == Decimal("240")
    assert order.total == Decimal("2160") + order.shipping_fee
    seller_order = await db.scalar(select(SellerOrder).where(SellerOrder.order_id == order.id))
    assert seller_order.subtotal == Decimal("2160")
    await db.refresh(shop["coupon"])
    assert shop["coupon"].uses_count == 1
    usages = list((await db.scalars(select(CouponUsage))).all())
    assert len(usages) == 1
    assert usages[0].order_id == order.id
    before = await snapshot(db)
    response = await client.post(
        "/api/v1/coupons/validate",
        headers=headers,
        json={"code": "SAVE10", "subtotal": "2400.00"},
    )
    error(response, 422, "BUSINESS_RULE_VIOLATION")
    assert await snapshot(db) == before


@pytest.mark.parametrize("role", ["buyer", "admin"])
async def test_non_seller_cannot_manage_seller_orders(client, db, shop, role):
    before = await snapshot(db)
    for method, path, payload in (
        ("GET", "/seller/orders", None),
        ("GET", f"/seller/orders/{uuid4()}", None),
        ("PUT", f"/seller/orders/{uuid4()}/status", {"status": "processing"}),
    ):
        response = await client.request(
            method, "/api/v1" + path, headers=shop["headers"][role], json=payload
        )
        error(response, 403, "FORBIDDEN")
    assert await snapshot(db) == before


async def test_customer_and_seller_order_ownership(client, db, shop):
    created = await create_order(client, shop)
    order_id = UUID(created["order_id"])
    so = await db.scalar(select(SellerOrder).where(SellerOrder.order_id == order_id))
    owner = shop["headers"]["seller"]
    response = await client.get(f"/api/v1/seller/orders/{so.id}", headers=owner)
    assert response.status_code == 200, response.text
    response = await client.get("/api/v1/seller/orders?status=pending", headers=owner)
    assert response.status_code == 200
    assert [row["id"] for row in response.json()["data"]] == [str(so.id)]
    for role, path in (("other", "/orders"), ("foreign_seller", "/seller/orders")):
        response = await client.get("/api/v1" + path, headers=shop["headers"][role])
        assert response.status_code == 200
        assert response.json()["data"] == []
    before = await snapshot(db)
    for method, path, role, payload in (
        ("GET", f"/orders/{order_id}", "other", None),
        ("GET", f"/orders/number/{created['order_number']}", "other", None),
        ("POST", f"/orders/{order_id}/cancel", "other", {}),
        ("GET", f"/seller/orders/{so.id}", "foreign_seller", None),
        ("PUT", f"/seller/orders/{so.id}/status", "foreign_seller", {"status": "processing"}),
    ):
        response = await client.request(
            method, "/api/v1" + path, headers=shop["headers"][role], json=payload
        )
        error(response, 404, "NOT_FOUND")
        assert await snapshot(db) == before
    response = await client.put(
        f"/api/v1/seller/orders/{so.id}/status", headers=owner, json={"status": "shipped"}
    )
    error(response, 422, "VALIDATION_ERROR")
    assert "tracking_number required" in response.text
    assert await snapshot(db) == before
    response = await client.put(
        f"/api/v1/seller/orders/{so.id}/status", headers=owner, json={"status": "processing"}
    )
    error(response, 422, "BUSINESS_RULE_VIOLATION")
    assert await snapshot(db) == before


async def test_verified_fulfilment_and_shipping_replay(client, db, shop):
    created = await create_order(client, shop)
    order = await db.get(Order, UUID(created["order_id"]))
    # This fixture represents prior COD verification, not a test of its admin endpoint.
    order.status = OrderStatus.payment_confirmed
    await db.commit()
    so = await db.scalar(select(SellerOrder).where(SellerOrder.order_id == order.id))
    path = f"/api/v1/seller/orders/{so.id}/status"
    headers = shop["headers"]["seller"]
    response = await client.put(path, headers=headers, json={"status": "delivered"})
    error(response, 422, "BUSINESS_RULE_VIOLATION")
    response = await client.put(path, headers=headers, json={"status": "processing"})
    assert response.status_code == 200, response.text
    response = await client.put(
        path,
        headers=headers,
        json={"status": "shipped", "tracking_number": "TEST-123", "courier_name": "Test Courier"},
    )
    assert response.status_code == 200, response.text
    await db.refresh(order)
    await db.refresh(shop["inventory"])
    assert order.status == OrderStatus.shipped
    assert (shop["inventory"].stock, shop["inventory"].reserved) == (6, 0)
    before = await snapshot(db)
    replay = await client.put(
        path, headers=headers, json={"status": "shipped", "tracking_number": "TEST-123"}
    )
    assert replay.status_code == 200
    assert await snapshot(db) == before
    response = await client.put(path, headers=headers, json={"status": "delivered"})
    assert response.status_code == 200, response.text
    await db.refresh(order)
    assert order.status == OrderStatus.delivered
