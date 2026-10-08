"""Behavioural regression tests using a disposable PostgreSQL schema."""

from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy import func, select

from app.core.exceptions import (
    AuthenticationError,
    BusinessRuleError,
    NotFoundError,
    PermissionDeniedError,
)
from app.models.coupon import Coupon, DiscountType
from app.models.order import Order, OrderStatus, SellerOrder
from app.models.payment import Payment, PaymentStatus
from app.models.product import Product, ProductImage, ProductInventory, ProductVariant, SizeType
from app.models.seller import Seller, SellerStatus, SellerWallet
from app.models.user import User, UserRole
from app.schemas.order import CreateGuestOrderRequest, CreateOrderRequest, UpdateSellerOrderRequest
from app.schemas.payment import RefundRequest
from app.services.order_service import OrderService
from app.services.payment_service import PaymentService
from app.services.product_service import ProductService

pytestmark = pytest.mark.integration

ADDRESS = dict(
    recipient_name="Test Customer",
    phone="03001234567",
    street="12 Test Street",
    city="Lahore",
    province="Punjab",
)


@pytest.fixture
async def market(db):
    buyer = User(
        email="buyer@example.com",
        password_hash="test-not-a-live-password",
        role=UserRole.customer,
        has_verified_email=True,
    )
    seller_user = User(
        email="seller@example.com",
        password_hash="test-only",
        role=UserRole.seller,
        has_verified_email=True,
    )
    admin = User(
        email="admin@example.com",
        password_hash="test-only",
        role=UserRole.admin,
        has_verified_email=True,
    )
    db.add_all([buyer, seller_user, admin])
    await db.flush()
    seller = Seller(
        user_id=seller_user.id,
        brand_name="Test Brand",
        slug="test-brand",
        status=SellerStatus.active,
        total_slots=50,
    )
    db.add(seller)
    await db.flush()
    db.add(SellerWallet(seller_id=seller.id))
    product = Product(
        seller_id=seller.id,
        name="Linen Shirt",
        slug="linen-shirt",
        price=Decimal("1500"),
        sale_price=Decimal("1200"),
        is_published=True,
    )
    db.add(product)
    await db.flush()
    variant = ProductVariant(
        product_id=product.id,
        sku="TEST-M",
        size_type=SizeType.alpha,
        size_value="M",
        colour="Ivory",
    )
    db.add(variant)
    await db.flush()
    inventory = ProductInventory(variant_id=variant.id, stock=8, reserved=0)
    db.add(inventory)
    db.add(
        ProductImage(product_id=product.id, url="https://example.test/image.webp", is_primary=True)
    )
    await db.commit()
    return SimpleNamespace(
        buyer=buyer,
        seller=seller,
        seller_user=seller_user,
        admin=admin,
        product=product,
        variant=variant,
        inventory=inventory,
    )


def guest_payload(market, **overrides):
    return CreateGuestOrderRequest(
        shipping_address=ADDRESS,
        payment_method="cod",
        guest_email="guest@example.com",
        guest_name="Guest Customer",
        guest_phone="03001234567",
        items=[{"variant_id": market.variant.id, "quantity": 2}],
        **overrides,
    )


async def test_guest_checkout_payment_idempotence_and_access(db, market):
    created = await OrderService(db).create_guest_order(guest_payload(market))
    assert created.total == Decimal("2600.00")  # sale price, two units, shipping
    assert created.guest_token
    service = PaymentService(db)
    first = await service.initiate(created.order_id, guest_token=created.guest_token)
    second = await service.initiate(created.order_id, guest_token=created.guest_token)
    assert first.payment_id == second.payment_id
    assert await db.scalar(select(func.count(Payment.id))) == 1
    assert (
        await service.get_status(created.order_id, guest_token=created.guest_token)
    ).amount == Decimal("2600.00")
    for token in (None, "forged"):
        with pytest.raises((NotFoundError, AuthenticationError)):
            await service.get_status(created.order_id, guest_token=token)
    with pytest.raises(NotFoundError):
        await service.get_status(created.order_id, user_id=market.buyer.id)
    await db.refresh(market.inventory)
    assert market.inventory.reserved == 2


async def test_coupon_changes_persisted_order_and_seller_totals(db, market, isolated_redis):
    coupon = Coupon(
        code="SAVE",
        discount_type=DiscountType.percentage,
        discount_value=Decimal("12.5"),
        is_active=True,
        max_uses_per_customer=1,
    )
    db.add(coupon)
    await db.commit()
    await isolated_redis.hset(f"cart:{market.buyer.id}", str(market.variant.id), 1)
    created = await OrderService(db, isolated_redis).create_order(
        market.buyer.id,
        CreateOrderRequest(shipping_address=ADDRESS, payment_method="cod", coupon_code="SAVE"),
    )
    order = await db.get(Order, created.order_id)
    seller_order = await db.scalar(select(SellerOrder).where(SellerOrder.order_id == order.id))
    assert order.discount_amount == Decimal("150.00")
    assert order.coupon_id == coupon.id
    assert order.total == Decimal("1250.00")
    assert seller_order.subtotal == Decimal("1050.00")
    assert not await isolated_redis.hgetall(f"cart:{market.buyer.id}")


async def test_hidden_products_cannot_be_ordered(db, market):
    market.product.admin_hidden = True
    await db.commit()
    with pytest.raises(BusinessRuleError):
        await OrderService(db).create_guest_order(guest_payload(market))
    with pytest.raises(NotFoundError):
        await ProductService(db).get_variants(market.product.id)


async def test_invalid_fulfilment_and_unpaid_delivery_are_rejected(db, market):
    created = await OrderService(db).create_guest_order(guest_payload(market))
    so = await db.scalar(select(SellerOrder).where(SellerOrder.order_id == created.order_id))
    with pytest.raises(BusinessRuleError):
        await OrderService(db).update_seller_order_status(
            market.seller.id, so.id, UpdateSellerOrderRequest(status="delivered")
        )
    with pytest.raises(BusinessRuleError):
        await OrderService(db).update_seller_order_status(
            market.seller.id, so.id, UpdateSellerOrderRequest(status="processing")
        )


