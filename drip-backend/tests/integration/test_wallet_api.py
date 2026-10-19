"""Wallet HTTP checks with native rows, real identities and exact financial effects."""

from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy import func, select

from app.core.config import settings
from app.core.security import create_access_token
from app.models.seller import Seller, SellerBankAccount, SellerStatus, SellerWallet
from app.models.user import User, UserRole
from app.models.wallet import (
    CommissionLedger,
    Payout,
    PayoutStatus,
    WalletTransaction,
    WalletTxType,
)
from app.schemas.wallet import WithdrawalRequest
from app.services.wallet_service import WalletService

pytestmark = pytest.mark.integration


@pytest.fixture
async def accounts(db):
    users = {
        name: User(
            email=f"wallet-{name}@example.com",
            password_hash="synthetic-only",
            role=role,
            has_verified_email=True,
        )
        for name, role in [
            ("seller", UserRole.seller),
            ("other", UserRole.seller),
            ("buyer", UserRole.customer),
            ("admin", UserRole.admin),
        ]
    }
    db.add_all(users.values())
    await db.flush()
    owner = Seller(
        user_id=users["seller"].id,
        brand_name="Wallet Brand",
        slug="wallet-brand",
        status=SellerStatus.active,
        total_slots=50,
    )
    other = Seller(
        user_id=users["other"].id,
        brand_name="Other Wallet",
        slug="other-wallet",
        status=SellerStatus.active,
        total_slots=50,
    )
    db.add_all([owner, other])
    await db.flush()
    amount = min(
        Decimal(settings.MIN_WITHDRAWAL_AMOUNT) + Decimal(".25"),
        Decimal(settings.MAX_WITHDRAWAL_AMOUNT),
    )
    original_balance = amount + Decimal("1000.50")
    wallet = SellerWallet(
        seller_id=owner.id,
        available_balance=original_balance,
        pending_balance=Decimal("100.25"),
        total_earned=Decimal("2000.50"),
        total_commission=Decimal("300.10"),
    )
    foreign_wallet = SellerWallet(
        seller_id=other.id, available_balance=Decimal("9000.10"), pending_balance=Decimal("50.10")
    )
    bank = SellerBankAccount(
        seller_id=owner.id,
        bank_name="Synthetic Bank",
        account_title="Wallet Brand",
        account_number="0000000001",
    )
    foreign_bank = SellerBankAccount(
        seller_id=other.id,
        bank_name="Other Bank",
        account_title="Other Brand",
        account_number="0000000002",
    )
    db.add_all([wallet, foreign_wallet, bank, foreign_bank])
    await db.commit()
    return SimpleNamespace(
        **users,
        owner=owner,
        foreign=other,
        wallet=wallet,
        bank=bank,
        foreign_bank=foreign_bank,
        amount=amount,
        original_balance=original_balance,
    )


@pytest.fixture
async def requested(db, accounts):
    response = await WalletService(db).request_withdrawal(
        accounts.owner.id,
        WithdrawalRequest(amount=accounts.amount, bank_account_id=accounts.bank.id),
    )
    return await db.get(Payout, response.id)


def headers(user):
    token, _ = create_access_token(
        subject=str(user.id), role=user.role.value, extra_claims={"ver": user.auth_version}
    )
    return {"Authorization": f"Bearer {token}"}


def withdrawal(accounts, **changes):
    return {
        "amount": format(accounts.amount, ".2f"),
        "bank_account_id": str(accounts.bank.id),
        **changes,
    }


async def snapshot(db):
    return {
        model.__tablename__: sorted(
            tuple(map(str, row))
            for row in (await db.execute(select(*model.__table__.columns))).all()
        )
        for model in (SellerWallet, Payout, WalletTransaction, CommissionLedger)
    }


def assert_error(response, status, code, fields=()):
    assert response.status_code == status, response.text
    assert response.json()["error"]["code"] == code
    assert set(fields) <= set(response.json()["error"].get("fields", {}))


