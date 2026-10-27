"""Security HTTP checks using disposable PostgreSQL and the shared fakeredis fixture.

Collection is unconditional. The shared database fixture skips execution only when
TEST_DATABASE_URL is absent; no deployment accounts or provider credentials are used.
"""

import base64
import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from sqlalchemy import func, select

from app.core.config import settings
from app.core.security import create_access_token, revoke_token
from app.integrations.payfast import PayFastClient
from app.models.order import Order
from app.models.payment import Payment, PaymentCallback, PaymentStatus
from app.models.product import Product, ProductImage, ProductInventory, ProductVariant, SizeType
from app.models.seller import Seller, SellerStatus, SellerWallet
from app.models.user import User, UserRole
from app.schemas.order import CreateGuestOrderRequest
from app.services.order_service import OrderService

pytestmark = [pytest.mark.security, pytest.mark.integration]
ADDRESS = {
    "recipient_name": "Synthetic Customer",
    "phone": "03001234567",
    "street": "12 Synthetic Street",
    "city": "Lahore",
    "province": "Punjab",
}


@pytest.fixture(autouse=True)
def offline_services(monkeypatch):
    pool = AsyncMock()
    monkeypatch.setattr("arq.create_pool", AsyncMock(return_value=pool))
    transport = AsyncMock(side_effect=AssertionError("Provider transport must stay offline"))
    monkeypatch.setattr(PayFastClient, "_post_form", transport)
    monkeypatch.setattr(PayFastClient, "_get", transport)
    return SimpleNamespace(pool=pool, transport=transport)


@pytest.fixture
async def accounts(db):
    users = {
        name: User(
            email=f"security-{name}@example.com",
            password_hash="synthetic-only",
            role=role,
            has_verified_email=True,
        )
        for name, role in [
            ("buyer", UserRole.customer),
            ("seller", UserRole.seller),
            ("other", UserRole.seller),
            ("admin", UserRole.admin),
        ]
    }
    db.add_all(users.values())
    await db.flush()
    owner = Seller(
        user_id=users["seller"].id,
        brand_name="Security Brand",
        slug="security-brand",
        status=SellerStatus.active,
        total_slots=50,
    )
    other = Seller(
        user_id=users["other"].id,
        brand_name="Other Brand",
        slug="security-other",
        status=SellerStatus.active,
        total_slots=50,
    )
    db.add_all([owner, other])
    await db.flush()
    db.add_all(
        [
            SellerWallet(seller_id=owner.id, available_balance=Decimal("1000")),
            SellerWallet(seller_id=other.id, available_balance=Decimal("9000")),
        ]
    )
    product = Product(
        seller_id=owner.id,
        name="Security shirt",
        slug="security-shirt",
        price=Decimal("1500"),
        is_published=True,
    )
    db.add(product)
    await db.flush()
    variant = ProductVariant(
        product_id=product.id, sku="SEC-M", size_type=SizeType.alpha, size_value="M", colour="Ivory"
    )
    db.add(variant)
    await db.flush()
    db.add(ProductInventory(variant_id=variant.id, stock=8))
    db.add(
        ProductImage(
            product_id=product.id, url="https://example.test/security.webp", is_primary=True
        )
    )
    await db.commit()
    return SimpleNamespace(**users, owner=owner, foreign=other, product=product, variant=variant)


def token_for(user, **claims):
    return create_access_token(
        subject=str(user.id),
        role=user.role.value,
        extra_claims={"ver": user.auth_version, **claims},
    )[0]


def headers(user, **claims):
    return {"Authorization": f"Bearer {token_for(user, **claims)}"}


def assert_error(response, status, code):
    assert response.status_code == status, response.text
    assert response.json()["error"]["code"] == code


async def snapshot(db):
    return {
        model.__tablename__: sorted(
            tuple(map(str, row))
            for row in (await db.execute(select(*model.__table__.columns))).all()
        )
        for model in (
            Product,
            ProductVariant,
            ProductImage,
            ProductInventory,
            SellerWallet,
            Order,
            Payment,
        )
    }