async def test_fulfilment_deducts_inventory_once_and_collection_settles(db, market):
    created = await OrderService(db).create_guest_order(guest_payload(market))
    payment = await PaymentService(db).initiate(created.order_id, guest_token=created.guest_token)
    from app.services.admin_service import AdminService

    await AdminService(db).verify_cod(created.order_id, market.admin.id)
    so = await db.scalar(select(SellerOrder).where(SellerOrder.order_id == created.order_id))
    service = OrderService(db)
    await service.update_seller_order_status(
        market.seller.id, so.id, UpdateSellerOrderRequest(status="processing")
    )
    shipped = UpdateSellerOrderRequest(
        status="shipped", tracking_number="TRACK123", courier_name="Test courier"
    )
    await service.update_seller_order_status(market.seller.id, so.id, shipped)
    await service.update_seller_order_status(market.seller.id, so.id, shipped)
    await db.refresh(market.inventory)
    assert (market.inventory.stock, market.inventory.reserved) == (6, 0)
    await service.update_seller_order_status(
        market.seller.id, so.id, UpdateSellerOrderRequest(status="delivered")
    )
    await PaymentService(db).record_cod_collection(
        payment.payment_id, market.admin.id, "COD-TRANSFER-001"
    )
    await PaymentService(db).record_cod_collection(
        payment.payment_id, market.admin.id, "COD-TRANSFER-001"
    )
    wallet = await db.scalar(select(SellerWallet).where(SellerWallet.seller_id == market.seller.id))
    assert wallet.pending_balance == Decimal("2040.00")


async def test_refund_request_is_pending_capped_and_idempotent(db, market):
    created = await OrderService(db).create_guest_order(guest_payload(market))
    initiated = await PaymentService(db).initiate(created.order_id, guest_token=created.guest_token)
    payment = await db.get(Payment, initiated.payment_id)
    payment.status = PaymentStatus.completed
    await db.commit()
    service = PaymentService(db)
    request = RefundRequest(
        amount="1000.25", reason="Returned item", idempotency_key="refund-request-001"
    )
    refund = await service.refund(payment.id, market.admin.id, request)
    repeated = await service.refund(payment.id, market.admin.id, request)
    assert refund.status == "pending" and refund.refund_id == repeated.refund_id
    assert payment.status == PaymentStatus.completed
    with pytest.raises(BusinessRuleError):
        await service.refund(
            payment.id, market.admin.id, RefundRequest(amount=2000, reason="Too large refund")
        )
    confirmed = await service.confirm_refund(refund.refund_id, market.admin.id, "BANK-TRANSFER-001")
    assert confirmed.status == "completed"
    assert payment.status == PaymentStatus.completed  # partial refund


async def test_seller_cannot_edit_another_brand(db, market):
    with pytest.raises(PermissionDeniedError):
        await ProductService(db)._require_owned(uuid4(), market.product.id)


async def test_all_analytics_queries_run(db, market):
    from app.services.analytics_service import AdminAnalyticsService, SellerAnalyticsService

    admin = AdminAnalyticsService(db)
    seller = SellerAnalyticsService(db)
    await admin.get_platform_analytics("30d")
    await admin.get_platform_revenue("30d", "day")
    await admin.get_top_sellers("30d", 10)
    await admin.get_cohort(3)
    await admin.get_payment_methods("30d")
    await admin.get_cities("30d", 10)
    await admin.get_conversion("30d")
    await admin.get_search_queries("30d", 10)
    await seller.get_overview(market.seller.id, "30d")
    await seller.get_revenue_series(market.seller.id, "30d", "day")
    await seller.get_top_products(market.seller.id, "30d", "revenue", 10)
    await seller.get_inventory_health(market.seller.id)


async def test_payment_callback_amount_signature_and_replay(db, market, monkeypatch):
    from unittest.mock import AsyncMock

    import app.services.payment_service as module
    from app.integrations.payfast import PayFastClient
    from app.models.order import PaymentMethod

    created = await OrderService(db).create_guest_order(guest_payload(market))
    order = await db.get(Order, created.order_id)
    order.payment_method, order.status = PaymentMethod.payfast, OrderStatus.pending_payment
    await db.commit()
    gateway = PayFastClient("test-merchant", "test-secret")
    monkeypatch.setattr(gateway, "get_checkout_token", AsyncMock(return_value="test-token"))
    monkeypatch.setattr(module, "_build_payfast", lambda: gateway)
    service = PaymentService(db)
    initialized = await service.initiate(order.id, guest_token=created.guest_token)
    assert initialized.payfast_payload["TXNAMT"] == "2600.00"
    assert initialized.payfast_payload["TOKEN"] == "test-token"
    data = dict(
        basket_id=str(order.id),
        txnamt="2600.00",
        currency_code="PKR",
        err_code="000",
        err_msg="Approved",
        transaction_id="test-txn-001",
    )
    with pytest.raises(BusinessRuleError):
        await service.handle_payfast_callback({**data, "validation_hash": "forged"})
    wrong = {**data, "txnamt": "26.00"}
    wrong["validation_hash"] = gateway.callback_hash(basket_id=str(order.id), error_code="000")
    with pytest.raises(BusinessRuleError):
        await service.handle_payfast_callback(wrong)
    data["validation_hash"] = gateway.callback_hash(basket_id=str(order.id), error_code="000")
    await service.handle_payfast_callback(data)
    assert order.status == OrderStatus.payment_confirmed
    order.status = OrderStatus.delivered
    await db.commit()
    await service.handle_payfast_callback(data)
    assert order.status == OrderStatus.delivered
    failed = {**data, "err_code": "101", "err_msg": "Declined"}
    failed["validation_hash"] = gateway.callback_hash(basket_id=str(order.id), error_code="101")
    await service.handle_payfast_callback(failed)
    assert (await db.get(Payment, initialized.payment_id)).status == PaymentStatus.completed


async def test_payfast_status_reconciliation_is_verified_and_idempotent(db, market, monkeypatch):
    from unittest.mock import AsyncMock

    import app.services.payment_service as module
    from app.integrations.payfast import PayFastClient
    from app.models.order import PaymentMethod

    created = await OrderService(db).create_guest_order(guest_payload(market))
    order = await db.get(Order, created.order_id)
    order.payment_method, order.status = PaymentMethod.payfast, OrderStatus.pending_payment
    await db.commit()
    gateway = PayFastClient("test-merchant", "test-secret", api_base_url="https://api.test")
    monkeypatch.setattr(gateway, "get_checkout_token", AsyncMock(return_value="test-token"))
    monkeypatch.setattr(module, "_build_payfast", lambda: gateway)
    service = PaymentService(db)
    initialized = await service.initiate(
        order.id, guest_token=created.guest_token, customer_ip="203.0.113.7"
    )
    status = {
        "status_code": "00",
        "status_msg": "Approved",
        "basket_id": str(order.id),
        "transaction_id": "reconciled-txn-1",
    }
    monkeypatch.setattr(gateway, "check_status", AsyncMock(return_value=status))

    first = await service.reconcile_payfast(order.id)
    second = await service.reconcile_payfast(order.id)

    payment = await db.get(Payment, initialized.payment_id)
    await db.refresh(order)
    assert first.matched is True
    assert first.local_status == "completed"
    assert second.detail == "Payment was already reconciled"
    assert payment.gateway_reference == "reconciled-txn-1"
    assert order.status == OrderStatus.payment_confirmed


