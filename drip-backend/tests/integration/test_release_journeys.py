"""Customer and auth workflows against real persisted state."""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import func, select
from test_marketplace_regressions import market as marketplace_fixture

from app.core.exceptions import BusinessRuleError, NotFoundError
from app.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)
from app.models.review import Review, ReviewStatus
from app.models.user import User, UserSession
from app.schemas import auth, user
from app.services.auth_service import AuthService
from app.services.customer_service import CustomerService

pytestmark = pytest.mark.integration
market = marketplace_fixture


def headers(account):
    token, _ = create_access_token(
        subject=str(account.id), role=account.role.value, extra_claims={"ver": account.auth_version}
    )
    return {"Authorization": "Bearer " + token}


async def request(client, account, method, path, expected=200, **kwargs):
    response = await client.request(method, "/api/v1" + path, headers=headers(account), **kwargs)
    assert response.status_code == expected, response.text
    return response.json() if response.content else None


async def test_customer_profile_address_wishlist_preferences(client, db, market):
    account = market.buyer
    profile = await request(client, account, "GET", "/customers/me")
    assert profile["email"] == account.email
    profile = await request(
        client,
        account,
        "PATCH",
        "/customers/me",
        json={"first_name": "Ali", "last_name": "Khan", "phone": "03001234567"},
    )
    assert profile["first_name"] == "Ali"
    address = {
        "street": "12 Test Street",
        "city": "Lahore",
        "province": "Punjab",
        "label": "Home",
        "is_default": True,
    }
    first = await request(client, account, "POST", "/customers/me/addresses", 201, json=address)
    second = await request(
        client, account, "POST", "/customers/me/addresses", 201, json={**address, "label": "Work"}
    )
    rows = await request(client, account, "GET", "/customers/me/addresses")
    assert len(rows) == 2 and sum(row["is_default"] for row in rows) == 1
    await request(
        client,
        market.admin,
        "PATCH",
        "/customers/me/addresses/" + first["id"],
        404,
        json={"city": "Karachi"},
    )
    changed = await request(
        client,
        account,
        "PATCH",
        "/customers/me/addresses/" + first["id"],
        json={**address, "city": "Karachi"},
    )
    assert changed["city"] == "Karachi"
    await request(
        client, account, "POST", "/customers/me/addresses/" + second["id"] + "/set-default"
    )
    await request(client, account, "DELETE", "/customers/me/addresses/" + first["id"], 204)
    await request(client, account, "DELETE", "/customers/me/addresses/" + first["id"], 404)
    assert (await request(client, account, "GET", "/customers/me/wishlist"))["total"] == 0
    wishlist = await request(
        client,
        account,
        "POST",
        "/customers/me/wishlist",
        201,
        json={"product_id": str(market.product.id)},
    )
    assert wishlist["total"] == 1 and wishlist["items"][0]["is_in_stock"]
    await request(
        client, account, "DELETE", "/customers/me/wishlist/" + str(market.product.id), 204
    )
    assert (await request(client, account, "GET", "/customers/me/wishlist"))["total"] == 0
    prefs = await request(
        client,
        account,
        "PATCH",
        "/customers/me/notification-preferences",
        json={"email_promotions": False, "sms_order_updates": True},
    )
    assert prefs["email_promotions"] is False and prefs["sms_order_updates"] is True
    assert (
        await request(client, account, "GET", "/customers/me/notification-preferences")
    ) == prefs


async def test_customer_review_moderation_edit_and_delete(client, db, market):
    account = market.buyer
    payload = {
        "product_id": str(market.product.id),
        "rating": 5,
        "title": "Good shirt",
        "body": "Fits well",
    }
    review = await request(client, account, "POST", "/customers/me/reviews", 201, json=payload)
    assert review["status"] == "pending"
    await request(client, account, "POST", "/customers/me/reviews", 422, json=payload)
    assert len(await request(client, account, "GET", "/customers/me/reviews")) == 1
    stored = await db.get(Review, review["id"])
    stored.status = ReviewStatus.approved
    await db.commit()
    public = await request(
        client,
        account,
        "GET",
        f"/customers/reviews/product/{market.product.id}?rating=5&sort=helpful",
    )
    assert public["total"] == 1 and public["avg_rating"] == 5
    await request(
        client,
        market.admin,
        "POST",
        f"/customers/reviews/{stored.id}/helpful",
        204,
        json={"helpful": True},
    )
    changed = await request(
        client,
        account,
        "PATCH",
        f"/customers/me/reviews/{stored.id}",
        json={"rating": 4, "title": "Updated", "body": "Changed review"},
    )
    assert changed["status"] == "pending" and changed["rating"] == 4
    await request(client, account, "DELETE", f"/customers/me/reviews/{stored.id}", 204)
    assert await request(client, account, "GET", "/customers/me/reviews") == []