@pytest.mark.parametrize(
    "path,limit,window,success,code",
    [
        ("/auth/login", 5, 300, 401, "INVALID_CREDENTIALS"),
        ("/auth/register", 3, 3600, 201, None),
        ("/auth/forgot-password", 3, 3600, 200, None),
    ],
)
async def test_auth_rate_limit_exact_threshold(
    client, db, isolated_redis, monkeypatch, offline_services, path, limit, window, success, code
):
    monkeypatch.setattr(settings, "TRUSTED_PROXY_IPS", [])
    for index in range(limit):
        payload = {"email": f"security-rate-{index}@example.com"}
        if not path.endswith("/forgot-password"):
            payload["password"] = "StrongPassword123"
        if path.endswith("/register"):
            payload.update(first_name="Synthetic", last_name="Customer")
        response = await client.post("/api/v1" + path, json=payload)
        assert response.status_code == success, response.text
        if code:
            assert response.json()["error"]["code"] == code
        assert response.headers["X-RateLimit-Limit"] == str(limit)
        assert response.headers["X-RateLimit-Remaining"] == str(limit - index - 1)
    payload = {**payload, "email": "blocked@example.com"}
    blocked = await client.post("/api/v1" + path, json=payload)
    assert_error(blocked, 429, "RATE_LIMITED")
    assert blocked.headers["Retry-After"] == str(window)
    assert blocked.headers["X-RateLimit-Remaining"] == "0"
    spoofed = await client.post(
        "/api/v1" + path, json=payload, headers={"X-Forwarded-For": "192.0.2.99"}
    )
    assert_error(spoofed, 429, "RATE_LIMITED")
    keys = await isolated_redis.keys(f"drip:rl:POST:/api/v1{path}:*")
    assert len(keys) == 1
    assert 0 < await isolated_redis.ttl(keys[0]) <= window
    count = await db.scalar(select(func.count(User.id)))
    assert count == (3 if path.endswith("/register") else 0)
    assert offline_services.pool.enqueue_job.await_count == (3 if path.endswith("/register") else 0)


async def test_reset_response_does_not_enumerate_accounts(client, accounts, offline_services):
    known = await client.post("/api/v1/auth/forgot-password", json={"email": accounts.buyer.email})
    unknown = await client.post(
        "/api/v1/auth/forgot-password", json={"email": "absent@example.com"}
    )
    assert known.status_code == unknown.status_code == 200
    assert known.json() == unknown.json()
    assert "if an account exists" in known.json()["message"].lower()
    offline_services.pool.enqueue_job.assert_awaited_once()


async def assert_valid_identity(client, user):
    response = await client.get("/api/v1/auth/me", headers=headers(user))
    assert response.status_code == 200, response.text
    assert response.json()["id"] == str(user.id)


async def test_valid_signed_token_reaches_current_user(client, accounts):
    await assert_valid_identity(client, accounts.buyer)


async def test_tampered_signed_payload_is_rejected(client, accounts):
    await assert_valid_identity(client, accounts.buyer)
    head, body, signature = token_for(accounts.buyer).split(".")
    claims = json.loads(base64.urlsafe_b64decode(body + "=" * (-len(body) % 4)))
    claims["role"] = "admin"
    changed = base64.urlsafe_b64encode(json.dumps(claims).encode()).rstrip(b"=").decode()
    response = await client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {head}.{changed}.{signature}"}
    )
    assert_error(response, 401, "TOKEN_INVALID")


async def test_expired_correctly_signed_token_is_rejected(client, accounts):
    await assert_valid_identity(client, accounts.buyer)
    now = datetime.now(UTC)
    expired = token_for(
        accounts.buyer, iat=now - timedelta(minutes=2), exp=now - timedelta(minutes=1)
    )
    response = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {expired}"})
    assert_error(response, 401, "TOKEN_EXPIRED")


@pytest.mark.parametrize("token", ["not-a-jwt", "Bearer", "eyXXXXXXX", "a.b"])
async def test_malformed_token_is_rejected(client, token):
    response = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert_error(response, 401, "TOKEN_INVALID")


async def test_absent_token_is_rejected(client):
    assert_error(await client.get("/api/v1/auth/me"), 401, "UNAUTHORIZED")


