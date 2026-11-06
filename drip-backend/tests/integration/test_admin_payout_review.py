"""Reviewed payout snapshots and manual-transfer safeguards, using real database rows."""

import asyncio
from uuid import uuid4

import pytest
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import async_sessionmaker
from tests.integration.test_wallet_api import accounts as accounts
from tests.integration.test_wallet_api import headers, snapshot
from tests.integration.test_wallet_api import requested as requested

from app.core.exceptions import BusinessRuleError, ConflictError
from app.models.seller import SellerWallet
from app.models.wallet import Payout, PayoutStatus, WalletTransaction, WalletTxType
from app.schemas.wallet import WithdrawalRequest
from app.services.wallet_service import WalletService

pytestmark = pytest.mark.integration


def review(payout):
    return {
        "expected_status": payout.status.value,
        "expected_amount": str(payout.amount),
        "expected_seller_id": str(payout.seller_id),
        "expected_payment_method": payout.payment_method,
        "expected_payment_detail": payout.payment_detail,
        "expected_admin_note": payout.admin_note,
    }


async def test_detail_saved_destination_and_admin_boundary(client, db, accounts, requested):
    path = f"/api/v1/admin/wallet/payouts/{requested.id}"
    for user in (accounts.seller, accounts.other, accounts.buyer):
        response = await client.get(path, headers=headers(user))
        assert response.status_code == 403
    accounts.bank.account_number = "CHANGED-CURRENT-BANK"
    await db.flush()
    response = await client.get(path, headers=headers(accounts.admin))
    assert response.status_code == 200, response.text
    value = response.json()
    assert value["seller_id"] == str(accounts.owner.id)
    assert value["payment_detail"] == requested.payment_detail
    assert "CHANGED" not in value["payment_detail"]
    assert value["last_action_by"] is None
    assert value["available_actions"] == ["approve", "reject"]
    assert (
        await client.get(f"/api/v1/admin/wallet/payouts/{uuid4()}", headers=headers(accounts.admin))
    ).status_code == 404


@pytest.mark.parametrize("prefix", ["/admin/wallet/payouts", "/admin/payouts"])
@pytest.mark.parametrize(
    "field,value",
    [
        ("expected_status", "approved"),
        ("expected_amount", "999.99"),
        ("expected_seller_id", "11111111-1111-4111-8111-111111111111"),
        ("expected_payment_method", "other"),
        ("expected_payment_detail", "Another destination"),
        ("expected_admin_note", "Concurrent review"),
    ],
)
async def test_stale_snapshot_cannot_approve(client, db, accounts, requested, prefix, field, value):
    before = await snapshot(db)
    response = await client.post(
        f"/api/v1{prefix}/{requested.id}/approve",
        headers=headers(accounts.admin),
        json={"review": {**review(requested), field: value}},
    )
    assert response.status_code == 409, response.text
    assert await snapshot(db) == before


@pytest.mark.parametrize("prefix", ["/admin/wallet/payouts", "/admin/payouts"])
async def test_reviewed_completion_preserves_receipt_on_replay(
    client, db, accounts, requested, prefix
):
    root = f"/api/v1{prefix}/{requested.id}"
    response = await client.post(
        root + "/approve",
        headers=headers(accounts.admin),
        json={"admin_note": "Reviewed", "review": review(requested)},
    )
    assert response.status_code == 200, response.text
    await db.refresh(requested)
    key = "reference" if "wallet" in prefix else "payment_reference"
    body = {key: "  BANK-001  ", "review": review(requested)}
    response = await client.post(root + "/complete", headers=headers(accounts.admin), json=body)
    assert response.status_code == 200, response.text
    assert response.json()["transfer_reference"] == "BANK-001"
    assert response.json()["admin_note"] == "Reviewed"
    saved = await snapshot(db)
    replay = await client.post(root + "/complete", headers=headers(accounts.admin), json=body)
    assert replay.json() == response.json()
    assert await snapshot(db) == saved
    detail = (
        await client.get(
            f"/api/v1/admin/wallet/payouts/{requested.id}", headers=headers(accounts.admin)
        )
    ).json()
    assert detail["available_actions"] == []
    assert detail["last_action_by"] == str(accounts.admin.id)