async def test_customer_password_revokes_tokens_and_account_deletion(db, market):
    service = CustomerService(db)
    market.buyer.password_hash = hash_password("OldPass123")
    await db.commit()
    old_token = headers(market.buyer)["Authorization"].removeprefix("Bearer ")
    await service.change_password(
        market.buyer.id,
        user.ChangePasswordRequest(
            current_password="OldPass123", new_password="NewPass456", confirm_password="NewPass456"
        ),
    )
    await db.refresh(market.buyer)
    assert market.buyer.auth_version == 1
    assert verify_password("NewPass456", market.buyer.password_hash)
    from app.api.deps import get_current_user_payload
    from app.core.exceptions import TokenInvalidError

    with pytest.raises(TokenInvalidError):
        await get_current_user_payload(old_token, db)
    with pytest.raises(BusinessRuleError):
        await service.delete_account(
            market.buyer.id,
            user.DeleteAccountRequest(password="wrong", confirm_phrase="DELETE MY ACCOUNT"),
        )
    await service.delete_account(
        market.buyer.id,
        user.DeleteAccountRequest(password="NewPass456", confirm_phrase="DELETE MY ACCOUNT"),
    )
    await db.refresh(market.buyer)
    assert market.buyer.deleted_at is not None
    with pytest.raises(NotFoundError):
        await service.get_profile(market.buyer.id)


async def test_customer_avatar_uses_validated_storage_upload(db, market, monkeypatch):
    import io

    from PIL import Image

    from app.integrations.supabase_storage import SupabaseStorage

    image = io.BytesIO()
    Image.new("RGB", (2, 2), "red").save(image, format="PNG")
    upload = AsyncMock(return_value="https://example.test/avatar.webp")
    monkeypatch.setattr(SupabaseStorage, "upload", upload)
    result = await CustomerService(db).upload_avatar(market.buyer.id, image.getvalue(), "image/png")
    assert result.avatar_url == "https://example.test/avatar.webp"
    assert upload.call_args.kwargs["bucket"] == "avatars"
    assert upload.call_args.kwargs["content_type"] == "image/webp"
    await db.refresh(market.buyer)
    assert market.buyer.avatar_url == result.avatar_url


async def test_auth_registration_verification_rotation_reset_and_logout(db):
    from app.core.exceptions import AuthenticationError, DuplicateEmailError, EmailNotVerifiedError

    payload = auth.RegisterRequest(
        first_name="Ali", last_name="Khan", email="new@example.com", password="OldPass123"
    )
    registered = await AuthService.register(db, payload)
    with pytest.raises(DuplicateEmailError):
        await AuthService.register(db, payload)
    with pytest.raises(EmailNotVerifiedError):
        await AuthService.login(db, payload.email, payload.password, None)
    verified, refresh = await AuthService.verify_email(db, registered["verify_token"])
    with pytest.raises(BusinessRuleError):
        await AuthService.verify_email(db, registered["verify_token"])
    rotated, new_refresh = await AuthService.refresh_token(db, refresh)
    assert new_refresh != refresh and rotated.access_token
    with pytest.raises(AuthenticationError):
        await AuthService.refresh_token(db, refresh)
    logged_in, refresh = await AuthService.login(db, payload.email, payload.password, None)
    claims = decode_access_token(logged_in.access_token)
    await AuthService.logout(db, refresh, claims["jti"], datetime.now(UTC) + timedelta(minutes=10))
    with pytest.raises(AuthenticationError):
        await AuthService.refresh_token(db, refresh)
    assert await AuthService.forgot_password(db, "absent@example.com") is None
    token = await AuthService.forgot_password(db, payload.email)
    await AuthService.reset_password(db, token, "ResetPass456")
    with pytest.raises(BusinessRuleError):
        await AuthService.reset_password(db, token, "OtherPass789")
    await AuthService.change_password(db, registered["user"].id, "ResetPass456", "FinalPass789")
    assert await db.scalar(select(func.count(UserSession.id))) == 0