@pytest.mark.parametrize(
    "method,path",
    [
        ("GET", "/seller/wallet"),
        ("GET", "/seller/wallet/transactions"),
        ("POST", "/seller/wallet/withdraw"),
        ("GET", "/seller/wallet/payouts"),
        ("GET", "/seller/wallet/commission-breakdown"),
        ("GET", "/admin/wallet/overview"),
        ("GET", "/admin/wallet/payouts"),
        ("POST", "/admin/wallet/payouts/{id}/approve"),
        ("POST", "/admin/wallet/payouts/{id}/reject"),
        ("POST", "/admin/wallet/payouts/{id}/complete"),
    ],
)
async def test_wallet_routes_require_auth_without_financial_effect(
    client, db, accounts, requested, method, path
):
    before = await snapshot(db)
    body = (
        withdrawal(accounts)
        if path.endswith("/withdraw")
        else {"reference": "SYNTHETIC-RECEIPT"}
        if path.endswith("/complete")
        else {"admin_note": "Synthetic decision"}
    )
    response = await client.request(
        method,
        "/api/v1" + path.format(id=requested.id),
        **({"json": body} if method == "POST" else {}),
    )
    assert_error(response, 401, "UNAUTHORIZED")
    assert await snapshot(db) == before


@pytest.mark.parametrize("actor", ["buyer", "admin"])
async def test_seller_wallet_rejects_other_roles(client, db, accounts, actor):
    control = await client.get("/api/v1/seller/wallet", headers=headers(accounts.seller))
    assert control.status_code == 200, control.text
    before = await snapshot(db)
    response = await client.get("/api/v1/seller/wallet", headers=headers(getattr(accounts, actor)))
    assert_error(response, 403, "FORBIDDEN")
    assert await snapshot(db) == before


@pytest.mark.parametrize("actor", ["buyer", "seller"])
async def test_admin_wallet_rejects_other_roles(client, db, accounts, actor):
    control = await client.get("/api/v1/admin/wallet/overview", headers=headers(accounts.admin))
    assert control.status_code == 200, control.text
    before = await snapshot(db)
    response = await client.get(
        "/api/v1/admin/wallet/overview", headers=headers(getattr(accounts, actor))
    )
    assert_error(response, 403, "FORBIDDEN")
    assert await snapshot(db) == before


@pytest.mark.parametrize(
    "path,role,field",
    [
        ("/seller/wallet/transactions?tx_type=unknown", "seller", "query → tx_type"),
        ("/seller/wallet/payouts?status=unknown", "seller", "query → status"),
        ("/admin/wallet/payouts?status=unknown", "admin", "query → status"),
    ],
)
async def test_wallet_filter_validation_uses_authorized_identity(
    client, db, accounts, path, role, field
):
    before = await snapshot(db)
    response = await client.get("/api/v1" + path, headers=headers(getattr(accounts, role)))
    assert_error(response, 422, "VALIDATION_ERROR", [field])
    assert await snapshot(db) == before


@pytest.mark.parametrize("case", ["below", "zero", "above", "precision"])
async def test_withdrawal_validation_uses_seller_and_owned_bank(client, db, accounts, case):
    values = {
        "below": Decimal(settings.MIN_WITHDRAWAL_AMOUNT) - Decimal(".01"),
        "zero": Decimal(0),
        "above": Decimal(settings.MAX_WITHDRAWAL_AMOUNT) + Decimal(".01"),
        "precision": Decimal(settings.MIN_WITHDRAWAL_AMOUNT) + Decimal(".001"),
    }
    before = await snapshot(db)
    response = await client.post(
        "/api/v1/seller/wallet/withdraw",
        headers=headers(accounts.seller),
        json=withdrawal(accounts, amount=str(values[case])),
    )
    assert_error(response, 422, "VALIDATION_ERROR", ["amount"])
    assert await snapshot(db) == before


async def test_wallet_summary_uses_identity_and_preserves_exact_amounts(client, db, accounts):
    before = await snapshot(db)
    response = await client.get(
        "/api/v1/seller/wallet",
        headers=headers(accounts.seller),
        params={"seller_id": str(accounts.foreign.id)},
    )
    assert response.status_code == 200, response.text
    assert response.json() == {
        "available_balance": format(accounts.original_balance, ".2f"),
        "pending_balance": "100.25",
        "total_earned": "2000.50",
        "total_commission": "300.10",
    }
    assert await snapshot(db) == before


