"""Cross-account HTTP requests use real rows/tokens, not mocked authorization."""

from decimal import Decimal
from types import SimpleNamespace

import pytest
from sqlalchemy import select
from test_marketplace_regressions import guest_payload
from test_marketplace_regressions import market as marketplace_fixture

from app.core.security import create_access_token
from app.models.notification import Notification
from app.models.order import Order, OrderItem, OrderStatus, SellerOrder
from app.models.product import Product, ProductImage, ProductInventory, ProductVariant, SizeType
from app.models.return_ import Dispute, Return, ReturnStatus
from app.models.review import Review
from app.models.seller import Seller, SellerBankAccount, SellerStatus, SellerWallet
from app.models.user import User, UserAddress, UserRole
from app.services.order_service import OrderService

pytestmark = pytest.mark.integration
market = marketplace_fixture


def headers(user, **claims):
    token, _ = create_access_token(
        subject=str(user.id), role=user.role.value, extra_claims=claims or None
    )
    return {"Authorization": f"Bearer {token}"}


async def request(client, redis, user, method, path, **kwargs):
    # Rate limiting is tested elsewhere; it must never mask an ownership failure.
    await redis.flushdb()
    return await client.request(method, "/api/v1" + path, headers=headers(user), **kwargs)


@pytest.fixture
async def resources(db, market):
    other = User(email="other@example.com", password_hash="test", has_verified_email=True)
    other_seller_user = User(
        email="other-seller@example.com",
        password_hash="test",
        role=UserRole.seller,
        has_verified_email=True,
    )
    db.add_all([other, other_seller_user])
    await db.flush()
    other_seller = Seller(
        user_id=other_seller_user.id,
        brand_name="Other Brand",
        slug="other-brand",
        status=SellerStatus.active,
        total_slots=50,
    )
    db.add(other_seller)
    await db.flush()
    db.add(SellerWallet(seller_id=other_seller.id, available_balance=Decimal("2000")))
    own_product = Product(
        seller_id=other_seller.id,
        name="Other Product",
        slug="other-product",
        price=Decimal("900"),
        is_published=False,
    )
    db.add(own_product)
    await db.flush()
    own_variant = ProductVariant(
        product_id=own_product.id,
        sku="OTHER-M",
        size_type=SizeType.alpha,
        size_value="M",
        colour="Blue",
    )
    db.add(own_variant)
    await db.flush()
    db.add(ProductInventory(variant_id=own_variant.id, stock=4))
    own_image = ProductImage(product_id=own_product.id, url="https://example.test/other.webp")
    address = UserAddress(
        user_id=market.buyer.id, street="Private street", city="Lahore", province="Punjab"
    )
    review = Review(
        user_id=market.buyer.id, product_id=market.product.id, rating=4, body="Owner review"
    )
    notice = Notification(
        user_id=market.buyer.id, type="test", title="Private notice", body="Private body"
    )
    bank = SellerBankAccount(
        seller_id=market.seller.id,
        bank_name="Test bank",
        account_title="Owner",
        account_number="1234567890",
    )
    db.add_all([own_image, address, review, notice, bank])
    created = await OrderService(db).create_guest_order(guest_payload(market))
    order = await db.get(Order, created.order_id)
    order.user_id = market.buyer.id
    order.status = OrderStatus.delivered
    seller_order = await db.scalar(select(SellerOrder).where(SellerOrder.order_id == order.id))
    item = await db.scalar(select(OrderItem).where(OrderItem.order_id == order.id))
    ret = Return(
        order_id=order.id,
        seller_order_id=seller_order.id,
        user_id=market.buyer.id,
        reason="Private return reason",
        status=ReturnStatus.rejected,
    )
    db.add(ret)
    await db.flush()
    dispute = Dispute(return_id=ret.id, seller_id=market.seller.id, user_id=market.buyer.id)
    db.add(dispute)
    await db.commit()
    image = await db.scalar(
        select(ProductImage).where(ProductImage.product_id == market.product.id)
    )
    return SimpleNamespace(**locals())


async def snapshot(db):
    """Exact DB values across mutation targets; denied requests must change none."""
    models = (
        UserAddress,
        Review,
        Notification,
        Product,
        ProductVariant,
        ProductImage,
        ProductInventory,
        SellerBankAccount,
        SellerWallet,
        Order,
        SellerOrder,
        Return,
        Dispute,
    )
    return {
        model.__tablename__: sorted(
            [
                tuple(map(str, row))
                for row in (await db.execute(select(*model.__table__.columns))).all()
            ]
        )
        for model in models
    }