async def test_admin_totp_policy_and_seller_refresh(db, market):
    import pyotp

    from app.core.exceptions import TwoFactorRequiredError

    market.admin.password_hash = hash_password("AdminPass123")
    market.seller_user.password_hash = hash_password("SellerPass123")
    await db.commit()
    with pytest.raises(BusinessRuleError):
        await AuthService.setup_totp(db, market.buyer.id)
    setup = await AuthService.setup_totp(db, market.admin.id)
    await AuthService.verify_and_enable_totp(db, market.admin.id, pyotp.TOTP(setup.secret).now())
    with pytest.raises(TwoFactorRequiredError):
        await AuthService.login(db, market.admin.email, "AdminPass123", None)
    logged, _ = await AuthService.login(
        db, market.admin.email, "AdminPass123", pyotp.TOTP(setup.secret).now()
    )
    assert logged.user.role == "admin"
    logged, refresh = await AuthService.login(db, market.seller_user.email, "SellerPass123", None)
    assert logged.user.seller_id == str(market.seller.id)
    rotated, _ = await AuthService.refresh_token(db, refresh)
    assert decode_access_token(rotated.access_token)["seller_id"] == str(market.seller.id)


async def test_seller_product_lifecycle_and_public_visibility(client, db, market, monkeypatch):
    from app.services.image_service import ImageService
    from app.services.product_service import ProductService

    monkeypatch.setattr(ImageService, "delete", AsyncMock())
    seller = market.seller_user
    payload = {
        "name": "Release Test Jacket",
        "description": "A warm jacket for release testing",
        "price": 3000,
        "variants": [{"size_type": "alpha", "size_value": "L", "colour": "Black", "stock": 4}],
    }
    product = await request(client, seller, "POST", "/seller/products", 201, json=payload)
    pid = product["id"]
    images = await ProductService(db).add_images(
        market.seller.id, pid, ["https://example.test/front.webp", "https://example.test/back.webp"]
    )
    await request(client, seller, "POST", f"/seller/products/{pid}/publish")
    public = await request(client, market.buyer, "GET", f"/products/slug/{product['slug']}")
    assert public["name"] == payload["name"]
    await request(
        client,
        seller,
        "PUT",
        f"/seller/products/{pid}",
        json={"name": "Updated Jacket", "price": 2800, "sale_price": 2400},
    )
    listing = await request(client, seller, "GET", "/seller/products")
    assert len(listing["data"]) == 2
    await request(
        client,
        seller,
        "PUT",
        f"/seller/products/{pid}/images/order",
        json={"image_ids": [str(i.id) for i in reversed(images)]},
    )
    await request(client, seller, "PUT", f"/seller/products/{pid}/images/{images[1].id}/primary")
    await request(client, seller, "DELETE", f"/seller/products/{pid}/images/{images[0].id}", 204)
    await request(
        client,
        market.admin,
        "POST",
        f"/admin/products/{pid}/hide",
        json={"reason": "Review listing"},
    )
    await request(client, market.buyer, "GET", f"/products/{pid}", 404)
    await request(client, market.admin, "POST", f"/admin/products/{pid}/unhide")
    await request(
        client,
        market.admin,
        "GET",
        f"/admin/products?seller_id={market.seller.id}&admin_hidden=false",
    )
    await request(client, seller, "POST", f"/seller/products/{pid}/unpublish")
    await request(client, seller, "DELETE", f"/seller/products/{pid}", 204)
    await request(client, seller, "GET", f"/seller/products/{pid}", 404)