@pytest.mark.parametrize("action", ["approve", "reject", "complete"])
async def test_existing_evidence_blocks_mutation(client, db, accounts, requested, action):
    requested.status = PayoutStatus.approved if action == "complete" else PayoutStatus.requested
    requested.transfer_reference = "EXISTING-EVIDENCE"
    await db.flush()
    before = await snapshot(db)
    root = f"/api/v1/admin/wallet/payouts/{requested.id}"
    detail = await client.get(root, headers=headers(accounts.admin))
    assert detail.json()["available_actions"] == []
    response = await client.post(
        root + "/" + action,
        headers=headers(accounts.admin),
        json={"admin_note": "Checked", "reference": "BANK-002", "review": review(requested)},
    )
    assert response.status_code == 422, response.text
    assert await snapshot(db) == before


@pytest.mark.parametrize("note", ["   ", "bad\u0000note"])
async def test_rejection_requires_meaningful_note(client, db, accounts, requested, note):
    before = await snapshot(db)
    response = await client.post(
        f"/api/v1/admin/wallet/payouts/{requested.id}/reject",
        headers=headers(accounts.admin),
        json={"admin_note": note},
    )
    assert response.status_code == 422, response.text
    assert await snapshot(db) == before


async def test_missing_wallet_does_not_falsely_record_reversal(client, db, accounts, requested):
    await db.execute(delete(SellerWallet).where(SellerWallet.seller_id == requested.seller_id))
    await db.flush()
    before = await snapshot(db)
    response = await client.post(
        f"/api/v1/admin/wallet/payouts/{requested.id}/reject",
        headers=headers(accounts.admin),
        json={"admin_note": "Beneficiary mismatch"},
    )
    assert response.status_code == 422, response.text
    assert await snapshot(db) == before


@pytest.mark.parametrize(
    "actions", [("complete", "reject"), ("reject", "reject"), ("complete", "complete")]
)
async def test_independent_sessions_cannot_double_release_or_complete(test_engine, actions):
    sessions = async_sessionmaker(test_engine, expire_on_commit=False)
    async with sessions() as db:
        world = await accounts.__wrapped__(db)
        service = WalletService(db)
        payout = await service.request_withdrawal(
            world.owner.id, WithdrawalRequest(amount=world.amount, bank_account_id=world.bank.id)
        )
        await service.admin_approve_payout(payout.id, world.admin.id)
        payout_id, admin_id, seller_id = payout.id, world.admin.id, world.owner.id
        original, amount = world.original_balance, world.amount
    ready, count = asyncio.Event(), 0

    async def decide(action):
        nonlocal count
        async with sessions() as db:
            cached = await db.get(Payout, payout_id)
            assert cached.status == PayoutStatus.approved
            count += 1
            if count == 2:
                ready.set()
            await ready.wait()
            try:
                service = WalletService(db)
                if action == "complete":
                    return await service.admin_complete_payout(payout_id, admin_id, "BANK-RACE-001")
                return await service.admin_reject_payout(payout_id, admin_id, "Verified rejection")
            except (BusinessRuleError, ConflictError):
                await db.rollback()
                return None

    outcomes = await asyncio.wait_for(asyncio.gather(*(decide(action) for action in actions)), 20)
    assert sum(result is not None for result in outcomes) == (
        2 if actions == ("complete", "complete") else 1
    )
    async with sessions() as db:
        saved = await db.get(Payout, payout_id)
        wallet = await db.scalar(select(SellerWallet).where(SellerWallet.seller_id == seller_id))
        credits = (
            await db.scalars(
                select(WalletTransaction).where(
                    WalletTransaction.payout_id == payout_id,
                    WalletTransaction.type == WalletTxType.credit_adjustment,
                )
            )
        ).all()
        rejected = saved.status == PayoutStatus.rejected
        assert wallet.available_balance == (original if rejected else original - amount)
        assert len(credits) == (1 if rejected else 0)
        assert saved.transfer_reference == (None if rejected else "BANK-RACE-001")