async def test_payfast_status_reconciliation_rejects_mismatched_basket(db, market, monkeypatch):
    from unittest.mock import AsyncMock

    import app.services.payment_service as module
    from app.integrations.payfast import PayFastClient
    from app.models.order import PaymentMethod

    created = await OrderService(db).create_guest_order(guest_payload(market))
    order = await db.get(Order, created.order_id)
    order.payment_method, order.status = PaymentMethod.payfast, OrderStatus.pending_payment
    await db.commit()
    gateway = PayFastClient("test-merchant", "test-secret", api_base_url="https://api.test")
    monkeypatch.setattr(gateway, "get_checkout_token", AsyncMock(return_value="test-token"))
    monkeypatch.setattr(module, "_build_payfast", lambda: gateway)
    service = PaymentService(db)
    initialized = await service.initiate(
        order.id, guest_token=created.guest_token, customer_ip="203.0.113.7"
    )
    monkeypatch.setattr(
        gateway,
        "check_status",
        AsyncMock(
            return_value={
                "status_code": "00",
                "basket_id": str(uuid4()),
                "transaction_id": "wrong-order-txn",
            }
        ),
    )

    result = await service.reconcile_payfast(order.id)

    payment = await db.get(Payment, initialized.payment_id)
    assert result.matched is False
    assert payment.status == PaymentStatus.pending
    assert payment.gateway_reference is None


async def test_roles_deleted_accounts_and_password_version(db, market):
    from app.api.deps import get_current_user_payload, require_seller
    from app.core.exceptions import TokenInvalidError
    from app.core.security import create_access_token

    token, _ = create_access_token(subject=str(market.buyer.id), role="customer")
    assert (await get_current_user_payload(token, db))["sub"] == str(market.buyer.id)
    other, _ = create_access_token(subject=str(market.buyer.id), role="admin")
    with pytest.raises(TokenInvalidError):
        await get_current_user_payload(other, db)
    market.buyer.auth_version += 1
    await db.commit()
    with pytest.raises(TokenInvalidError):
        await get_current_user_payload(token, db)
    fresh, _ = create_access_token(
        subject=str(market.buyer.id), role="customer", extra_claims={"ver": 1}
    )
    market.buyer.deleted_at = datetime.now(UTC)
    await db.commit()
    with pytest.raises(TokenInvalidError):
        await get_current_user_payload(fresh, db)
    with pytest.raises(PermissionDeniedError):
        await require_seller(db, {"role": "admin", "sub": str(market.admin.id)})


async def test_product_controls_price_cursor_and_visibility(db, market):
    from app.schemas.product import CreateVariantRequest, UpdateProductRequest, UpdateVariantRequest

    service = ProductService(db)
    detail = await service.add_variant(
        market.seller.id,
        market.product.id,
        CreateVariantRequest(size_type="alpha", size_value="L", colour="Black", stock=3),
    )
    assert len(detail.variants) == 2
    variant = next(v for v in detail.variants if v.id != market.variant.id)
    updated = await service.update_variant(
        market.seller.id, market.product.id, variant.id, UpdateVariantRequest(price_override=999)
    )
    assert updated.price == 999
    assert (
        await service.update_product(
            market.seller.id, market.product.id, UpdateProductRequest(sale_price=None)
        )
    ).sale_price is None
    db.add(
        Product(
            seller_id=market.seller.id,
            name="Other Shirt",
            slug="other-shirt",
            price=Decimal("2000"),
            is_published=True,
        )
    )
    await db.commit()
    first = await service.get_catalogue(sort="price_asc", limit=1)
    second = await service.get_catalogue(
        sort="price_asc", limit=1, cursor=first.pagination.next_cursor
    )
    assert first.data[0].id != second.data[0].id
    await service.set_hidden(market.product.id, True)
    assert len((await service.get_catalogue()).data) == 1


async def test_analytics_uses_recorded_events_and_cohorts(db, market, isolated_redis):
    from app.schemas.order import AddToCartRequest
    from app.services.analytics_service import AdminAnalyticsService
    from app.services.cart_service import CartService

    await ProductService(db).get_product_detail(market.product.id)
    await ProductService(db).get_catalogue(q="linen")
    await CartService(db, isolated_redis).add_item(
        market.buyer.id, AddToCartRequest(variant_id=market.variant.id, quantity=1)
    )
    created = await OrderService(db, isolated_redis).create_order(
        market.buyer.id, CreateOrderRequest(shipping_address=ADDRESS, payment_method="cod")
    )
    (await db.get(Order, created.order_id)).status = OrderStatus.delivered
    await db.commit()
    service = AdminAnalyticsService(db)
    conversion = await service.get_conversion("30d")
    assert (conversion.product_views, conversion.add_to_cart, conversion.orders_completed) == (
        1,
        1,
        1,
    )
    assert (await service.get_search_queries("30d", 10)).data[0].query == "linen"
    cohort = (await service.get_cohort(3)).data[0]
    assert cohort.cohort_size == 1 and cohort.retention[0] == 100


async def test_review_moderation_and_single_vote(db, market):
    from app.api.v1.admin.reviews import ModerateReviewRequest, moderate_review
    from app.models.review import Review
    from app.schemas.user import CreateReviewRequest
    from app.services.customer_service import CustomerService

    service = CustomerService(db)
    review = await service.create_review(
        market.buyer.id,
        CreateReviewRequest(
            product_id=market.product.id, rating=4, title="Good shirt", body="Good quality and fit"
        ),
    )
    await moderate_review(
        review.id, ModerateReviewRequest(status="approved"), db, {"sub": str(market.admin.id)}
    )
    await service.vote_review(market.admin.id, review.id, True)
    await service.vote_review(market.admin.id, review.id, True)
    assert (await db.get(Review, review.id)).helpful_count == 1
    await db.refresh(market.product)
    assert market.product.review_count == 1 and market.product.avg_rating == 4
    await service.delete_review(market.buyer.id, review.id)
    await db.refresh(market.product)
    assert market.product.review_count == 0


async def test_guest_token_scoped_to_one_order(db, market):
    first = await OrderService(db).create_guest_order(guest_payload(market))
    second = await OrderService(db).create_guest_order(guest_payload(market))
    with pytest.raises(NotFoundError):
        await PaymentService(db).initiate(second.order_id, guest_token=first.guest_token)
    with pytest.raises(AuthenticationError):
        await OrderService(db).get_order_by_number(first.order_number, "guest@example.com")


