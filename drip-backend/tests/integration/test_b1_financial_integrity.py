"""Regression tests for backend repair batch 1 financial invariants."""

from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from sqlalchemy import func, select
from test_marketplace_regressions import (
    _fulfil_and_collect_cod,
    _request_single_item_return,
    actor_headers,
)
from test_marketplace_regressions import (
    market as marketplace_fixture,
)

from app.models.payment import Refund
from app.models.seller import SellerBankAccount, SellerWallet
from app.models.wallet import Payout, PayoutStatus, WalletTransaction, WalletTxType
from app.schemas.return_ import AdminReturnActionRequest
from app.schemas.wallet import WithdrawalRequest
from app.services.commission_service import CommissionService
from app.services.payment_service import PaymentService
from app.services.return_service import ReturnService
from app.services.wallet_service import WalletService

pytestmark = pytest.mark.integration
market = marketplace_fixture


async def _fund_wallet_and_bank(db, market, balance: str = "1500.75"):
    wallet = await db.scalar(
        select(SellerWallet).where(SellerWallet.seller_id == market.seller.id)
    )
    wallet.available_balance = Decimal(balance)
    bank = SellerBankAccount(
        seller_id=market.seller.id,
        bank_name="Test Bank",
        account_title="Test Brand",
        account_number="B1-TEST-ACCOUNT",
    )
    db.add(bank)
    await db.commit()
    return wallet, bank