@pytest.mark.parametrize(
    "case", ["role", "version", "deleted", "unverified", "revoked", "audience", "issuer"]
)
async def test_invalid_session_cannot_use_signed_token(client, db, accounts, case):
    user = accounts.buyer
    await assert_valid_identity(client, user)
    extra = (
        {"role": "admin"}
        if case == "role"
        else (
            {"aud": "another-client"}
            if case == "audience"
            else {"iss": "another-issuer"}
            if case == "issuer"
            else {}
        )
    )
    token = token_for(user, **extra)
    if case == "version":
        user.auth_version += 1
    elif case == "deleted":
        user.deleted_at = datetime.now(UTC)
    elif case == "unverified":
        user.has_verified_email = False
    elif case == "revoked":
        _, jti = create_access_token(subject=str(user.id), role=user.role.value)
        # Revoke the exact valid token used below, with a known signed jti.
        token = token_for(user, jti=jti)
        await revoke_token(jti, datetime.now(UTC) + timedelta(minutes=15))
    await db.commit()
    response = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert_error(response, 401, "EMAIL_NOT_VERIFIED" if case == "unverified" else "TOKEN_INVALID")


@pytest.mark.parametrize(
    "kind,status,code",
    [
        ("edit", 403, "FORBIDDEN"),
        ("delete", 403, "FORBIDDEN"),
        ("inventory", 404, "NOT_FOUND"),
    ],
)
async def test_foreign_seller_writes_are_rejected_without_mutation(
    client, db, accounts, kind, status, code
):
    owner_read = await client.get(
        f"/api/v1/seller/products/{accounts.product.id}", headers=headers(accounts.seller)
    )
    assert owner_read.status_code == 200, owner_read.text
    before = await snapshot(db)
    path = f"/api/v1/seller/products/{accounts.product.id}"
    if kind == "edit":
        response = await client.put(
            path, headers=headers(accounts.other), json={"name": "Unauthorized edit"}
        )
    elif kind == "delete":
        response = await client.delete(path, headers=headers(accounts.other))
    else:
        response = await client.put(
            f"/api/v1/seller/inventory/{accounts.variant.id}",
            headers=headers(accounts.other),
            json={"stock": 9999},
        )
    assert_error(response, status, code)
    assert await snapshot(db) == before


async def test_wallet_read_uses_authenticated_seller_not_query_id(client, db, accounts):
    before = await snapshot(db)
    for user, other_id, balance in [
        (accounts.seller, accounts.foreign.id, Decimal("1000")),
        (accounts.other, accounts.owner.id, Decimal("9000")),
    ]:
        response = await client.get(
            "/api/v1/seller/wallet", headers=headers(user), params={"seller_id": str(other_id)}
        )
        assert response.status_code == 200, response.text
        assert Decimal(response.json()["available_balance"]) == balance
    assert await snapshot(db) == before


@pytest.mark.parametrize(
    "actor,method,path",
    [
        ("buyer", "GET", "/admin/products"),
        ("buyer", "GET", "/seller/products"),
        ("seller", "GET", "/admin/products"),
        ("seller", "POST", "/admin/wallet/payouts/{id}/approve"),
    ],
)
async def test_wrong_role_is_forbidden_before_resource_lookup(
    client, db, accounts, actor, method, path
):
    for role, control in [("admin", "/admin/products"), ("seller", "/seller/products")]:
        response = await client.get("/api/v1" + control, headers=headers(getattr(accounts, role)))
        assert response.status_code == 200, response.text
    before = await snapshot(db)
    response = await client.request(
        method,
        "/api/v1" + path.format(id=uuid4()),
        headers=headers(getattr(accounts, actor)),
        json={},
    )
    assert_error(response, 403, "FORBIDDEN")
    assert await snapshot(db) == before


async def test_account_order_requires_identity(client, db, accounts):
    before = await snapshot(db)
    response = await client.post(
        "/api/v1/orders", json={"shipping_address": ADDRESS, "payment_method": "cod"}
    )
    assert_error(response, 401, "UNAUTHORIZED")
    assert await snapshot(db) == before