async def test_seller_registration_payment_and_dashboard(db, market):
    from app.api.v1.admin.brands import record_registration_payment
    from app.schemas.admin import SellerRegistrationPaymentRequest
    from app.schemas.seller import SellerRegistrationRequest
    from app.services.admin_service import AdminService
    from app.services.seller_service import SellerService

    created = await SellerService(db).register(
        SellerRegistrationRequest(
            email="new-brand@example.com",
            password="TestPassword123",
            first_name="Brand",
            brand_name="Second Test Brand",
            description="Test clothing brand description",
            return_policy="Returns accepted within the agreed window",
            whatsapp_number="03001234567",
            extra_slots=2,
        )
    )
    assert created.amount_due == 5100
    seller = await db.get(Seller, created.seller_id)
    request = SellerRegistrationPaymentRequest(amount=5100, reference="BANK-TEST-001")
    await record_registration_payment(seller.id, request, db, {"sub": str(market.admin.id)})
    await record_registration_payment(seller.id, request, db, {"sub": str(market.admin.id)})
    await AdminService(db).approve_seller(seller.id, market.admin.id)
    dashboard = await SellerService(db).get_dashboard(seller.user_id, "month")
    assert dashboard.slots_available == 52


async def test_wallet_withdrawal_rejection_and_transfer_receipt(db, market):
    from app.models.seller import SellerBankAccount
    from app.models.wallet import WalletTransaction, WalletTxType
    from app.schemas.wallet import WithdrawalRequest
    from app.services.wallet_service import WalletService

    wallet = await db.scalar(select(SellerWallet).where(SellerWallet.seller_id == market.seller.id))
    wallet.available_balance = Decimal("1000.75")
    bank = SellerBankAccount(
        seller_id=market.seller.id,
        bank_name="Test Bank",
        account_title="Test Brand",
        account_number="0000000000",
    )
    db.add(bank)
    await db.commit()
    service = WalletService(db)
    payload = WithdrawalRequest(amount=Decimal("500.25"), bank_account_id=bank.id)
    first = await service.request_withdrawal(market.seller.id, payload)
    assert first.amount == Decimal("500.25")
    assert (await service.get_summary(market.seller.id)).available_balance == Decimal("500.50")
    with pytest.raises(BusinessRuleError):
        await service.request_withdrawal(
            market.seller.id, WithdrawalRequest(amount=600, bank_account_id=bank.id)
        )
    await service.admin_reject_payout(first.id, market.admin.id, "Invalid beneficiary details")
    with pytest.raises(BusinessRuleError):
        await service.admin_reject_payout(first.id, market.admin.id, "Repeated action")
    assert (await service.get_summary(market.seller.id)).available_balance == Decimal("1000.75")
    assert (
        await db.scalar(
            select(func.count(WalletTransaction.id)).where(
                WalletTransaction.type == WalletTxType.credit_adjustment
            )
        )
        == 1
    )
    second = await service.request_withdrawal(market.seller.id, payload)
    with pytest.raises(BusinessRuleError):
        await service.admin_complete_payout(second.id, market.admin.id, "transfer-1")
    await service.admin_approve_payout(second.id, market.admin.id)
    complete = await service.admin_complete_payout(second.id, market.admin.id, "transfer-1")
    replay = await service.admin_complete_payout(second.id, market.admin.id, "transfer-1")
    assert complete.status == replay.status == "completed"
    assert complete.transfer_reference == "transfer-1"
    assert (
        next(
            p for p in (await service.get_payouts(market.seller.id)).data if p.id == second.id
        ).transfer_reference
        == "transfer-1"
    )
    assert (await service.get_summary(market.seller.id)).available_balance == Decimal("500.50")


async def test_recorded_slot_revenue_and_dashboard_period(db, market):
    from datetime import timedelta

    from app.schemas.seller import SlotPurchaseRequest
    from app.services.admin_service import AdminService
    from app.services.analytics_service import AdminAnalyticsService
    from app.services.slot_service import SlotService

    wallet = await db.scalar(select(SellerWallet).where(SellerWallet.seller_id == market.seller.id))
    wallet.available_balance = Decimal("250.50")
    market.seller.registration_paid_at = datetime.now(UTC) - timedelta(days=50)
    market.seller.registration_fee = Decimal("5000")
    await db.commit()
    purchased = await SlotService(db).purchase_slots(
        market.seller_user.id, SlotPurchaseRequest(quantity=2, payment_method="wallet")
    )
    assert purchased.amount_charged == 100
    assert (await AdminService(db).get_dashboard("month")).slot_revenue == 100
    assert (await AdminService(db).get_dashboard("quarter")).slot_revenue == 5100
    assert (await AdminAnalyticsService(db).get_platform_analytics("30d")).slot_revenue == 100
    with pytest.raises(Exception) as exc:
        await SlotService(db).purchase_slots(
            market.seller_user.id, SlotPurchaseRequest(quantity=4, payment_method="wallet")
        )
    assert exc.type.__name__ == "InsufficientBalanceError"
    assert (await AdminService(db).get_dashboard("month")).slot_revenue == 100


async def test_http_guest_checkout_and_browser_token_header(db, market):
    import httpx
    from main import app

    from app.api.deps import get_db
    from app.core.config import settings

    async def override_db():
        yield db

    app.dependency_overrides[get_db] = override_db
    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://testserver"
        ) as client:
            preflight = await client.options(
                "/api/v1/orders/test",
                headers={
                    "Origin": settings.ALLOWED_ORIGINS[0],
                    "Access-Control-Request-Method": "GET",
                    "Access-Control-Request-Headers": "X-Guest-Token",
                },
            )
            assert preflight.status_code == 200
            created = await client.post(
                "/api/v1/orders/guest", json=guest_payload(market).model_dump(mode="json")
            )
            assert created.status_code == 201, created.text
            data = created.json()
            order_path = f"/api/v1/orders/{data['order_id']}"
            denied = await client.get(order_path)
            assert denied.status_code == 401
            allowed = await client.get(order_path, headers={"X-Guest-Token": data["guest_token"]})
            assert allowed.status_code == 200, allowed.text
            assert Decimal(allowed.json()["total"]) == Decimal("2600.00")
    finally:
        app.dependency_overrides.pop(get_db, None)