async def test_notifications_delivery_preferences_and_jobs(db, market, monkeypatch):

    from test_marketplace_regressions import guest_payload

    from app.core import database
    from app.core.config import settings
    from app.integrations import resend_client
    from app.models.notification import EmailLog
    from app.models.order import Order
    from app.models.wallet import Payout
    from app.schemas.notification import BroadcastRequest, UpdatePreferencesRequest
    from app.services.notification_service import NotificationService
    from app.services.order_service import OrderService
    from app.tasks import notification_tasks

    monkeypatch.setattr(
        resend_client.asyncio, "to_thread", AsyncMock(return_value={"id": "email-receipt"})
    )
    monkeypatch.setattr(settings, "RESEND_API_KEY", "re_test_only")
    context = AsyncMock()
    context.__aenter__.return_value = db
    monkeypatch.setattr(database, "AsyncSessionLocal", lambda: context)
    service = NotificationService(db)
    prefs = await service.get_preferences(market.buyer.id)
    assert prefs.promotions_email is True
    prefs = await service.update_preferences(
        market.buyer.id, UpdatePreferencesRequest(promotions_email=False)
    )
    assert prefs.promotions_email is False
    prefs = await service.update_preferences(
        market.buyer.id, UpdatePreferencesRequest(order_updates_push=False)
    )
    assert prefs.order_updates_push is False
    created = await OrderService(db).create_guest_order(guest_payload(market))
    order = await db.get(Order, created.order_id)
    order.user_id = market.buyer.id
    await db.commit()
    await notification_tasks.send_order_confirmation({}, str(order.id))
    log = await db.scalar(select(EmailLog))
    assert log.status == "sent" and log.resend_id == "email-receipt"
    await notification_tasks.send_order_status_update({}, str(order.id), "shipped")
    await notification_tasks.notify_seller_decision({}, str(market.seller.id), True)
    await notification_tasks.notify_seller_decision(
        {}, str(market.seller.id), False, "Incomplete application"
    )
    payout = Payout(
        seller_id=market.seller.id,
        amount=500,
        payment_method="bank_transfer",
        payment_detail="Test bank",
    )
    db.add(payout)
    await db.commit()
    await notification_tasks.send_payout_notification({}, str(payout.id), "completed")
    await notification_tasks.broadcast_notification(
        {}, [str(market.buyer.id)], "Announcement", "Test body", None, "test-broadcast"
    )
    notifications = await service.list_notifications(market.buyer.id)
    assert notifications.total == 3
    assert await service.mark_read(notifications.data[0].id, market.buyer.id)
    assert await service.mark_all_read(market.buyer.id) == 2
    assert (await service.list_notifications(market.buyer.id, unread_only=True)).unread_count == 0
    assert (await service.get_email_log(recipient_email=market.buyer.email))["total"] == 1
    pool = AsyncMock()
    import arq

    monkeypatch.setattr(arq, "create_pool", AsyncMock(return_value=pool))
    for audience, count in [("all", 3), ("customers", 1), ("sellers", 1)]:
        broadcast = await service.broadcast(
            BroadcastRequest(audience=audience, title="Notice", body="Release test notice"),
            market.admin.id,
        )
        assert broadcast.recipient_count == count
    assert pool.enqueue_job.await_count == 3


async def test_user_repository_state_changes_and_invalid_fields(db, market):
    from app.repositories.user_repo import UserRepository

    repo = UserRepository

    assert await repo.count(db) == 3
    assert len(await repo.list_all(db, limit=2)) == 2
    assert await repo.exists(db, email=market.buyer.email)
    assert (await repo.get_by_field(db, "email", market.buyer.email)).id == market.buyer.id
    with pytest.raises(AttributeError):
        await repo.get_by_field(db, "not_a_field", "x")
    await repo.update(db, market.buyer, first_name="Updated")
    with pytest.raises(AttributeError):
        await repo.update(db, market.buyer, missing_field="value")
    assert await repo.bulk_update(db, {"id": market.buyer.id}, {"last_name": "Khan"}) == 1
    assert (await repo.get_for_update(db, market.buyer.id)).first_name == "Updated"
    await repo.soft_delete(db, market.buyer)
    assert await repo.get_by_id(db, market.buyer.id) is None
    assert await repo.count(db) == 2
    assert await repo.count(db, include_deleted=True) == 3
    assert await repo.get_by_field(db, "email", market.buyer.email) is None
    assert len(await repo.list_all(db)) == 2
    await repo.restore(db, market.buyer)
    assert await repo.get_by_id(db, market.buyer.id) is market.buyer