async def test_empty_wallet_lists_and_commission_summary(client, accounts):
    auth = headers(accounts.seller)
    for path in ("transactions", "payouts"):
        response = await client.get(f"/api/v1/seller/wallet/{path}", headers=auth)
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["data"] == []
        assert body["total"] == 0
        assert body["page"] == body["total_pages"] == 1
    response = await client.get("/api/v1/seller/wallet/commission-breakdown", headers=auth)
    assert response.status_code == 200, response.text
    assert response.json()["data"] == []
    assert response.json()["total"] == 0
    assert all(Decimal(value) == 0 for value in response.json()["summary"].values())


async def test_admin_overview_has_exact_balances_and_counts(client, accounts):
    response = await client.get("/api/v1/admin/wallet/overview", headers=headers(accounts.admin))
    assert response.status_code == 200, response.text
    assert response.json() == {
        "total_available_balance": format(accounts.original_balance + Decimal("9000.10"), ".2f"),
        "total_pending_balance": "150.35",
        "total_payouts_pending": 0,
        "total_payouts_completed": 0,
    }


async def test_withdrawal_debits_once_and_creates_requested_payout(client, db, accounts):
    response = await client.post(
        "/api/v1/seller/wallet/withdraw",
        headers=headers(accounts.seller),
        json=withdrawal(accounts),
    )
    assert response.status_code == 201, response.text
    assert response.json()["amount"] == format(accounts.amount, ".2f")
    assert response.json()["status"] == "requested"
    assert response.json()["transfer_reference"] is None
    await db.refresh(accounts.wallet)
    assert accounts.wallet.available_balance == accounts.original_balance - accounts.amount
    payouts = (await db.scalars(select(Payout))).all()
    transactions = (await db.scalars(select(WalletTransaction))).all()
    assert len(payouts) == len(transactions) == 1
    assert payouts[0].seller_id == accounts.owner.id
    assert payouts[0].status == PayoutStatus.requested
    assert payouts[0].amount == transactions[0].amount == accounts.amount
    assert transactions[0].type == WalletTxType.debit_withdrawal
    assert transactions[0].payout_id == payouts[0].id
    assert transactions[0].balance_after == accounts.wallet.available_balance


@pytest.mark.parametrize("case", ["foreign", "missing"])
async def test_bank_ownership_or_missing_bank_cannot_debit_wallet(client, db, accounts, case):
    bank_id = accounts.foreign_bank.id if case == "foreign" else uuid4()
    before = await snapshot(db)
    response = await client.post(
        "/api/v1/seller/wallet/withdraw",
        headers=headers(accounts.seller),
        json=withdrawal(accounts, bank_account_id=str(bank_id)),
    )
    assert_error(response, 404, "NOT_FOUND")
    assert await snapshot(db) == before


async def test_insufficient_balance_has_no_financial_effect(client, db, accounts):
    accounts.wallet.available_balance = accounts.amount - Decimal(".01")
    await db.commit()
    before = await snapshot(db)
    response = await client.post(
        "/api/v1/seller/wallet/withdraw",
        headers=headers(accounts.seller),
        json=withdrawal(accounts),
    )
    assert_error(response, 422, "BUSINESS_RULE_VIOLATION")
    assert await snapshot(db) == before


async def test_payout_transaction_filters_and_seller_isolation(client, accounts, requested):
    for suffix, expected in [
        ("payouts?status=requested", 1),
        ("payouts?status=completed", 0),
        ("transactions?tx_type=debit_withdrawal", 1),
        ("transactions?tx_type=credit_adjustment", 0),
    ]:
        response = await client.get(
            "/api/v1/seller/wallet/" + suffix, headers=headers(accounts.seller)
        )
        assert response.status_code == 200, response.text
        assert response.json()["total"] == len(response.json()["data"]) == expected
    for suffix in ("transactions", "payouts"):
        response = await client.get(
            "/api/v1/seller/wallet/" + suffix,
            headers=headers(accounts.other),
            params={"seller_id": str(accounts.owner.id)},
        )
        assert response.status_code == 200, response.text
        assert response.json()["data"] == []
        assert response.json()["total"] == 0
    admin = await client.get("/api/v1/admin/wallet/payouts", headers=headers(accounts.admin))
    assert admin.status_code == 200, admin.text
    assert [row["id"] for row in admin.json()["data"]] == [str(requested.id)]