async def test_runtime_settings_drive_pricing_checkout_and_commission(db, market, isolated_redis):
    from app.models.wallet import CommissionLedger
    from app.services.admin_service import AdminService
    from app.services.cart_service import CartService
    from app.services.commission_service import CommissionService
    from app.services.slot_service import SlotService

    admin = AdminService(db)
    await admin.update_settings(
        {
            "commission_rate": 0.2,
            "registration_fee": 6000,
            "extra_slot_price": 75,
            "standard_shipping_fee": 300,
            "free_shipping_threshold": 3000,
        },
        market.admin.id,
    )
    pricing = await SlotService(db).get_pricing(2)
    assert pricing.total_cost == 6150
    await isolated_redis.hset(f"cart:{market.buyer.id}", str(market.variant.id), 2)
    cart = await CartService(db, isolated_redis).get_cart(market.buyer.id)
    assert cart.total == 2700
    created = await OrderService(db).create_guest_order(guest_payload(market))
    assert created.total == cart.total
    seller_order = await db.scalar(
        select(SellerOrder).where(SellerOrder.order_id == created.order_id)
    )
    from app.models.order import SellerOrderStatus

    seller_order.status = SellerOrderStatus.delivered
    db.add(
        Payment(
            order_id=created.order_id,
            method="cod",
            status=PaymentStatus.completed,
            amount=created.total,
        )
    )
    await db.commit()
    await CommissionService(db).settle(seller_order.id)
    ledger = await db.scalar(
        select(CommissionLedger).where(CommissionLedger.seller_order_id == seller_order.id)
    )
    assert ledger.commission_rate == Decimal("0.20")
    assert ledger.commission_amount == Decimal("480.00")


@pytest.mark.parametrize(
    "extra_slots,amount_due,expected_status",
    [
        (0, Decimal("0"), SellerStatus.pending_approval),
        (2, Decimal("150"), SellerStatus.pending_payment),
    ],
)
async def test_zero_registration_fee_still_charges_optional_slots(
    db, market, extra_slots, amount_due, expected_status
):
    from app.schemas.seller import SellerRegistrationRequest
    from app.services.admin_service import AdminService
    from app.services.seller_service import SellerService

    admin = AdminService(db)
    await admin.update_settings({"registration_fee": 0, "extra_slot_price": 75}, market.admin.id)
    created = await SellerService(db).register(
        SellerRegistrationRequest(
            email="fee-waiver@example.com",
            password="TestPassword123",
            first_name="Brand",
            brand_name="Fee Waiver Brand",
            description="Test clothing brand description",
            return_policy="Returns accepted within the agreed window",
            whatsapp_number="03001234567",
            extra_slots=extra_slots,
        )
    )
    seller = await db.get(Seller, created.seller_id)
    assert created.amount_due == amount_due
    assert seller.status == expected_status
    assert seller.registration_paid_at is None  # Never invent a payment receipt.
    if not amount_due:
        await admin.approve_seller(seller.id, market.admin.id)
        assert (await SellerService(db).get_profile(seller.user_id)).status == "active"
    else:
        with pytest.raises(BusinessRuleError):
            await admin.approve_seller(seller.id, market.admin.id)
    assert (await admin.get_dashboard("month")).slot_revenue == 0


def actor_headers(actor):
    from app.core.security import create_access_token

    token, _ = create_access_token(
        subject=str(actor.id), role=actor.role.value, extra_claims={"ver": actor.auth_version}
    )
    return {"Authorization": f"Bearer {token}"}


async def test_http_runtime_pricing_and_payment_due_snapshot(client, db, market):
    from app.api.v1.admin.brands import record_registration_payment
    from app.models.admin import SystemSetting
    from app.schemas.admin import SellerRegistrationPaymentRequest
    from app.schemas.seller import SellerRegistrationRequest
    from app.services.admin_service import AdminService
    from app.services.seller_service import SellerService

    service = AdminService(db)
    await service.update_settings(
        {"registration_fee": 6000, "extra_slot_price": 75}, market.admin.id
    )
    # Keep an ORM row loaded: subsequent updates must still be visible in this session.
    loaded = await db.get(SystemSetting, "extra_slot_price")
    await service.update_settings({"extra_slot_price": 80}, market.admin.id)
    quote = await client.get("/api/v1/seller/register/slot-price?extra_slots=2")
    assert quote.status_code == 200, quote.text
    assert quote.json()["total_cost"] == 6160
    assert loaded.value == "80"
    registered = await SellerService(db).register(
        SellerRegistrationRequest(
            email="quote@example.com",
            password="TestPassword123",
            first_name="Quote",
            brand_name="Quoted Brand",
            description="Clothes with a fixed registration quote",
            return_policy="Returns accepted within the agreed window",
            whatsapp_number="03001234567",
            extra_slots=2,
        )
    )
    seller = await db.get(Seller, registered.seller_id)
    await service.update_settings({"registration_fee": 7000}, market.admin.id)
    assert (await SellerService(db).get_profile(seller.user_id)).registration_amount_due == 6160
    await record_registration_payment(
        seller.id,
        SellerRegistrationPaymentRequest(amount=6160, reference="registration-transfer"),
        db,
        {"sub": str(market.admin.id)},
    )
    assert (await SellerService(db).get_profile(seller.user_id)).registration_amount_due == 0


async def test_http_wallet_precision_roles_and_duplicate_payout_actions(client, db, market):
    from app.models.seller import SellerBankAccount
    from app.models.wallet import Payout, WalletTransaction, WalletTxType

    wallet = await db.scalar(select(SellerWallet).where(SellerWallet.seller_id == market.seller.id))
    wallet.available_balance = Decimal("1000.75")
    account = SellerBankAccount(
        seller_id=market.seller.id,
        bank_name="Bank",
        account_title="Brand",
        account_number="0000000000",
    )
    db.add(account)
    await db.commit()
    seller_headers = actor_headers(market.seller_user)
    admin_headers = actor_headers(market.admin)
    payload = {"amount": "500.25", "bank_account_id": str(account.id)}
    base = "/api/v1"
    denied = await client.post(
        base + "/seller/wallet/withdraw", headers=actor_headers(market.buyer), json=payload
    )
    assert denied.status_code == 403
    foreign = await client.post(
        base + "/seller/wallet/withdraw",
        headers=seller_headers,
        json={**payload, "bank_account_id": str(uuid4())},
    )
    assert foreign.status_code == 404
    first = await client.post(
        base + "/seller/wallet/withdraw", headers=seller_headers, json=payload
    )
    assert first.status_code == 201, first.text
    assert first.json()["amount"] == "500.25"
    first_id = first.json()["id"]
    rejected_path = base + f"/admin/wallet/payouts/{first_id}/reject"
    denied = await client.post(rejected_path, headers=seller_headers, json={"admin_note": "Reject"})
    assert denied.status_code == 403
    for status in (200, 422):
        rejected = await client.post(
            rejected_path, headers=admin_headers, json={"admin_note": "Wrong account details"}
        )
        assert rejected.status_code == status, rejected.text
    second = await client.post(
        base + "/seller/wallet/withdraw", headers=seller_headers, json=payload
    )
    second_id = second.json()["id"]
    path = base + f"/admin/wallet/payouts/{second_id}"
    approved = await client.post(path + "/approve", headers=admin_headers, json={})
    assert approved.status_code == 200
    for _ in range(2):
        completed = await client.post(
            path + "/complete", headers=admin_headers, json={"reference": "bank-receipt-123"}
        )
        assert completed.status_code == 200, completed.text
        assert completed.json()["transfer_reference"] == "bank-receipt-123"
    conflict = await client.post(
        path + "/complete", headers=admin_headers, json={"reference": "different-receipt"}
    )
    assert conflict.status_code == 422
    cannot_reject = await client.post(
        path + "/reject", headers=admin_headers, json={"admin_note": "Too late"}
    )
    assert cannot_reject.status_code == 422
    wallet_response = await client.get(base + "/seller/wallet", headers=seller_headers)
    assert wallet_response.json()["available_balance"] == "500.50"
    history = await client.get(base + "/seller/wallet/payouts", headers=seller_headers)
    assert type(history.json()["total"]) is int
    assert history.json()["total"] == 2
    transactions = await client.get(base + "/seller/wallet/transactions", headers=seller_headers)
    assert type(transactions.json()["total"]) is int
    assert transactions.json()["total"] == 3
    assert await db.scalar(select(func.count(Payout.id))) == 2
    assert (
        await db.scalar(
            select(func.count(WalletTransaction.id)).where(
                WalletTransaction.type == WalletTxType.credit_adjustment
            )
        )
        == 1
    )


