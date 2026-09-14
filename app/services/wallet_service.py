from __future__ import annotations

from decimal import Decimal
from uuid import UUID
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BusinessRuleError, NotFoundError, PermissionDeniedError
from app.models.wallet import WalletTxType, Payout, PayoutStatus
from app.models.seller import SellerWallet, SellerBankAccount
from app.repositories.wallet_repo import (
    WalletTransactionRepository, PayoutRepository, CommissionRepository
)
from app.repositories.seller_repo import WalletRepository, SellerRepository
from app.schemas.wallet import (
    WalletSummaryResponse, PaginatedTransactions, WalletTransactionResponse,
    WithdrawalRequest, PayoutResponse, PaginatedPayouts,
    CommissionEntryResponse, CommissionSummary, CommissionBreakdownResponse,
    AdminWalletOverviewResponse,
)

MIN_WITHDRAWAL = Decimal("500")


class WalletService:
    def __init__(self, db: AsyncSession) -> None:
        self.db          = db
        self.wallet_repo = WalletRepository(db)
        self.tx_repo     = WalletTransactionRepository(db)
        self.payout_repo = PayoutRepository(db)
        self.comm_repo   = CommissionRepository(db)
        self.seller_repo = SellerRepository(db)

    # ── Summary ────────────────────────────────────────────────────────────────

    async def get_summary(self, seller_id: UUID) -> WalletSummaryResponse:
        wallet = await self.wallet_repo.get_by_seller_id(seller_id)
        if not wallet:
            raise NotFoundError("Wallet not found")
        return WalletSummaryResponse(
            available_balance = int(wallet.available_balance),
            pending_balance   = int(wallet.pending_balance),
            total_earned      = int(wallet.total_earned),
            total_commission  = int(wallet.total_commission),
        )

    # ── Transactions ───────────────────────────────────────────────────────────

    async def get_transactions(
        self,
        seller_id: UUID,
        tx_type:   Optional[str] = None,
        page:      int = 1,
        per_page:  int = 25,
    ) -> PaginatedTransactions:
        rows, total = await self.tx_repo.list_by_seller(seller_id, tx_type, page, per_page)
        total_pages = max(1, (total + per_page - 1) // per_page)
        return PaginatedTransactions(
            data=[
                WalletTransactionResponse(
                    id           = tx.id,
                    type         = tx.type.value,
                    amount       = int(tx.amount),
                    balance_after= int(tx.balance_after),
                    reference    = tx.reference,
                    note         = tx.note,
                    created_at   = tx.created_at,
                )
                for tx in rows
            ],
            total=total, page=page, per_page=per_page, total_pages=total_pages,
        )

    # ── Withdrawal ─────────────────────────────────────────────────────────────

    async def request_withdrawal(
        self, seller_id: UUID, payload: WithdrawalRequest
    ) -> PayoutResponse:
        wallet = await self.wallet_repo.get_by_seller_id(seller_id)
        if not wallet:
            raise NotFoundError("Wallet not found")

        amount = Decimal(payload.amount)
        if wallet.available_balance < amount:
            raise BusinessRuleError(
                f"Insufficient balance. Available: PKR {int(wallet.available_balance):,}"
            )
        if amount < MIN_WITHDRAWAL:
            raise BusinessRuleError(f"Minimum withdrawal is PKR {int(MIN_WITHDRAWAL):,}")

        # Fetch bank account
        result = await self.db.execute(
            select(SellerBankAccount).where(
                SellerBankAccount.id == payload.bank_account_id,
                SellerBankAccount.seller_id == seller_id,
            )
        )
        bank_account = result.scalar_one_or_none()
        if not bank_account:
            raise NotFoundError("Bank account not found")

        # Determine payment method + detail
        if bank_account.jazzcash_number:
            method = "jazzcash"
            detail = bank_account.jazzcash_number
        elif bank_account.easypaisa_number:
            method = "easypaisa"
            detail = bank_account.easypaisa_number
        else:
            method = "bank_transfer"
            detail = f"{bank_account.bank_name} — {bank_account.account_number}"

        # Debit available balance
        await self.wallet_repo.debit_available(seller_id, amount)

        # Create payout record
        payout = await self.payout_repo.create(
            seller_id      = seller_id,
            amount         = amount,
            payment_method = method,
            payment_detail = detail,
            status         = PayoutStatus.requested,
        )

        # Refresh wallet for balance_after
        updated = await self.wallet_repo.get_by_seller_id(seller_id)
        balance_after = updated.available_balance if updated else Decimal("0")

        # Log transaction
        await self.tx_repo.create(
            seller_id     = seller_id,
            type          = WalletTxType.debit_withdrawal,
            amount        = amount,
            balance_after = balance_after,
            reference     = str(payout.id),
            payout_id     = payout.id,
            note          = payload.note,
        )

        await self.db.commit()

        return PayoutResponse(
            id             = payout.id,
            amount         = int(amount),
            payment_method = method,
            payment_detail = detail,
            status         = payout.status.value,
            admin_note     = None,
            requested_at   = payout.requested_at,
            completed_at   = None,
        )

    # ── Payouts ────────────────────────────────────────────────────────────────

    async def get_payouts(
        self,
        seller_id: UUID,
        status:    Optional[str] = None,
        page:      int = 1,
    ) -> PaginatedPayouts:
        rows, total = await self.payout_repo.list_by_seller(seller_id, status, page)
        total_pages = max(1, (total + 24) // 25)
        return PaginatedPayouts(
            data=[
                PayoutResponse(
                    id             = p.id,
                    amount         = int(p.amount),
                    payment_method = p.payment_method,
                    payment_detail = p.payment_detail,
                    status         = p.status.value,
                    admin_note     = p.admin_note,
                    requested_at   = p.requested_at,
                    completed_at   = p.completed_at,
                )
                for p in rows
            ],
            total=total, page=page, total_pages=total_pages,
        )

    # ── Commission breakdown ───────────────────────────────────────────────────

    async def get_commission_breakdown(
        self,
        seller_id: UUID,
        date_from: Optional[str] = None,
        date_to:   Optional[str] = None,
        page:      int = 1,
    ) -> CommissionBreakdownResponse:
        rows, total, summary = await self.comm_repo.list_by_seller(
            seller_id, date_from, date_to, page
        )
        return CommissionBreakdownResponse(
            data=[
                CommissionEntryResponse(
                    id                = e.id,
                    seller_order_id   = e.seller_order_id,
                    gross_amount      = int(e.gross_amount),
                    commission_rate   = float(e.commission_rate),
                    commission_amount = int(e.commission_amount),
                    seller_amount     = int(e.seller_amount),
                    settled_at        = e.settled_at,
                )
                for e in rows
            ],
            summary = CommissionSummary(**summary),
            total   = total,
            page    = page,
        )

    # ── Admin ──────────────────────────────────────────────────────────────────

    async def admin_overview(self) -> AdminWalletOverviewResponse:
        from sqlalchemy import func as sqlfunc
        from app.models.seller import SellerWallet as SW
        result = await self.db.execute(
            select(
                sqlfunc.coalesce(sqlfunc.sum(SW.available_balance), 0),
                sqlfunc.coalesce(sqlfunc.sum(SW.pending_balance),   0),
            )
        )
        totals = result.one()

        _, pending_count = await self.payout_repo.list_admin(status="requested")
        _, done_count    = await self.payout_repo.list_admin(status="completed")

        return AdminWalletOverviewResponse(
            total_available_balance = int(totals[0]),
            total_pending_balance   = int(totals[1]),
            total_payouts_pending   = pending_count,
            total_payouts_completed = done_count,
        )

    async def admin_approve_payout(
        self, payout_id: UUID, admin_id: UUID, note: Optional[str] = None
    ) -> PayoutResponse:
        payout = await self.payout_repo.get_by_id(payout_id)
        if not payout:
            raise NotFoundError("Payout not found")
        if payout.status != PayoutStatus.requested:
            raise BusinessRuleError(f"Payout is already '{payout.status.value}'")

        await self.payout_repo.update_status(
            payout_id,
            PayoutStatus.approved,
            approved_by=admin_id,
            admin_note=note,
        )
        await self.db.commit()
        payout.status = PayoutStatus.approved
        return PayoutResponse(
            id=payout.id, amount=int(payout.amount),
            payment_method=payout.payment_method, payment_detail=payout.payment_detail,
            status=PayoutStatus.approved.value, admin_note=note,
            requested_at=payout.requested_at, completed_at=None,
        )

    async def admin_reject_payout(
        self, payout_id: UUID, admin_id: UUID, note: str
    ) -> PayoutResponse:
        payout = await self.payout_repo.get_by_id(payout_id)
        if not payout:
            raise NotFoundError("Payout not found")
        if payout.status not in (PayoutStatus.requested, PayoutStatus.approved):
            raise BusinessRuleError(f"Cannot reject payout at status '{payout.status.value}'")

        # Refund available balance
        await self.wallet_repo.credit_available(payout.seller_id, payout.amount)

        # Log reversal transaction
        updated = await self.wallet_repo.get_by_seller_id(payout.seller_id)
        balance_after = updated.available_balance if updated else Decimal("0")
        await self.tx_repo.create(
            seller_id     = payout.seller_id,
            type          = WalletTxType.credit_adjustment,
            amount        = payout.amount,
            balance_after = balance_after,
            reference     = str(payout_id),
            payout_id     = payout_id,
            note          = f"Payout rejected: {note}",
        )

        await self.payout_repo.update_status(
            payout_id, PayoutStatus.rejected, approved_by=admin_id, admin_note=note
        )
        await self.db.commit()

        return PayoutResponse(
            id=payout.id, amount=int(payout.amount),
            payment_method=payout.payment_method, payment_detail=payout.payment_detail,
            status=PayoutStatus.rejected.value, admin_note=note,
            requested_at=payout.requested_at, completed_at=None,
        )