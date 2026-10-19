"""Seller API regression checks using real auth and isolated PostgreSQL."""

from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select

from app.core.security import create_access_token, verify_password
from app.models.admin import SystemSetting
from app.models.seller import Seller, SellerBankAccount, SellerStatus, SellerWallet
from app.models.user import User, UserRole
from app.models.wallet import WalletTransaction, WalletTxType

pytestmark = pytest.mark.integration

REGISTRATION = {
    "email": "newbrand@example.com",
    "password": "Password123",
    "first_name": "Ali",
    "brand_name": "New Streetwear Brand",
    "description": "Authentic streetwear for the culture of Pakistan",
    "return_policy": "Exchange unworn items within seven days",
    "whatsapp_number": "03001234567",
    "extra_slots": 0,
}
BANK = {"bank_name": "Test Bank", "account_title": "Test Seller", "account_number": "12345678"}


def auth(user):
    token, _ = create_access_token(
        subject=str(user.id), role=user.role.value, extra_claims={"ver": user.auth_version}
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def sellers(db):
    users, brands, wallets = {}, {}, {}
    for name, role in (
        ("owner", UserRole.seller),
        ("other", UserRole.seller),
        ("customer", UserRole.customer),
        ("admin", UserRole.admin),
    ):
        user = User(
            email=f"{name}@example.com",
            password_hash="synthetic-only",
            role=role,
            has_verified_email=True,
        )
        db.add(user)
        users[name] = user
    await db.flush()
    for name in ("owner", "other"):
        seller = Seller(
            user_id=users[name].id,
            brand_name=f"{name} Brand",
            slug=f"{name}-brand",
            status=SellerStatus.active,
            total_slots=50,
            slots_used=3,
        )
        db.add(seller)
        brands[name] = seller
    await db.flush()
    for name, seller in brands.items():
        wallet = SellerWallet(
            seller_id=seller.id,
            available_balance=Decimal("1000"),
            pending_balance=Decimal("250"),
        )
        db.add(wallet)
        wallets[name] = wallet
    foreign_bank = SellerBankAccount(seller_id=brands["other"].id, **BANK, is_default=True)
    db.add_all(
        [
            foreign_bank,
            SystemSetting(key="registration_fee", value="4500"),
            SystemSetting(key="extra_slot_price", value="75"),
        ]
    )
    await db.commit()
    return {
        "users": users,
        "brands": brands,
        "wallets": wallets,
        "headers": {name: auth(user) for name, user in users.items()},
        "foreign_bank": foreign_bank,
    }


async def snapshot(db):
    state = {}
    for model in (User, Seller, SellerWallet, SellerBankAccount, WalletTransaction):
        rows = (await db.execute(select(*model.__table__.columns))).all()
        state[model.__tablename__] = sorted(tuple(str(value) for value in row) for row in rows)
    return state


def error(response, status, code, field=None):
    assert response.status_code == status, response.text
    body = response.json()["error"]
    assert body["code"] == code
    if field is not None:
        assert field in body["fields"], body


@pytest.mark.parametrize("extra", [0, 20, 10000])
async def test_public_pricing_uses_runtime_values(client, db, sellers, extra):
    before = await snapshot(db)
    response = await client.get("/api/v1/seller/register/slot-price", params={"extra_slots": extra})
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["registration_fee"] == "4500.00"
    assert body["extra_slot_price"] == "75.00"
    assert Decimal(body["extra_cost"]) == 75 * extra
    assert Decimal(body["total_cost"]) == 4500 + 75 * extra
    assert body["total_slots"] == 50 + extra
    assert await snapshot(db) == before


@pytest.mark.parametrize("extra", [-1, 10001])
async def test_public_pricing_rejects_out_of_range(client, db, sellers, extra):
    before = await snapshot(db)
    response = await client.get("/api/v1/seller/register/slot-price", params={"extra_slots": extra})
    error(response, 422, "VALIDATION_ERROR", "query → extra_slots")
    assert await snapshot(db) == before


@pytest.mark.parametrize(
    ("patch", "field"),
    [
        ({"email": "invalid"}, "email"),
        ({"whatsapp_number": "12345"}, "whatsapp_number"),
        ({"password": "password"}, "password"),
        ({"description": "Too short"}, "description"),
        ({"extra_slots": -1}, "extra_slots"),
        ({"extra_slots": 10001}, "extra_slots"),
    ],
)
async def test_registration_validation_has_no_writes(client, db, sellers, patch, field):
    before = await snapshot(db)
    response = await client.post("/api/v1/seller/register", json={**REGISTRATION, **patch})
    error(response, 422, "VALIDATION_ERROR", field)
    assert await snapshot(db) == before


async def test_empty_registration_rejected(client, db, sellers):
    before = await snapshot(db)
    response = await client.post("/api/v1/seller/register", json={})
    error(response, 422, "VALIDATION_ERROR", "email")
    assert await snapshot(db) == before


@pytest.mark.parametrize("free", [False, True])
async def test_registration_persists_user_brand_and_wallet(client, db, sellers, free):
    extra = 2
    if free:
        for key in ("registration_fee", "extra_slot_price"):
            setting = await db.get(SystemSetting, key)
            setting.value = "0"
        await db.commit()
    response = await client.post(
        "/api/v1/seller/register", json={**REGISTRATION, "extra_slots": extra}
    )
    assert response.status_code == 201, response.text
    seller = await db.get(Seller, UUID(response.json()["seller_id"]))
    user = await db.get(User, seller.user_id)
    wallet = await db.scalar(select(SellerWallet).where(SellerWallet.seller_id == seller.id))
    assert user.email == REGISTRATION["email"]
    assert user.role == UserRole.seller
    assert user.has_verified_email is False
    assert user.password_hash != REGISTRATION["password"]
    assert verify_password(REGISTRATION["password"], user.password_hash)
    assert seller.brand_name == REGISTRATION["brand_name"]
    assert seller.total_slots == 52
    assert seller.status == (
        SellerStatus.pending_approval if free else SellerStatus.pending_payment
    )
    expected = Decimal("0") if free else Decimal("4650")
    assert seller.registration_fee == expected
    assert Decimal(response.json()["amount_due"]) == expected
    assert wallet is not None
    assert wallet.available_balance == wallet.pending_balance == Decimal("0")
    response = await client.get("/api/v1/seller/me", headers=auth(user))
    error(response, 401, "EMAIL_NOT_VERIFIED")


@pytest.mark.parametrize(
    "patch",
    [
        {"email": "owner@example.com"},
        {"brand_name": "owner Brand"},
    ],
)
async def test_registration_conflicts_are_atomic(client, db, sellers, patch):
    before = await snapshot(db)
    response = await client.post("/api/v1/seller/register", json={**REGISTRATION, **patch})
    error(response, 409, "CONFLICT")
    assert await snapshot(db) == before


PRIVATE_REQUESTS = [
    ("GET", "/me", None),
    ("PATCH", "/me", {"description": "Updated description"}),
    ("POST", "/logo", None),
    ("GET", "/dashboard", None),
    ("GET", "/orders", None),
    ("GET", "/orders/{id}", None),
    ("GET", "/bank-accounts", None),
    ("POST", "/bank-accounts", BANK),
    ("DELETE", "/bank-accounts/{id}", None),
    ("POST", "/slots/purchase", {"quantity": 2, "payment_method": "wallet"}),
    ("GET", "/analytics/revenue", None),
]


@pytest.mark.parametrize(("method", "path", "payload"), PRIVATE_REQUESTS)
async def test_private_endpoints_require_auth(client, db, sellers, method, path, payload):
    before = await snapshot(db)
    response = await client.request(
        method, "/api/v1/seller" + path.format(id=uuid4()), json=payload
    )
    error(response, 401, "UNAUTHORIZED")
    assert await snapshot(db) == before


@pytest.mark.parametrize("role", ["customer", "admin"])
async def test_non_seller_roles_cannot_access_seller_api(client, db, sellers, role):
    before = await snapshot(db)
    for method, path, payload in PRIVATE_REQUESTS:
        response = await client.request(
            method,
            "/api/v1/seller" + path.format(id=uuid4()),
            headers=sellers["headers"][role],
            json=payload,
        )
        error(response, 403, "FORBIDDEN")
        assert await snapshot(db) == before


@pytest.mark.parametrize(
    ("method", "path", "payload", "field"),
    [
        ("GET", "/dashboard?period=yesterday", None, "query → period"),
        ("GET", "/orders?status=unknown", None, "query → status"),
        ("GET", "/analytics/revenue?period=5y", None, "query → period"),
        ("GET", "/analytics/revenue?granularity=hour", None, "query → granularity"),
        ("POST", "/slots/purchase", {"quantity": 0, "payment_method": "wallet"}, "quantity"),
        ("POST", "/slots/purchase", {"quantity": 10001, "payment_method": "wallet"}, "quantity"),
        ("POST", "/slots/purchase", {"quantity": 1, "payment_method": "payfast"}, "payment_method"),
        ("PATCH", "/me", {"brand_color": "red"}, "brand_color"),
    ],
)
async def test_validation_reaches_authenticated_handler(
    client, db, sellers, method, path, payload, field
):
    before = await snapshot(db)
    response = await client.request(
        method, "/api/v1/seller" + path, headers=sellers["headers"]["owner"], json=payload
    )
    error(response, 422, "VALIDATION_ERROR", field)
    assert await snapshot(db) == before


@pytest.mark.parametrize("path", ["/me", "/bank-accounts"])
async def test_authenticated_empty_updates_rejected(client, db, sellers, path):
    before = await snapshot(db)
    response = await client.request(
        "PATCH" if path == "/me" else "POST",
        "/api/v1/seller" + path,
        headers=sellers["headers"]["owner"],
        json={},
    )
    error(response, 422, "VALIDATION_ERROR")
    assert await snapshot(db) == before


async def test_profile_update_is_scoped_to_current_seller(client, db, sellers):
    headers = sellers["headers"]["owner"]
    response = await client.get("/api/v1/seller/me", headers=headers)
    assert response.status_code == 200, response.text
    assert response.json()["id"] == str(sellers["brands"]["owner"].id)
    assert response.json()["slots_available"] == 47
    foreign_before = (await snapshot(db))["sellers"]
    response = await client.patch(
        "/api/v1/seller/me",
        headers=headers,
        json={"description": "Updated description", "brand_color": "#123ABC"},
    )
    assert response.status_code == 200, response.text
    await db.refresh(sellers["brands"]["owner"])
    assert sellers["brands"]["owner"].description == "Updated description"
    assert sellers["brands"]["owner"].brand_color == "#123ABC"
    foreign_after = (await snapshot(db))["sellers"]
    foreign_id = str(sellers["brands"]["other"].id)
    assert [row for row in foreign_after if foreign_id in row] == [
        row for row in foreign_before if foreign_id in row
    ]


@pytest.mark.parametrize("status", ["pending_payment", "pending_approval", "suspended", "rejected"])
async def test_onboarding_profile_allowed_but_commerce_blocked(client, db, sellers, status):
    seller = sellers["brands"]["owner"]
    seller.status = SellerStatus(status)
    await db.commit()
    headers = sellers["headers"]["owner"]
    response = await client.get("/api/v1/seller/me", headers=headers)
    assert response.status_code == 200
    assert response.json()["status"] == status
    before = await snapshot(db)
    response = await client.get("/api/v1/seller/dashboard", headers=headers)
    error(response, 403, "FORBIDDEN")
    response = await client.post(
        "/api/v1/seller/slots/purchase",
        headers=headers,
        json={"quantity": 1, "payment_method": "wallet"},
    )
    error(response, 403, "FORBIDDEN")
    response = await client.get("/api/v1/seller/analytics/revenue", headers=headers)
    error(response, 403, "SELLER_SUSPENDED" if status == "suspended" else "SELLER_NOT_ACTIVE")
    assert await snapshot(db) == before


async def test_dashboard_and_revenue_empty_state(client, db, sellers):
    headers = sellers["headers"]["owner"]
    before = await snapshot(db)
    response = await client.get("/api/v1/seller/dashboard", headers=headers)
    assert response.status_code == 200, response.text
    body = response.json()
    for key in ("gross_revenue", "commission_paid", "net_earnings"):
        assert Decimal(body[key]) == 0
    assert body["order_count"] == body["product_count"] == 0
    assert body["slots_used"] == 3
    assert body["slots_available"] == 47
    assert Decimal(body["available_balance"]) == 1000
    assert Decimal(body["pending_balance"]) == 250
    response = await client.get("/api/v1/seller/analytics/revenue", headers=headers)
    assert response.status_code == 200, response.text
    assert response.json()["period"] == "30d"
    assert response.json()["granularity"] == "day"
    for row in response.json()["data"]:
        assert all(Decimal(row[key]) == 0 for key in ("gross", "commission", "net"))
        assert row["orders"] == 0
    assert await snapshot(db) == before


async def test_bank_account_defaults_and_ownership(client, db, sellers):
    headers = sellers["headers"]["owner"]
    foreign = sellers["foreign_bank"]
    response = await client.get("/api/v1/seller/bank-accounts", headers=headers)
    assert response.status_code == 200
    assert response.json() == []
    created = []
    for number in ("11111111", "22222222"):
        response = await client.post(
            "/api/v1/seller/bank-accounts",
            headers=headers,
            json={**BANK, "account_number": number, "is_default": True},
        )
        assert response.status_code == 201, response.text
        created.append(UUID(response.json()["id"]))
    first = await db.get(SellerBankAccount, created[0])
    second = await db.get(SellerBankAccount, created[1])
    await db.refresh(first)
    await db.refresh(foreign)
    assert first.is_default is False
    assert second.is_default is True
    assert foreign.is_default is True
    assert second.seller_id == sellers["brands"]["owner"].id
    response = await client.get("/api/v1/seller/bank-accounts", headers=headers)
    assert response.status_code == 200
    assert {row["id"] for row in response.json()} == {str(account) for account in created}
    before = await snapshot(db)
    for account in (foreign.id, uuid4()):
        response = await client.delete(f"/api/v1/seller/bank-accounts/{account}", headers=headers)
        error(response, 404, "NOT_FOUND")
        assert await snapshot(db) == before
    response = await client.delete(f"/api/v1/seller/bank-accounts/{first.id}", headers=headers)
    assert response.status_code == 204
    remaining = list((await db.scalars(select(SellerBankAccount.id))).all())
    assert first.id not in remaining
    assert second.id in remaining and foreign.id in remaining


async def test_slots_charge_runtime_price_and_log_one_debit(client, db, sellers):
    foreign_before = (await snapshot(db))["seller_wallets"]
    response = await client.post(
        "/api/v1/seller/slots/purchase",
        headers=sellers["headers"]["owner"],
        json={"quantity": 2, "payment_method": "wallet"},
    )
    assert response.status_code == 200, response.text
    assert response.json() == {
        "slots_purchased": 2,
        "new_total_slots": 52,
        "new_slots_available": 49,
        "amount_charged": "150.00",
    }
    seller_id = sellers["brands"]["owner"].id
    balances = (
        await db.execute(
            select(SellerWallet.available_balance, SellerWallet.pending_balance, Seller.total_slots)
            .join(Seller, Seller.id == SellerWallet.seller_id)
            .where(Seller.id == seller_id)
        )
    ).one()
    assert balances == (Decimal("850"), Decimal("250"), 52)
    rows = list((await db.scalars(select(WalletTransaction))).all())
    assert len(rows) == 1
    assert rows[0].seller_id == seller_id
    assert rows[0].type == WalletTxType.debit_adjustment
    assert rows[0].amount == 150
    assert rows[0].balance_after == 850
    assert rows[0].reference.startswith("slot-purchase:")
    foreign_id = str(sellers["brands"]["other"].id)
    assert [row for row in (await snapshot(db))["seller_wallets"] if foreign_id in row] == [
        row for row in foreign_before if foreign_id in row
    ]


async def test_insufficient_wallet_does_not_add_slots_or_transactions(client, db, sellers):
    before = await snapshot(db)
    response = await client.post(
        "/api/v1/seller/slots/purchase",
        headers=sellers["headers"]["owner"],
        json={"quantity": 14, "payment_method": "wallet"},
    )
    error(response, 422, "INSUFFICIENT_BALANCE")
    assert await snapshot(db) == before