async def test_dashboard_periods_precision_and_filtered_order_totals(client, db, market):
    from datetime import timedelta

    from app.models.order import SellerOrderStatus
    from app.models.wallet import CommissionLedger
    from app.services.admin_service import AdminService
    from app.services.seller_service import SellerService

    current = await OrderService(db).create_guest_order(guest_payload(market))
    old = await OrderService(db).create_guest_order(guest_payload(market))
    now = datetime.now(UTC)
    yesterday = now.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(minutes=1)
    for result, when in ((current, now), (old, yesterday)):
        order = await db.get(Order, result.order_id)
        order.created_at = when
        order.status = OrderStatus.delivered
        order.total = Decimal("2600.50")
        seller_order = await db.scalar(select(SellerOrder).where(SellerOrder.order_id == order.id))
        seller_order.status = SellerOrderStatus.delivered
        seller_order.created_at = when
        seller_order.subtotal = Decimal("2400.50")
        db.add(
            CommissionLedger(
                seller_order_id=seller_order.id,
                seller_id=market.seller.id,
                gross_amount=Decimal("2400.50"),
                commission_rate=Decimal("0.15"),
                commission_amount=Decimal("360.08"),
                seller_amount=Decimal("2040.42"),
                settled_at=when,
            )
        )
    wallet = await db.scalar(select(SellerWallet).where(SellerWallet.seller_id == market.seller.id))
    wallet.available_balance = Decimal("20.75")
    await db.commit()
    admin = AdminService(db)
    assert (await admin.get_dashboard("today")).total_gmv == Decimal("2600.50")
    assert (await admin.get_dashboard("today")).platform_revenue == Decimal("360.08")
    seller_today = await SellerService(db).get_dashboard(market.seller_user.id, "today")
    assert seller_today.net_earnings == Decimal("2040.42")
    assert seller_today.available_balance == Decimal("20.75")
    assert seller_today.order_count == 1
    month = await admin.get_dashboard("month")
    assert month.total_gmv == Decimal("5201.00") and month.total_orders == 2
    delivered = await admin.list_orders(status="delivered", per_page=1)
    assert delivered.total == 2 and delivered.totals.total_gmv == Decimal("5201.00")
    assert delivered.totals.total_commission == Decimal("720.16")
    assert delivered.data[0].commission == Decimal("360.08")
    absent = await admin.list_orders(status="cancelled")
    assert (
        absent.total == 0 and absent.totals.total_gmv == 0 and absent.totals.total_commission == 0
    )
    sellers = await admin.list_sellers()
    assert sellers.data[0].total_gmv == Decimal("4801.00")
    assert type(sellers.model_dump(mode="json")["total"]) is int
    response = await client.get(
        "/api/v1/admin/orders?payment_method=payfast", headers=actor_headers(market.admin)
    )
    assert response.status_code == 200 and response.json()["total"] == 0
    bad_filter = await client.get(
        "/api/v1/admin/orders?status=not-real", headers=actor_headers(market.admin)
    )
    assert bad_filter.status_code == 422


# ── Task 2: Refund and return accounting ───────────────────────────────────────


async def _fulfil_and_collect_cod(db, market, isolated_redis):
    """
    Shared helper: logged-in user COD order → fully fulfilled → COD collected.
    Returns (order, so, payment, wallet) with commission settled into pending_balance.
    """
    from app.services.admin_service import AdminService

    await isolated_redis.hset(f"cart:{market.buyer.id}", str(market.variant.id), 2)
    created = await OrderService(db, isolated_redis).create_order(
        market.buyer.id,
        CreateOrderRequest(shipping_address=ADDRESS, payment_method="cod"),
    )
    payment_init = await PaymentService(db).initiate(created.order_id, user_id=market.buyer.id)
    await AdminService(db).verify_cod(created.order_id, market.admin.id)
    so = await db.scalar(select(SellerOrder).where(SellerOrder.order_id == created.order_id))
    svc = OrderService(db)
    await svc.update_seller_order_status(
        market.seller.id, so.id, UpdateSellerOrderRequest(status="processing")
    )
    await svc.update_seller_order_status(
        market.seller.id,
        so.id,
        UpdateSellerOrderRequest(status="shipped", tracking_number="TRK01", courier_name="TCS"),
    )
    await svc.update_seller_order_status(
        market.seller.id, so.id, UpdateSellerOrderRequest(status="delivered")
    )
    await PaymentService(db).record_cod_collection(
        payment_init.payment_id, market.admin.id, "COD-TEST-001"
    )

    order = await db.get(Order, created.order_id)
    payment = await db.get(Payment, payment_init.payment_id)
    wallet = await db.scalar(select(SellerWallet).where(SellerWallet.seller_id == market.seller.id))
    return order, so, payment, wallet


async def _do_return_and_process(db, market, order, so):
    """Create return → approve → receive → process_refund. Returns refund_id."""
    from uuid import UUID

    from app.models.order import OrderItem
    from app.schemas.return_ import AdminReturnActionRequest, CreateReturnRequest
    from app.services.return_service import ReturnService

    order_item = await db.scalar(select(OrderItem).where(OrderItem.order_id == order.id))

    ret = await ReturnService(db).request_return(
        market.buyer.id,
        CreateReturnRequest(
            seller_order_id=so.id,
            reason="Item arrived damaged and not as described in the listing",
            items=[{"order_item_id": str(order_item.id), "quantity": 1}],
        ),
    )
    await ReturnService(db).approve_return(ret.id, market.admin.id, AdminReturnActionRequest())
    await ReturnService(db).mark_received(ret.id, market.admin.id, AdminReturnActionRequest())
    result = await ReturnService(db).process_refund(
        ret.id, market.admin.id, AdminReturnActionRequest(admin_note="Approved")
    )
    return UUID(result["refund_id"])


