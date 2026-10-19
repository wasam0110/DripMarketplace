"""Native withdrawal writes obey startup limits without ledger drift."""

from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import select
from test_marketplace_regressions import market as marketplace_fixture
from test_resource_ownership import headers

from app.core.config import settings
from app.core.exceptions import BusinessRuleError
from app.models.seller import SellerBankAccount, SellerWallet
from app.models.wallet import Payout, WalletTransaction, WalletTxType
from app.schemas.wallet import WithdrawalRequest
from app.services.wallet_service import WalletService

pytestmark = pytest.mark.integration
market = marketplace_fixture
PATH = "/api/v1/seller/wallet/withdraw"


@pytest.fixture
async def funded(db, market):
    wallet = await db.scalar(select(SellerWallet).where(SellerWallet.seller_id == market.seller.id))
    wallet.available_balance = Decimal(settings.MAX_WITHDRAWAL_AMOUNT) + Decimal("1000.75")
    bank = SellerBankAccount(
        seller_id=market.seller.id,
        bank_name="Synthetic Bank",
        account_title="Synthetic Brand",
        account_number="0000000000",
    )
    db.add(bank)
    await db.commit()
    return wallet, bank


async def snapshot(db):
    return [
        sorted(
            tuple(map(str, row))
            for row in (await db.execute(select(*model.__table__.columns))).all()
        )
        for model in (SellerWallet, Payout, WalletTransaction)
    ]


@pytest.mark.parametrize("boundary", ["minimum", "maximum", "fractional"])
async def test_configured_boundary_debits_once_and_records_exact_amount(
    client, db, market, funded, boundary
):
    wallet, bank = funded
    amount = Decimal(
        settings.MAX_WITHDRAWAL_AMOUNT if boundary == "maximum" else settings.MIN_WITHDRAWAL_AMOUNT
    )
    if boundary == "fractional":
        amount += Decimal(".25")
    before = wallet.available_balance
    response = await client.post(
        PATH,
        headers=headers(market.seller_user),
        json={"amount": str(amount), "bank_account_id": str(bank.id)},
    )
    assert response.status_code == 201, response.text
    assert Decimal(response.json()["amount"]) == amount
    await db.refresh(wallet)
    assert wallet.available_balance == before - amount
    payouts = (await db.scalars(select(Payout))).all()
    transactions = (await db.scalars(select(WalletTransaction))).all()
    assert len(payouts) == len(transactions) == 1
    assert payouts[0].amount == transactions[0].amount == amount
    assert transactions[0].type == WalletTxType.debit_withdrawal
    assert transactions[0].balance_after == before - amount
    assert transactions[0].payout_id == payouts[0].id


@pytest.mark.parametrize("kind", ["below", "above", "precision", "nonfinite", "zero"])
async def test_out_of_policy_http_request_has_no_financial_effect(client, db, market, funded, kind):
    _, bank = funded
    amounts = {
        "below": str(Decimal(settings.MIN_WITHDRAWAL_AMOUNT) - Decimal(".01")),
        "above": str(Decimal(settings.MAX_WITHDRAWAL_AMOUNT) + Decimal(".01")),
        "precision": str(Decimal(settings.MIN_WITHDRAWAL_AMOUNT) + Decimal(".001")),
        "nonfinite": "NaN",
        "zero": "0",
    }
    before = await snapshot(db)
    response = await client.post(
        PATH,
        headers=headers(market.seller_user),
        json={"amount": amounts[kind], "bank_account_id": str(bank.id)},
    )
    assert response.status_code == 422, response.text
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
    assert await snapshot(db) == before


@pytest.mark.parametrize("direction", ["below", "above"])
async def test_direct_service_rejects_out_of_policy_without_writes(db, market, funded, direction):
    _, bank = funded
    amount = (
        Decimal(settings.MIN_WITHDRAWAL_AMOUNT) - Decimal(".01")
        if direction == "below"
        else Decimal(settings.MAX_WITHDRAWAL_AMOUNT) + Decimal(".01")
    )
    before = await snapshot(db)
    payload = WithdrawalRequest.model_construct(amount=amount, bank_account_id=bank.id)
    with pytest.raises(BusinessRuleError):
        await WalletService(db).request_withdrawal(market.seller.id, payload)
    assert await snapshot(db) == before


@pytest.mark.parametrize("actor,status", [(None, 401), ("buyer", 403), ("admin", 403)])
async def test_withdrawal_roles_still_rejected(client, db, market, funded, actor, status):
    _, bank = funded
    before = await snapshot(db)
    response = await client.post(
        PATH,
        headers=headers(getattr(market, actor)) if actor else {},
        json={"amount": settings.MIN_WITHDRAWAL_AMOUNT, "bank_account_id": str(bank.id)},
    )
    assert response.status_code == status, response.text
    assert await snapshot(db) == before


@pytest.mark.parametrize("failure,status", [("missing_bank", 404), ("insufficient", 422)])
async def test_other_withdrawal_guards_preserved(client, db, market, funded, failure, status):
    wallet, bank = funded
    if failure == "insufficient":
        wallet.available_balance = Decimal(settings.MIN_WITHDRAWAL_AMOUNT) - Decimal(".01")
        await db.commit()
    before = await snapshot(db)
    response = await client.post(
        PATH,
        headers=headers(market.seller_user),
        json={
            "amount": settings.MIN_WITHDRAWAL_AMOUNT,
            "bank_account_id": str(uuid4() if failure == "missing_bank" else bank.id),
        },
    )
    assert response.status_code == status, response.text
    assert await snapshot(db) == before