async def test_customer_foreign_ids_denied_without_mutation(
    client, db, market, resources, isolated_redis
):
    r = resources
    cases = [
        ("PATCH", f"/customers/me/addresses/{r.address.id}", {"street": "Stolen"}),
        ("DELETE", f"/customers/me/addresses/{r.address.id}", None),
        ("POST", f"/customers/me/addresses/{r.address.id}/set-default", None),
        ("PATCH", f"/customers/me/reviews/{r.review.id}", {"rating": 1}),
        ("DELETE", f"/customers/me/reviews/{r.review.id}", None),
        ("POST", f"/notifications/{r.notice.id}/read", None),
        ("GET", f"/orders/{r.order.id}", None),
        ("GET", f"/orders/number/{r.order.order_number}", None),
        ("POST", f"/orders/{r.order.id}/cancel", {"reason": "Unauthorized cancellation"}),
        ("POST", "/payments/initiate", {"order_id": str(r.order.id)}),
        ("POST", f"/payments/{r.order.id}/retry", {"payment_method": "cod"}),
        ("GET", f"/payments/{r.order.id}/status", None),
        ("GET", f"/returns/{r.ret.id}", None),
        ("GET", f"/returns/{r.ret.id}/dispute", None),
        ("POST", f"/returns/{r.ret.id}/dispute", {"message": "Another customer's dispute"}),
        ("POST", f"/returns/{r.ret.id}/dispute/messages", {"body": "Unauthorized reply"}),
        (
            "POST",
            "/returns",
            {
                "seller_order_id": str(r.seller_order.id),
                "reason": "Wrong account return",
                "items": [{"order_item_id": str(r.item.id), "quantity": 1}],
            },
        ),
    ]
    before = await snapshot(db)
    for method, path, body in cases:
        response = await request(
            client,
            isolated_redis,
            r.other,
            method,
            path,
            **({"json": body} if body is not None else {}),
        )
        if path.startswith("/notifications/"):
            assert response.status_code == 200 and response.json() == {"marked": False}
        else:
            assert response.status_code in {403, 404}, (
                method,
                path,
                response.status_code,
                response.text,
            )
        assert await snapshot(db) == before, (method, path)
    # Valid owner reads/writes prove these are usable resources, not missing IDs.
    for path in (f"/orders/{r.order.id}", f"/returns/{r.ret.id}", f"/returns/{r.ret.id}/dispute"):
        response = await request(client, isolated_redis, market.buyer, "GET", path)
        assert response.status_code == 200, response.text
    response = await request(
        client,
        isolated_redis,
        market.buyer,
        "PATCH",
        f"/customers/me/addresses/{r.address.id}",
        json={"street": "Owner edit"},
    )
    assert response.status_code == 200, response.text
    response = await request(
        client, isolated_redis, market.buyer, "POST", f"/notifications/{r.notice.id}/read"
    )
    assert response.status_code == 200, response.text


async def test_customer_lists_and_bulk_reads_do_not_cross_accounts(
    client, db, market, resources, isolated_redis
):
    r = resources
    for path, secret in (
        ("/customers/me/addresses", r.address.id),
        ("/customers/me/reviews", r.review.id),
        ("/notifications", r.notice.id),
        ("/orders", r.order.id),
        ("/returns", r.ret.id),
    ):
        own = await request(client, isolated_redis, market.buyer, "GET", path)
        other = await request(client, isolated_redis, r.other, "GET", path)
        assert own.status_code == other.status_code == 200, (path, own.text, other.text)
        assert str(secret) in own.text and str(secret) not in other.text, path
    response = await request(client, isolated_redis, r.other, "POST", "/notifications/read-all")
    assert response.status_code == 200, response.text
    await db.refresh(r.notice)
    assert r.notice.is_read is False