@pytest.fixture
async def online_payment(db, accounts, monkeypatch):
    monkeypatch.setattr(settings, "PAYFAST_ENABLED", True)
    monkeypatch.setattr(settings, "PAYFAST_MERCHANT_ID", "synthetic-merchant")
    monkeypatch.setattr(settings, "PAYFAST_SECURED_KEY", "synthetic-key")
    monkeypatch.setattr(settings, "PAYFAST_IPN_IPS", [])
    created = await OrderService(db).create_guest_order(
        CreateGuestOrderRequest(
            shipping_address=ADDRESS,
            payment_method="payfast",
            guest_email="guest@example.com",
            guest_name="Synthetic Customer",
            guest_phone="03001234567",
            items=[{"variant_id": accounts.variant.id, "quantity": 1}],
        )
    )
    payment = Payment(
        order_id=created.order_id,
        method="payfast",
        amount=created.total,
        status=PaymentStatus.pending,
        currency="PKR",
    )
    db.add(payment)
    await db.commit()
    return payment


def callback_payload(payment, error_code="000"):
    client = PayFastClient("synthetic-merchant", "synthetic-key")
    basket = str(payment.order_id)
    return {
        "basket_id": basket,
        "err_code": error_code,
        "transaction_id": "synthetic-txn",
        "validation_hash": client.callback_hash(basket_id=basket, error_code=error_code),
        "amount": str(payment.amount),
        "currency_code": "PKR",
    }


async def callback_request(client, method, payload, **kwargs):
    if method == "GET":
        return await client.get("/api/v1/payments/callback/payfast", params=payload, **kwargs)
    return await client.post(
        "/api/v1/payments/callback/payfast",
        data=payload,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        **kwargs,
    )


@pytest.mark.parametrize("method", ["GET", "POST"])
@pytest.mark.parametrize("fault", ["bad_hash", "missing_hash", "missing_transaction"])
async def test_invalid_callback_authentication_cannot_change_payment(
    client, db, online_payment, offline_services, method, fault
):
    payload = callback_payload(online_payment)
    if fault == "bad_hash":
        payload["validation_hash"] = "0" * 64
    else:
        payload.pop("validation_hash" if fault == "missing_hash" else "transaction_id")
    before = await snapshot(db)
    response = await callback_request(client, method, payload)
    assert_error(response, 422, "BUSINESS_RULE_VIOLATION")
    assert await snapshot(db) == before
    audits = (await db.scalars(select(PaymentCallback))).all()
    assert len(audits) == 1
    assert audits[0].is_verified is False
    offline_services.transport.assert_not_awaited()


@pytest.mark.parametrize("field,value", [("amount", "0.01"), ("currency_code", "USD")])
async def test_callback_hash_does_not_override_monetary_checks(
    client, db, online_payment, offline_services, field, value
):
    payload = {**callback_payload(online_payment), field: value}
    before = await snapshot(db)
    response = await callback_request(client, "POST", payload)
    assert_error(response, 422, "BUSINESS_RULE_VIOLATION")
    assert await snapshot(db) == before
    audit = (await db.scalars(select(PaymentCallback))).one()
    assert audit.is_verified is False
    offline_services.transport.assert_not_awaited()


@pytest.mark.parametrize("method", ["GET", "POST"])
async def test_valid_failed_callback_control_reaches_verified_handler(
    client, db, online_payment, offline_services, monkeypatch, method
):
    # A signed failure is insufficient: a matching terminal provider result is required.
    payload = callback_payload(online_payment, "101")
    lookup = AsyncMock(return_value={**payload, "status": "FAILED"})
    monkeypatch.setattr(PayFastClient, "check_status", lookup)
    response = await callback_request(client, method, payload)
    assert response.status_code == 200, response.text
    assert response.json() == {"status": "ok"}
    await db.refresh(online_payment)
    assert online_payment.status == PaymentStatus.failed
    audits = (await db.scalars(select(PaymentCallback))).all()
    assert {audit.gateway for audit in audits} == {"payfast", "payfast_reconciliation"}
    assert len(audits) == 2 and all(audit.is_verified for audit in audits)
    lookup.assert_awaited_once()
    assert lookup.await_args.kwargs["basket_id"] == str(online_payment.order_id)
    assert lookup.await_args.kwargs["transaction_id"] == payload["transaction_id"]
    offline_services.transport.assert_not_awaited()