async def test_cart_customer_order_and_cancellation(db, market, isolated_redis):
    from test_marketplace_regressions import ADDRESS

    from app.schemas.order import AddToCartRequest, CancelOrderRequest, CreateOrderRequest
    from app.services.cart_service import CartService
    from app.services.order_service import OrderService

    cart = CartService(db, isolated_redis)
    added = await cart.add_item(
        market.buyer.id, AddToCartRequest(variant_id=market.variant.id, quantity=1)
    )
    assert len(added.items) == 1
    await cart.update_item(market.buyer.id, market.variant.id, 2)
    assert (await cart.get_raw_items(market.buyer.id))[market.variant.id] == 2
    await cart.remove_item(market.buyer.id, market.variant.id)
    assert not (await cart.get_cart(market.buyer.id)).items
    await cart.sync(market.buyer.id, [{"variant_id": str(market.variant.id), "quantity": 2}])
    orders = OrderService(db, isolated_redis)
    created = await orders.create_order(
        market.buyer.id, CreateOrderRequest(shipping_address=ADDRESS, payment_method="cod")
    )
    assert (await orders.get_customer_orders(market.buyer.id)).pagination.total == 1
    detail = await orders.get_order(created.order_id, market.buyer.id)
    assert detail.total == 2600
    assert (
        await orders.get_order_by_number(created.order_number, user_id=market.buyer.id)
    ).id == created.order_id
    seller_orders = await orders.get_seller_orders(market.seller.id)
    assert seller_orders["pagination"]["total"] == 1
    await orders.get_seller_order_detail(market.seller.id, seller_orders["data"][0]["id"])
    await orders.cancel_order(
        created.order_id, market.buyer.id, CancelOrderRequest(reason="Changed my mind")
    )
    await db.refresh(market.inventory)
    assert market.inventory.reserved == 0


async def test_admin_seller_bank_and_cod_management(db, market):
    from test_marketplace_regressions import guest_payload

    from app.models.seller import SellerStatus
    from app.schemas.seller import CreateBankAccountRequest, SellerProfileUpdateRequest
    from app.services.admin_service import AdminService
    from app.services.order_service import OrderService
    from app.services.seller_service import SellerService

    service = SellerService(db)
    account = await service.add_bank_account(
        market.seller_user.id,
        CreateBankAccountRequest(
            bank_name="Test Bank",
            account_title="Test Brand",
            account_number="1234567890",
            is_default=True,
        ),
    )
    assert len(await service.list_bank_accounts(market.seller_user.id)) == 1
    await service.delete_bank_account(market.seller_user.id, account.id)
    assert await service.list_bank_accounts(market.seller_user.id) == []
    profile = await service.update_profile(
        market.seller_user.id, SellerProfileUpdateRequest(description="Updated brand description")
    )
    assert profile.description == "Updated brand description"
    await service.update_logo(market.seller_user.id, "https://example.test/logo.webp")
    admin = AdminService(db)
    assert (await admin.get_seller(market.seller.id)).brand_name == "Test Brand"
    await admin.suspend_seller(market.seller.id, market.admin.id, "Test suspension")
    await db.refresh(market.product)
    assert market.product.admin_hidden
    await admin.reinstate_seller(market.seller.id, market.admin.id)
    await db.refresh(market.product)
    assert not market.product.admin_hidden
    created = await OrderService(db).create_guest_order(guest_payload(market))
    queue = await admin.list_cod_queue()
    assert len(queue) == 1 and queue[0].order_id == created.order_id
    await admin.cancel_cod(created.order_id, market.admin.id, "Customer unavailable")
    assert await admin.list_cod_queue() == []
    await db.refresh(market.inventory)
    assert market.inventory.reserved == 0
    market.seller.status = SellerStatus.pending_approval
    await db.commit()
    await admin.reject_seller(market.seller.id, market.admin.id, "Missing paperwork")
    await db.refresh(market.seller)
    assert market.seller.status == SellerStatus.rejected