async def test_seller_foreign_ids_denied_without_mutation(
    client, db, market, resources, isolated_redis
):
    r = resources
    base = f"/seller/products/{market.product.id}"
    cases = [
        ("GET", base, None),
        ("PUT", base, {"name": "Stolen product"}),
        ("DELETE", base, None),
        ("POST", base + "/publish", None),
        ("POST", base + "/unpublish", None),
        (
            "POST",
            base + "/variants",
            {"size_type": "alpha", "size_value": "L", "colour": "Black", "stock": 1},
        ),
        ("PATCH", base + f"/variants/{market.variant.id}", {"colour": "Black"}),
        ("PUT", base + "/images/order", {"image_ids": [str(r.image.id)]}),
        ("PUT", base + f"/images/{r.image.id}/primary", None),
        ("DELETE", base + f"/images/{r.image.id}", None),
        ("GET", f"/seller/inventory/{market.variant.id}", None),
        ("PUT", f"/seller/inventory/{market.variant.id}", {"stock": 30}),
        (
            "POST",
            f"/seller/inventory/{market.variant.id}/adjust",
            {"delta": 1, "reason": "Unauthorized restock"},
        ),
        ("DELETE", f"/seller/bank-accounts/{r.bank.id}", None),
        ("GET", f"/seller/orders/{r.seller_order.id}", None),
        ("PUT", f"/seller/orders/{r.seller_order.id}/status", {"status": "processing"}),
        ("GET", f"/seller/returns/{r.ret.id}", None),
        *[
            (
                "POST",
                f"/seller/returns/{r.ret.id}/{action}",
                {"admin_note": "Unauthorized decision"},
            )
            for action in ("approve", "reject", "received")
        ],
        ("POST", "/seller/wallet/withdraw", {"amount": "500", "bank_account_id": str(r.bank.id)}),
    ]
    before = await snapshot(db)
    for method, path, body in cases:
        response = await request(
            client,
            isolated_redis,
            r.other_seller_user,
            method,
            path,
            **({"json": body} if body is not None else {}),
        )
        assert response.status_code in {403, 404}, (
            method,
            path,
            response.status_code,
            response.text,
        )
        assert await snapshot(db) == before, (method, path)
    for path in (
        base,
        f"/seller/inventory/{market.variant.id}",
        f"/seller/orders/{r.seller_order.id}",
        f"/seller/returns/{r.ret.id}",
    ):
        response = await request(client, isolated_redis, market.seller_user, "GET", path)
        assert response.status_code == 200, (path, response.text)
    response = await request(
        client, isolated_redis, market.seller_user, "PUT", base, json={"name": "Owner edit"}
    )
    assert response.status_code == 200, response.text


async def test_seller_nested_ids_cannot_be_mixed(client, db, market, resources, isolated_redis):
    r = resources
    base = f"/seller/products/{r.own_product.id}"
    before = await snapshot(db)
    for method, path, body in (
        ("PATCH", base + f"/variants/{market.variant.id}", {"colour": "Stolen"}),
        ("PUT", base + f"/images/{r.image.id}/primary", None),
        ("DELETE", base + f"/images/{r.image.id}", None),
        ("PUT", base + "/images/order", {"image_ids": [str(r.image.id)]}),
    ):
        response = await request(
            client,
            isolated_redis,
            r.other_seller_user,
            method,
            path,
            **({"json": body} if body is not None else {}),
        )
        assert response.status_code in {400, 403, 404, 409, 422}, (path, response.text)
        if response.status_code == 422:
            assert response.json()["error"]["code"] == "BUSINESS_RULE_VIOLATION"
        assert await snapshot(db) == before


async def test_seller_lists_filters_and_claims_stay_scoped(
    client, db, market, resources, isolated_redis
):
    r = resources
    for path, secret in (
        ("/seller/products", market.product.id),
        ("/seller/inventory", market.variant.id),
        ("/seller/bank-accounts", r.bank.id),
        ("/seller/orders", r.seller_order.id),
        ("/seller/returns", r.ret.id),
    ):
        own = await request(client, isolated_redis, market.seller_user, "GET", path)
        other = await request(client, isolated_redis, r.other_seller_user, "GET", path)
        assert own.status_code == other.status_code == 200, (path, own.text, other.text)
        assert str(secret) in own.text and str(secret) not in other.text, path
    response = await request(
        client,
        isolated_redis,
        r.other_seller_user,
        "GET",
        f"/seller/inventory?product_id={market.product.id}",
    )
    assert response.status_code == 200 and response.json()["data"] == []
    # Even a signed stale/forged seller_id claim is replaced with DB ownership.
    await isolated_redis.flushdb()
    response = await client.get(
        "/api/v1/seller/me", headers=headers(r.other_seller_user, seller_id=str(market.seller.id))
    )
    assert response.status_code == 200 and response.json()["id"] == str(r.other_seller.id)