@pytest.mark.parametrize("method", ["GET", "POST"])
@pytest.mark.parametrize("provider_status", ["001", "002"])
async def test_signed_failure_cannot_turn_pending_or_timed_out_provider_state_into_failure(
    client, db, online_payment, offline_services, monkeypatch, method, provider_status
):
    payload = callback_payload(online_payment, "101")
    lookup = AsyncMock(return_value={**payload, "status_code": provider_status})
    monkeypatch.setattr(PayFastClient, "check_status", lookup)
    before = await snapshot(db)
    before.pop(Payment.__tablename__)
    # Reconciliation records evidence, but must not change payment business fields.
    payment_before = {
        column.name: getattr(online_payment, column.name)
        for column in Payment.__table__.columns
        if column.name not in {"gateway_payload", "updated_at"}
    }
    response = await callback_request(client, method, payload)
    assert_error(response, 422, "BUSINESS_RULE_VIOLATION")
    after = await snapshot(db)
    after.pop(Payment.__tablename__)
    assert after == before
    await db.refresh(online_payment)
    assert {name: getattr(online_payment, name) for name in payment_before} == payment_before
    assert online_payment.status == PaymentStatus.pending
    lookup.assert_awaited_once()
    offline_services.transport.assert_not_awaited()


async def test_untrusted_forwarding_header_cannot_bypass_callback_allowlist(
    client, db, online_payment, monkeypatch
):
    monkeypatch.setattr(settings, "PAYFAST_IPN_IPS", ["192.0.2.99"])
    monkeypatch.setattr(settings, "PAYFAST_TRUSTED_PROXY_IPS", [])
    monkeypatch.setattr(settings, "TRUSTED_PROXY_IPS", [])
    before = await snapshot(db)
    response = await callback_request(
        client, "GET", callback_payload(online_payment), headers={"X-Forwarded-For": "192.0.2.99"}
    )
    assert_error(response, 403, "FORBIDDEN")
    assert await snapshot(db) == before
    assert await db.scalar(select(func.count(PaymentCallback.id))) == 0


@pytest.mark.parametrize(
    "query", ["' OR '1'='1", "'; DROP TABLE products; --", "1; SELECT * FROM users"]
)
async def test_search_sql_strings_are_bound_as_data(client, db, accounts, query):
    before = await snapshot(db)
    response = await client.get("/api/v1/products", params={"q": query})
    assert response.status_code == 200, response.text
    assert response.json()["data"] == []
    assert await snapshot(db) == before
    assert await db.scalar(select(func.count(Product.id))) == 1


async def test_search_script_input_is_not_echoed_as_catalogue_content(client, accounts):
    response = await client.get("/api/v1/products", params={"q": "<script>alert(1)</script>"})
    assert response.status_code == 200, response.text
    assert response.json()["data"] == []
    assert "<script>" not in response.text


async def test_oversized_callback_is_rejected_before_payment_handler(client, db, online_payment):
    before = await snapshot(db)
    response = await client.post(
        "/api/v1/payments/callback/payfast",
        content=b"x" * 16385,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert_error(response, 413, "PAYLOAD_TOO_LARGE")
    assert await snapshot(db) == before
    assert await db.scalar(select(func.count(PaymentCallback.id))) == 0


async def test_oversized_registration_password_is_schema_rejected(client, db):
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "synthetic@example.com",
            "password": "X" * 100000,
            "first_name": "Synthetic",
            "last_name": "Customer",
        },
    )
    assert_error(response, 422, "VALIDATION_ERROR")
    assert "password" in response.json()["error"]["fields"]
    assert await db.scalar(select(func.count(User.id))) == 0


@pytest.mark.parametrize("slug", ["../../../etc/passwd", "..%2F..%2Fetc%2Fpasswd"])
async def test_traversal_slug_returns_no_file_content(client, db, accounts, slug):
    before = await snapshot(db)
    response = await client.get(f"/api/v1/products/slug/{slug}")
    assert_error(response, 404, "NOT_FOUND")
    assert await snapshot(db) == before