async def test_return_rejection_dispute_and_resolution(db, market):
    from test_marketplace_regressions import guest_payload

    from app.models.order import Order, OrderItem, OrderStatus, SellerOrder, SellerOrderStatus
    from app.schemas.return_ import (
        AddDisputeMessageRequest,
        AdminReturnActionRequest,
        CreateReturnRequest,
        OpenDisputeRequest,
        ResolveDisputeRequest,
    )
    from app.services.order_service import OrderService
    from app.services.return_service import ReturnService

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
    assert (await service.list_returns(market.buyer.id)).total == 1
    assert (await service.get_return(returned.id, market.buyer.id)).status == "requested"
    assert (await service.admin_list_returns(status="requested")).total == 1
    await service.reject_return(
        returned.id, market.admin.id, AdminReturnActionRequest(admin_note="Need more information")
    )
    dispute = await service.open_dispute(
        returned.id, market.buyer.id, OpenDisputeRequest(message="Please reconsider this return")
    )
    assert len(dispute.messages) == 1
    message = await service.add_message(
        returned.id, market.buyer.id, AddDisputeMessageRequest(body="Additional details")
    )
    assert message.body == "Additional details"
    assert len((await service.get_dispute(returned.id, market.buyer.id)).messages) == 2
    assert (await service.admin_list_disputes())["total"] == 1
    resolved = await service.resolve_dispute(
        dispute.id,
        market.admin.id,
        ResolveDisputeRequest(
            in_favor_of="customer", resolution_note="Evidence supports the customer"
        ),
    )
    assert resolved.status == "resolved_customer"
    with pytest.raises(BusinessRuleError):
        await service.add_message(
            returned.id, market.buyer.id, AddDisputeMessageRequest(body="Too late")
        )


async def test_storefront_category_visibility_brand_and_banner_lifecycle(client, db, market):
    from app.models.product import Category
    from app.services.admin_service import AdminService

    parent = Category(name="Clothing", slug="clothing", is_active=True)
    hidden = Category(name="Hidden", slug="hidden", is_active=False)
    db.add_all([parent, hidden])
    await db.flush()
    child = Category(name="Shirts", slug="shirts", is_active=True, parent_id=parent.id)
    orphan = Category(name="Hidden child", slug="hidden-child", is_active=True, parent_id=hidden.id)
    db.add_all([child, orphan])
    await db.commit()
    categories = await request(client, market.buyer, "GET", "/categories")
    assert {row["slug"] for row in categories["data"]} == {"clothing", "shirts"}
    brands = await request(client, market.buyer, "GET", "/brands?q=Test")
    assert brands["pagination"]["total"] == 1
    assert (await request(client, market.buyer, "GET", "/brands/test-brand"))[
        "brand_name"
    ] == "Test Brand"
    assert (
        len((await request(client, market.buyer, "GET", "/brands/test-brand/products"))["data"])
        == 1
    )
    await request(client, market.buyer, "GET", "/brands/absent", 404)
    banner = await AdminService(db).create_banner(
        title="Launch",
        image_url="https://example.test/hero.webp",
        position="homepage_hero",
        is_active=True,
    )
    public = await request(client, market.buyer, "GET", "/content/banners?position=homepage_hero")
    assert len(public) == 1
    updated = await request(
        client,
        market.admin,
        "PATCH",
        f"/admin/content/banners/{banner.id}",
        json={"title": "Updated", "link_url": "/products", "is_active": False},
    )
    assert updated["title"] == "Updated"
    assert await request(client, market.buyer, "GET", "/content/banners") == []
    assert len(await request(client, market.admin, "GET", "/admin/content/banners")) == 1
    await request(client, market.admin, "DELETE", f"/admin/content/banners/{banner.id}", 204)


async def test_readonly_admin_seller_endpoints_use_real_queries(client, market):
    admin_paths = [
        "/admin/dashboard",
        "/admin/orders",
        "/admin/analytics/platform",
        "/admin/analytics/revenue",
        "/admin/analytics/top-sellers",
        "/admin/analytics/cohort",
        "/admin/analytics/payment-methods",
        "/admin/analytics/cities",
        "/admin/analytics/conversion",
        "/admin/analytics/search-queries",
    ]
    from main import app

    paths = app.openapi()["paths"]
    for path in admin_paths:
        # Keep this list tied to actual routes; missing endpoints fail the test.
        assert "/api/v1" + path in paths
        await request(client, market.admin, "GET", path)