async def test_return_refund_reverses_seller_pending_balance(db, market, isolated_redis):
    """
    Full happy path: COD collected → commission in pending → return 1 of 2 units
    → confirm refund → pending_balance reduced proportionally.

    Order: 2 units × 1200 = 2400 subtotal, 200 shipping = 2600 total.
    Commission: 2400 × 0.15 = 360 → seller earns 2040 in pending.
    Refund: 1 unit = 1200 (no discount).
    Expected debit: 2040 × (1200 / 2400) = 1020.
    Expected pending after: 2040 − 1020 = 1020.
    """
    from app.models.wallet import WalletTransaction, WalletTxType

    order, so, payment, wallet = await _fulfil_and_collect_cod(db, market, isolated_redis)
    assert wallet.pending_balance == Decimal("2040.00")

    refund_id = await _do_return_and_process(db, market, order, so)
    await PaymentService(db).confirm_refund(refund_id, market.admin.id, "BANK-REF-001")

    await db.refresh(wallet)
    assert wallet.pending_balance == Decimal("1020.00")
    assert wallet.available_balance == Decimal("0.00")

    tx = await db.scalar(
        select(WalletTransaction).where(
            WalletTransaction.reference == f"return-refund:{refund_id}",
            WalletTransaction.type == WalletTxType.debit_adjustment,
            WalletTransaction.seller_order_id == so.id,
        )
    )
    assert tx is not None
    assert tx.amount == Decimal("1020.00")

    # Stock: 8 original − 2 sold + 1 returned = 7.
    await db.refresh(market.inventory)
    assert market.inventory.stock == 7


async def test_return_refund_reverses_seller_available_balance(db, market, isolated_redis):
    """
    When funds have been released from the hold period (released_at set), the
    reversal targets available_balance, not pending_balance.
    """
    from app.models.wallet import CommissionLedger, WalletTransaction, WalletTxType

    order, so, payment, wallet = await _fulfil_and_collect_cod(db, market, isolated_redis)
    assert wallet.pending_balance == Decimal("2040.00")

    # Simulate hold release: funds moved from pending to available.
    ledger = await db.scalar(
        select(CommissionLedger).where(CommissionLedger.seller_order_id == so.id)
    )
    from datetime import UTC, datetime

    ledger.released_at = datetime.now(UTC)
    wallet.available_balance = wallet.pending_balance
    wallet.pending_balance = Decimal("0.00")
    await db.commit()

    refund_id = await _do_return_and_process(db, market, order, so)
    await PaymentService(db).confirm_refund(refund_id, market.admin.id, "BANK-REF-002")

    await db.refresh(wallet)
    assert wallet.pending_balance == Decimal("0.00")
    assert wallet.available_balance == Decimal("1020.00")  # 2040 − 1020

    tx = await db.scalar(
        select(WalletTransaction).where(
            WalletTransaction.reference == f"return-refund:{refund_id}",
            WalletTransaction.type == WalletTxType.debit_adjustment,
        )
    )
    assert tx.amount == Decimal("1020.00")


async def test_return_refund_idempotent_no_double_reversal(db, market, isolated_redis):
    """
    Calling confirm_refund twice with the same reference must not:
    - Debit the wallet a second time.
    - Restock inventory a second time.
    - Create a second WalletTransaction.
    """
    from sqlalchemy import func

    from app.models.wallet import WalletTransaction, WalletTxType

    order, so, payment, wallet = await _fulfil_and_collect_cod(db, market, isolated_redis)
    refund_id = await _do_return_and_process(db, market, order, so)

    await PaymentService(db).confirm_refund(refund_id, market.admin.id, "BANK-REF-003")
    await PaymentService(db).confirm_refund(refund_id, market.admin.id, "BANK-REF-003")

    await db.refresh(wallet)
    assert wallet.pending_balance == Decimal("1020.00")  # touched exactly once

    tx_count = await db.scalar(
        select(func.count(WalletTransaction.id)).where(
            WalletTransaction.reference == f"return-refund:{refund_id}",
            WalletTransaction.type == WalletTxType.debit_adjustment,
        )
    )
    assert tx_count == 1

    await db.refresh(market.inventory)
    assert market.inventory.stock == 7  # 8 − 2 + 1, restocked once


async def test_refund_before_settlement_reduces_gross_at_settle_time(db, market, isolated_redis):
    """
    Edge case: admin confirms a direct refund before COD is collected.
    When settle() runs, the pre-confirmed refund reduces gross_amount so the
    seller is never over-credited.

    Order: 2400 subtotal.  Direct refund of 1200 confirmed before COD.
    Expected gross at settle: 2400 − 1200 = 1200.
    Expected seller_amount: 1200 × 0.85 = 1020.
    """
    from app.models.wallet import CommissionLedger
    from app.services.admin_service import AdminService

    await isolated_redis.hset(f"cart:{market.buyer.id}", str(market.variant.id), 2)
    created = await OrderService(db, isolated_redis).create_order(
        market.buyer.id,
        CreateOrderRequest(shipping_address=ADDRESS, payment_method="cod"),
    )
    payment_init = await PaymentService(db).initiate(created.order_id, user_id=market.buyer.id)
    await AdminService(db).verify_cod(created.order_id, market.admin.id)
    so = await db.scalar(select(SellerOrder).where(SellerOrder.order_id == created.order_id))
    svc = OrderService(db)
    await svc.update_seller_order_status(
        market.seller.id, so.id, UpdateSellerOrderRequest(status="processing")
    )
    await svc.update_seller_order_status(
        market.seller.id,
        so.id,
        UpdateSellerOrderRequest(status="shipped", tracking_number="TRK02", courier_name="TCS"),
    )
    await svc.update_seller_order_status(
        market.seller.id, so.id, UpdateSellerOrderRequest(status="delivered")
    )
    # Order is now delivered but COD not yet collected → no commission ledger yet.

    # Admin creates and immediately confirms a direct refund of 1200.
    payment = await db.get(Payment, payment_init.payment_id)
    from app.models.payment import Refund

    refund = Refund(
        payment_id=payment.id,
        amount=Decimal("1200.00"),
        reason="Quality issue — refund before COD",
        processed_by=market.admin.id,
        idempotency_key="pre-cod-refund-001",
    )
    db.add(refund)
    # Confirm the recorded refund before collection; leave COD pending so the
    # collection operation can record the later receipt and settle earnings.
    await db.commit()

    await PaymentService(db).confirm_refund(refund.id, market.admin.id, "BANK-PRE-001")
    # No CommissionLedger exists yet → _reverse_one is a no-op.

    # Now admin collects COD → settle() sees the pre-confirmed refund.
    await PaymentService(db).record_cod_collection(payment.id, market.admin.id, "COD-POST-001")

    ledger = await db.scalar(
        select(CommissionLedger).where(CommissionLedger.seller_order_id == so.id)
    )
    assert ledger.gross_amount == Decimal("1200.00")  # 2400 − 1200
    assert ledger.seller_amount == Decimal("1020.00")  # 1200 × 0.85
    assert ledger.commission_amount == Decimal("180.00")  # 1200 × 0.15

    wallet = await db.scalar(select(SellerWallet).where(SellerWallet.seller_id == market.seller.id))
    assert wallet.pending_balance == Decimal("1020.00")