async def test_legacy_payout_completion_uses_locked_state_machine_and_receipt(
    client, db, market
):
    _, bank = await _fund_wallet_and_bank(db, market)
    service = WalletService(db)
    payout = await service.request_withdrawal(
        market.seller.id,
        WithdrawalRequest(amount=Decimal("500.25"), bank_account_id=bank.id),
    )
    await service.admin_approve_payout(payout.id, market.admin.id, "Approved")

    path = f"/api/v1/admin/payouts/{payout.id}/complete"
    response = await client.post(
        path,
        json={"payment_reference": "B1-TRANSFER-001", "admin_note": "Sent by bank"},
        headers=actor_headers(market.admin),
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "completed"
    assert body["transfer_reference"] == "B1-TRANSFER-001"
    assert Decimal(str(body["amount"])) == Decimal("500.25")

    stored = await db.get(Payout, payout.id, populate_existing=True)
    assert stored.status == PayoutStatus.completed
    assert stored.transfer_reference == "B1-TRANSFER-001"
    assert stored.admin_note == "Sent by bank"

    replay = await client.post(
        path,
        json={"payment_reference": "B1-TRANSFER-001"},
        headers=actor_headers(market.admin),
    )
    assert replay.status_code == 200
    conflict = await client.post(
        path,
        json={"payment_reference": "B1-TRANSFER-OTHER"},
        headers=actor_headers(market.admin),
    )
    assert conflict.status_code == 422

    listing = await client.get(
        "/api/v1/admin/payouts?status=completed",
        headers=actor_headers(market.admin),
    )
    assert listing.status_code == 200, listing.text
    listed = next(row for row in listing.json()["data"] if row["id"] == str(payout.id))
    assert Decimal(str(listed["amount"])) == Decimal("500.25")
    assert listed["transfer_reference"] == "B1-TRANSFER-001"


async def test_legacy_payout_completion_rejects_missing_receipt_and_rejected_state(
    client, db, market
):
    wallet, bank = await _fund_wallet_and_bank(db, market, "1000.00")
    service = WalletService(db)
    payout_response = await service.request_withdrawal(
        market.seller.id,
        WithdrawalRequest(amount=Decimal("500.00"), bank_account_id=bank.id),
    )
    await service.admin_reject_payout(
        payout_response.id, market.admin.id, "Invalid beneficiary"
    )
    path = f"/api/v1/admin/payouts/{payout_response.id}/complete"

    missing = await client.post(path, json={}, headers=actor_headers(market.admin))
    assert missing.status_code == 422
    invalid = await client.post(
        path,
        json={"payment_reference": "B1-INVALID-STATE"},
        headers=actor_headers(market.admin),
    )
    assert invalid.status_code == 422

    payout = await db.get(Payout, payout_response.id, populate_existing=True)
    await db.refresh(wallet)
    assert payout.status == PayoutStatus.rejected
    assert payout.transfer_reference is None
    assert wallet.available_balance == Decimal("1000.00")


async def _received_return(db, market, order, seller_order):
    returned, _ = await _request_single_item_return(db, market, order, seller_order)
    service = ReturnService(db)
    await service.approve_return(returned.id, market.admin.id, AdminReturnActionRequest())
    await service.mark_received(returned.id, market.admin.id, AdminReturnActionRequest())
    return returned


async def test_return_refund_is_created_with_its_return_link(db, market, isolated_redis):
    order, seller_order, payment, _ = await _fulfil_and_collect_cod(
        db, market, isolated_redis
    )
    returned = await _received_return(db, market, order, seller_order)

    first = await ReturnService(db).process_refund(
        returned.id,
        market.admin.id,
        AdminReturnActionRequest(admin_note="Atomic return refund"),
    )
    replay = await ReturnService(db).process_refund(
        returned.id,
        market.admin.id,
        AdminReturnActionRequest(admin_note="Atomic return refund"),
    )

    refund = await db.get(Refund, UUID(first["refund_id"]), populate_existing=True)
    count = await db.scalar(
        select(func.count(Refund.id)).where(Refund.payment_id == payment.id)
    )
    assert replay["refund_id"] == first["refund_id"]
    assert refund.return_id == returned.id
    assert count == 1


async def test_return_refund_failure_before_outer_commit_leaves_no_orphan(
    db, market, isolated_redis, monkeypatch
):
    order, seller_order, payment, _ = await _fulfil_and_collect_cod(
        db, market, isolated_redis
    )
    payment_id = payment.id
    returned = await _received_return(db, market, order, seller_order)
    original_refund = PaymentService.refund

    async def fail_after_refund_flush(self, *args, **kwargs):
        assert kwargs["return_id"] == returned.id
        assert kwargs["commit"] is False
        await original_refund(self, *args, **kwargs)
        raise RuntimeError("injected failure before outer commit")

    monkeypatch.setattr(PaymentService, "refund", fail_after_refund_flush)
    with pytest.raises(RuntimeError, match="injected failure"):
        await ReturnService(db).process_refund(
            returned.id,
            market.admin.id,
            AdminReturnActionRequest(admin_note="Failure injection"),
        )
    await db.rollback()

    refund = await db.scalar(
        select(Refund).where(Refund.idempotency_key == f"return:{returned.id}")
    )
    assert refund is None
    assert (
        await db.scalar(
            select(func.count(Refund.id)).where(Refund.payment_id == payment_id)
        )
        == 0
    )


@pytest.mark.parametrize(
    ("pending", "available", "released", "debit", "expected_balance"),
    [
        ("1000.00", "0.00", False, "100.00", "900.00"),
        ("0.00", "1000.00", True, "100.00", "900.00"),
        ("40.00", "60.00", False, "70.00", "30.00"),
        ("0.00", "25.00", True, "70.00", "0.00"),
    ],
)
async def test_refund_debit_audit_balance_matches_wallet(
    db,
    market,
    isolated_redis,
    pending,
    available,
    released,
    debit,
    expected_balance,
):
    _, seller_order, _, wallet = await _fulfil_and_collect_cod(
        db, market, isolated_redis
    )
    wallet.pending_balance = Decimal(pending)
    wallet.available_balance = Decimal(available)
    await db.flush()
    reference = f"b1-balance:{uuid4()}"

    await CommissionService(db)._apply_debit(
        seller_id=market.seller.id,
        debit=Decimal(debit),
        reference=reference,
        seller_order_id=seller_order.id,
        released=released,
        note="Batch 1 balance audit regression",
    )

    await db.refresh(wallet)
    transaction = await db.scalar(
        select(WalletTransaction).where(
            WalletTransaction.reference == reference,
            WalletTransaction.type == WalletTxType.debit_adjustment,
        )
    )
    actual_balance = wallet.pending_balance + wallet.available_balance
    assert actual_balance == Decimal(expected_balance)
    assert transaction.amount == Decimal(debit)
    assert transaction.balance_after == actual_balance