async def test_foreign_image_upload_denied_before_provider_call(
    client, db, market, resources, isolated_redis, monkeypatch
):
    from unittest.mock import AsyncMock

    from app.services.image_service import ImageService

    upload = AsyncMock(side_effect=AssertionError("Unauthorized request reached storage"))
    monkeypatch.setattr(ImageService, "process_and_upload", upload)
    await isolated_redis.flushdb()
    # The shared client's JSON content type must be omitted for multipart parsing.
    client.headers.pop("content-type", None)
    response = await client.post(
        f"/api/v1/seller/products/{market.product.id}/images",
        headers=headers(resources.other_seller_user),
        files=[("images", ("image.png", b"fake-image", "image/png"))],
    )
    assert response.status_code in {403, 404}, response.text
    upload.assert_not_awaited()


async def test_account_scoped_profile_preferences_cart_and_wishlist(
    client, db, market, resources, isolated_redis
):
    r = resources
    owner, other = headers(market.buyer), headers(r.other)
    # Do not flush Redis between requests: it contains the two users' real carts.
    await isolated_redis.flushdb()
    response = await client.patch(
        "/api/v1/customers/me", headers=owner, json={"first_name": "Private Owner"}
    )
    assert response.status_code == 200, response.text
    response = await client.patch(
        "/api/v1/customers/me", headers=other, json={"first_name": "Other Customer"}
    )
    assert response.status_code == 200, response.text
    await db.refresh(market.buyer)
    assert market.buyer.first_name == "Private Owner"
    for path, body in (
        ("/customers/me/notification-preferences", {"email_promotions": False}),
        ("/notifications/preferences", {"order_updates_email": False}),
    ):
        response = await client.patch("/api/v1" + path, headers=owner, json=body)
        assert response.status_code == 200, response.text
        response = await client.patch(
            "/api/v1" + path, headers=other, json=dict.fromkeys(body, True)
        )
        assert response.status_code == 200, response.text
        own = await client.get("/api/v1" + path, headers=owner)
        assert all(own.json()[key] is False for key in body)
    variant = str(market.variant.id)
    response = await client.post(
        "/api/v1/cart", headers=owner, json={"variant_id": variant, "quantity": 2}
    )
    assert response.status_code == 200, response.text
    for method, path, body in (
        ("POST", "/cart/sync", {"items": [{"variant_id": variant, "quantity": 1}]}),
        ("PATCH", f"/cart/{variant}", {"quantity": 3}),
        ("DELETE", f"/cart/{variant}", None),
        ("POST", "/cart/clear", None),
    ):
        response = await client.request(
            method, "/api/v1" + path, headers=other, **({"json": body} if body else {})
        )
        assert response.status_code in {200, 204}, response.text
        assert await isolated_redis.hget(f"cart:{market.buyer.id}", variant) == "2"
    response = await client.post(
        "/api/v1/customers/me/wishlist", headers=owner, json={"product_id": str(market.product.id)}
    )
    assert response.status_code == 201, response.text
    response = await client.delete(
        f"/api/v1/customers/me/wishlist/{market.product.id}", headers=other
    )
    assert response.status_code == 204, response.text
    assert await isolated_redis.sismember(f"wishlist:{market.buyer.id}", str(market.product.id))
    response = await client.get("/api/v1/customers/me/wishlist", headers=other)
    assert response.status_code == 200 and response.json()["items"] == []


async def test_wallet_history_and_bank_details_are_seller_scoped(
    client, db, market, resources, isolated_redis
):
    from app.schemas.wallet import WithdrawalRequest
    from app.services.wallet_service import WalletService

    wallet = await db.scalar(select(SellerWallet).where(SellerWallet.seller_id == market.seller.id))
    wallet.available_balance = Decimal("1500")
    await db.commit()
    payout = await WalletService(db).request_withdrawal(
        market.seller.id,
        WithdrawalRequest(
            amount=Decimal("500"),
            bank_account_id=resources.bank.id,
        ),
    )
    for path in ("/seller/wallet/payouts", "/seller/wallet/transactions"):
        own = await request(client, isolated_redis, market.seller_user, "GET", path)
        other = await request(client, isolated_redis, resources.other_seller_user, "GET", path)
        assert own.status_code == other.status_code == 200, (path, own.text, other.text)
        assert len(own.json()["data"]) == 1 and other.json()["data"] == []
        if path.endswith("payouts"):
            assert own.json()["data"][0]["id"] == str(payout.id)
            assert resources.bank.account_number not in other.text
    own = await request(client, isolated_redis, market.seller_user, "GET", "/seller/wallet")
    other = await request(
        client, isolated_redis, resources.other_seller_user, "GET", "/seller/wallet"
    )
    assert own.status_code == other.status_code == 200
    assert Decimal(own.json()["available_balance"]) == 1000
    assert Decimal(other.json()["available_balance"]) == 2000