async def test_direct_refund_prorates_across_two_sellers(db, market):
    """
    Multi-brand order with two settled sellers.
    A direct admin refund (no return) is split proportionally across both
    seller ledgers.

    Seller 1 subtotal: 1200  (share = 60%)
    Seller 2 subtotal:  800  (share = 40%)
    Total subtotal:    2000

    Direct refund: 1000

    Seller 1 proportional: 1000 × 0.60 = 600 → debit = 1020 × (600/1200) = 510
    Seller 2 proportional: 1000 × 0.40 = 400 → debit =  680 × (400/ 800) = 340
    """
    from app.models.order import PaymentMethod, SellerOrderStatus
    from app.models.order import SellerOrder as SO
    from app.models.payment import Payment as Pmt
    from app.models.payment import PaymentStatus as PS
    from app.models.payment import Refund
    from app.models.seller import Seller, SellerStatus
    from app.models.user import User, UserRole
    from app.models.wallet import CommissionLedger, WalletTransaction, WalletTxType
    from app.services.commission_service import CommissionService

    # ── Second seller ────────────────────────────────────────────────────────
    u2 = User(
        email="seller2-mb@test.com",
        password_hash="x",
        role=UserRole.seller,
        has_verified_email=True,
    )
    db.add(u2)
    await db.flush()
    s2 = Seller(
        user_id=u2.id,
        brand_name="Brand Two MB",
        slug="brand-two-mb",
        status=SellerStatus.active,
        total_slots=50,
    )
    db.add(s2)
    await db.flush()
    wallet2 = SellerWallet(seller_id=s2.id)
    db.add(wallet2)

    # ── Minimal multi-brand order ────────────────────────────────────────────
    order = Order(
        order_number="TEST-MB-002",
        user_id=market.buyer.id,
        status=OrderStatus.delivered,
        subtotal=Decimal("2000"),
        discount_amount=Decimal("0"),
        shipping_fee=Decimal("200"),
        total=Decimal("2200"),
        payment_method=PaymentMethod.cod,
    )
    db.add(order)
    await db.flush()

    so1 = SO(
        order_id=order.id,
        seller_id=market.seller.id,
        subtotal=Decimal("1200"),
        status=SellerOrderStatus.delivered,
    )
    so2 = SO(
        order_id=order.id,
        seller_id=s2.id,
        subtotal=Decimal("800"),
        status=SellerOrderStatus.delivered,
    )
    db.add_all([so1, so2])
    pmt = Pmt(
        order_id=order.id, method="cod", status=PS.completed, amount=Decimal("2200"), currency="PKR"
    )
    db.add(pmt)
    await db.flush()

    cl1 = CommissionLedger(
        seller_order_id=so1.id,
        seller_id=market.seller.id,
        gross_amount=Decimal("1200"),
        commission_rate=Decimal("0.15"),
        commission_amount=Decimal("180"),
        seller_amount=Decimal("1020"),
    )
    cl2 = CommissionLedger(
        seller_order_id=so2.id,
        seller_id=s2.id,
        gross_amount=Decimal("800"),
        commission_rate=Decimal("0.15"),
        commission_amount=Decimal("120"),
        seller_amount=Decimal("680"),
    )
    db.add_all([cl1, cl2])

    wallet1 = await db.scalar(
        select(SellerWallet).where(SellerWallet.seller_id == market.seller.id)
    )
    wallet1.pending_balance = Decimal("1020")
    wallet2.pending_balance = Decimal("680")
    await db.commit()

    # ── Direct admin refund of 1000 (no return) ─────────────────────────────
    refund = Refund(
        payment_id=pmt.id,
        amount=Decimal("1000"),
        reason="Multi-brand quality complaint",
        processed_by=market.admin.id,
    )
    db.add(refund)
    await db.commit()

    await CommissionService(db).reverse_for_refund(
        refund.id,
        order_id=order.id,
        refund_amount=Decimal("1000"),
        commit=True,
    )

    await db.refresh(wallet1)
    await db.refresh(wallet2)
    assert wallet1.pending_balance == Decimal("510.00")  # 1020 − 510
    assert wallet2.pending_balance == Decimal("340.00")  # 680  − 340

    txs = (
        (
            await db.execute(
                select(WalletTransaction).where(
                    WalletTransaction.reference.like(f"return-refund:{refund.id}%"),
                    WalletTransaction.type == WalletTxType.debit_adjustment,
                )
            )
        )
        .scalars()
        .all()
    )
    assert len(txs) == 2


async def test_seller_already_withdrawn_platform_absorbs_shortfall(db, market, isolated_redis):
    """
    If the seller has already withdrawn all funds (available_balance = 0,
    pending_balance = 0), the refund reversal floors at zero and logs the
    full intended debit amount for platform reconciliation.
    """
    from datetime import UTC, datetime

    from app.models.wallet import CommissionLedger, WalletTransaction, WalletTxType

    order, so, payment, wallet = await _fulfil_and_collect_cod(db, market, isolated_redis)
    assert wallet.pending_balance == Decimal("2040.00")

    # Simulate: hold released AND seller fully withdrew.
    ledger = await db.scalar(
        select(CommissionLedger).where(CommissionLedger.seller_order_id == so.id)
    )
    ledger.released_at = datetime.now(UTC)
    wallet.pending_balance = Decimal("0.00")
    wallet.available_balance = Decimal("0.00")  # fully withdrawn
    await db.commit()

    refund_id = await _do_return_and_process(db, market, order, so)
    await PaymentService(db).confirm_refund(refund_id, market.admin.id, "BANK-REF-ABSORBED")

    await db.refresh(wallet)
    assert wallet.pending_balance == Decimal("0.00")  # cannot go negative
    assert wallet.available_balance == Decimal("0.00")  # cannot go negative

    # Full intended debit still logged for platform reconciliation.
    tx = await db.scalar(
        select(WalletTransaction).where(
            WalletTransaction.reference == f"return-refund:{refund_id}",
            WalletTransaction.type == WalletTxType.debit_adjustment,
        )
    )
    assert tx is not None
    assert tx.amount == Decimal("1020.00")  # intended, not actual (for audit)