async def test_browser_auth_cookie_refresh_reset_and_logout(client, db, monkeypatch):
    import arq

    pool = AsyncMock()
    monkeypatch.setattr(arq, "create_pool", AsyncMock(return_value=pool))
    payload = {
        "first_name": "Browser",
        "last_name": "Tester",
        "email": "browser@example.com",
        "password": "BrowserPass123",
    }
    registered = await client.post("/api/v1/auth/register", json=payload)
    assert registered.status_code == 201, registered.text
    verify_token = pool.enqueue_job.call_args.args[3]
    verified = await client.get("/api/v1/auth/verify-email", params={"token": verify_token})
    assert verified.status_code == 200, verified.text
    assert "HttpOnly" in verified.headers["set-cookie"]
    access = {"Authorization": "Bearer " + verified.json()["access_token"]}
    assert (await client.get("/api/v1/auth/me", headers=access)).status_code == 200
    refreshed = await client.post("/api/v1/auth/refresh")
    assert refreshed.status_code == 200, refreshed.text
    logged = await client.post(
        "/api/v1/auth/login", json={"email": payload["email"], "password": payload["password"]}
    )
    assert logged.status_code == 200, logged.text
    access = {"Authorization": "Bearer " + logged.json()["access_token"]}
    assert (await client.post("/api/v1/auth/logout", headers=access)).status_code == 200
    assert (await client.post("/api/v1/auth/refresh")).status_code == 401
    forgotten = await client.post("/api/v1/auth/forgot-password", json={"email": payload["email"]})
    assert forgotten.status_code == 200
    reset_token = pool.enqueue_job.call_args.args[3]
    reset = await client.post(
        "/api/v1/auth/reset-password",
        json={"token": reset_token, "new_password": "ResetBrowser456"},
    )
    assert reset.status_code == 200, reset.text


async def test_google_signed_identity_callback_and_replay(db, isolated_redis, monkeypatch):
    import json
    from unittest.mock import MagicMock
    from urllib.parse import parse_qs, urlparse

    from fastapi import Request, Response
    from jose import jwk, jwt

    from app.core.config import settings
    from app.core.exceptions import AuthenticationError
    from app.services import google_oauth as google

    monkeypatch.setattr(settings, "GOOGLE_CLIENT_ID", "test-client")
    monkeypatch.setattr(settings, "GOOGLE_CLIENT_SECRET", "test-secret")
    for _attempt in range(2):
        started = await google.start_google_login(Response())
        state = parse_qs(urlparse(started["authorization_url"]).query)["state"][0]
        flow = json.loads(await isolated_redis.get("google-state:" + state))
        claims = {
            "sub": "google-test-id",
            "email": "google@example.com",
            "email_verified": True,
            "given_name": "Google",
            "family_name": "Tester",
            "iss": "https://accounts.google.com",
            "aud": "test-client",
            "nonce": flow["nonce"],
            "iat": int(datetime.now(UTC).timestamp()),
            "exp": int((datetime.now(UTC) + timedelta(minutes=5)).timestamp()),
        }
        signed = jwt.encode(
            claims, settings.JWT_PRIVATE_KEY, algorithm="RS256", headers={"kid": "test-key"}
        )
        key = jwk.construct(settings.JWT_PUBLIC_KEY, algorithm="RS256").to_dict()
        key["kid"] = "test-key"
        transport = AsyncMock()
        transport.__aenter__.return_value = transport
        transport.post.return_value = MagicMock(
            json=lambda signed=signed: {"id_token": signed}, raise_for_status=lambda: None
        )
        transport.get.return_value = MagicMock(
            json=lambda key=key: {"keys": [key]}, raise_for_status=lambda: None
        )
        monkeypatch.setattr(
            google.httpx, "AsyncClient", lambda transport=transport, **kwargs: transport
        )
        req = Request(
            {
                "type": "http",
                "query_string": f"state={state}&code=test-code".encode(),
                "headers": [(b"cookie", f"{google.STATE_COOKIE}={state}".encode())],
            }
        )
        response = await google.finish_google_login(req, db)
        assert response.status_code == 303
        assert "access_token" not in response.headers["location"]
        assert response.headers["cache-control"] == "no-store"
        with pytest.raises(AuthenticationError):
            await google.finish_google_login(req, db)
    assert (
        await db.scalar(select(func.count(User.id)).where(User.google_id == "google-test-id")) == 1
    )