async def test_admin_approval_does_not_debit_again_and_cannot_repeat(
    client, db, accounts, requested
):
    path = f"/api/v1/admin/wallet/payouts/{requested.id}/approve"
    balance = accounts.wallet.available_balance
    first = await client.post(
        path, headers=headers(accounts.admin), json={"admin_note": "Approved"}
    )
    assert first.status_code == 200, first.text
    assert first.json()["status"] == "approved"
    await db.refresh(requested)
    await db.refresh(accounts.wallet)
    assert requested.approved_by == accounts.admin.id
    assert accounts.wallet.available_balance == balance
    assert await db.scalar(select(func.count(WalletTransaction.id))) == 1
    before = await snapshot(db)
    repeated = await client.post(path, headers=headers(accounts.admin), json={})
    assert_error(repeated, 422, "BUSINESS_RULE_VIOLATION")
    assert await snapshot(db) == before


async def test_rejection_credits_original_amount_once(client, db, accounts, requested):
    path = f"/api/v1/admin/wallet/payouts/{requested.id}/reject"
    response = await client.post(
        path, headers=headers(accounts.admin), json={"admin_note": "Wrong beneficiary"}
    )
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "rejected"
    await db.refresh(accounts.wallet)
    assert accounts.wallet.available_balance == accounts.original_balance
    credits = (
        await db.scalars(
            select(WalletTransaction).where(
                WalletTransaction.type == WalletTxType.credit_adjustment
            )
        )
    ).all()
    assert len(credits) == 1
    assert credits[0].amount == accounts.amount
    assert credits[0].balance_after == accounts.original_balance
    before = await snapshot(db)
    replay = await client.post(
        path, headers=headers(accounts.admin), json={"admin_note": "Repeated"}
    )
    assert_error(replay, 422, "BUSINESS_RULE_VIOLATION")
    assert await snapshot(db) == before


async def test_rejection_requires_note_without_financial_effect(client, db, accounts, requested):
    before = await snapshot(db)
    response = await client.post(
        f"/api/v1/admin/wallet/payouts/{requested.id}/reject",
        headers=headers(accounts.admin),
        json={},
    )
    assert response.status_code == 422, response.text
    assert response.json()["error"]["message"] == "admin_note is required for rejection"
    assert await snapshot(db) == before


async def test_completion_receipt_is_idempotent_without_additional_debit(
    client, db, accounts, requested
):
    base = f"/api/v1/admin/wallet/payouts/{requested.id}"
    auth = headers(accounts.admin)
    approved = await client.post(base + "/approve", headers=auth, json={})
    assert approved.status_code == 200, approved.text
    balance = accounts.wallet.available_balance
    receipt = {"reference": "SYNTHETIC-RECEIPT-001"}
    first = await client.post(base + "/complete", headers=auth, json=receipt)
    repeated = await client.post(base + "/complete", headers=auth, json=receipt)
    assert first.status_code == repeated.status_code == 200
    assert first.json() == repeated.json()
    assert first.json()["status"] == "completed"
    assert first.json()["transfer_reference"] == receipt["reference"]
    assert first.json()["completed_at"] is not None
    await db.refresh(accounts.wallet)
    assert accounts.wallet.available_balance == balance
    assert await db.scalar(select(func.count(WalletTransaction.id))) == 1
    before = await snapshot(db)
    changed = await client.post(
        base + "/complete", headers=auth, json={"reference": "DIFFERENT-RECEIPT"}
    )
    assert_error(changed, 422, "BUSINESS_RULE_VIOLATION")
    assert await snapshot(db) == before


async def test_completion_before_approval_has_no_financial_effect(client, db, accounts, requested):
    before = await snapshot(db)
    response = await client.post(
        f"/api/v1/admin/wallet/payouts/{requested.id}/complete",
        headers=headers(accounts.admin),
        json={"reference": "SYNTHETIC-RECEIPT"},
    )
    assert_error(response, 422, "BUSINESS_RULE_VIOLATION")
    assert await snapshot(db) == before


@pytest.mark.parametrize("action", ["approve", "reject"])
async def test_admin_action_missing_payout_is_not_found(client, db, accounts, action):
    before = await snapshot(db)
    response = await client.post(
        f"/api/v1/admin/wallet/payouts/{uuid4()}/{action}",
        headers=headers(accounts.admin),
        json={"admin_note": "Synthetic decision"},
    )
    assert_error(response, 404, "NOT_FOUND")
    assert await snapshot(db) == before
