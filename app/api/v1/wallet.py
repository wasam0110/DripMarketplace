from __future__ import annotations

from uuid import UUID
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, CurrentSeller, CurrentAdmin
from app.schemas.wallet import (
    WalletSummaryResponse, PaginatedTransactions,
    WithdrawalRequest, PayoutResponse, PaginatedPayouts,
    CommissionBreakdownResponse, AdminWalletOverviewResponse,
    AdminPayoutActionRequest,
)
from app.services.wallet_service import WalletService

router = APIRouter(tags=["wallet"])

DB = Annotated[AsyncSession, Depends(get_db)]


# ── Seller wallet ──────────────────────────────────────────────────────────────

@router.get("/seller/wallet", response_model=WalletSummaryResponse)
async def get_wallet_summary(
    db: DB, current_seller: CurrentSeller
) -> WalletSummaryResponse:
    return await WalletService(db).get_summary(UUID(current_seller["seller_id"]))


@router.get("/seller/wallet/transactions", response_model=PaginatedTransactions)
async def get_wallet_transactions(
    db:             DB,
    current_seller: CurrentSeller,
    tx_type:        Optional[str] = Query(
        default=None,
        pattern="^(credit_commission|debit_commission|credit_refund|debit_withdrawal|credit_adjustment|debit_adjustment)$",
    ),
    page:     int = Query(default=1, ge=1),
    per_page: int = Query(default=25, ge=1, le=100),
) -> PaginatedTransactions:
    return await WalletService(db).get_transactions(
        seller_id = UUID(current_seller["seller_id"]),
        tx_type   = tx_type,
        page      = page,
        per_page  = per_page,
    )


@router.post("/seller/wallet/withdraw", response_model=PayoutResponse, status_code=201)
async def request_withdrawal(
    payload:        WithdrawalRequest,
    db:             DB,
    current_seller: CurrentSeller,
) -> PayoutResponse:
    return await WalletService(db).request_withdrawal(
        seller_id=UUID(current_seller["seller_id"]), payload=payload
    )


@router.get("/seller/wallet/payouts", response_model=PaginatedPayouts)
async def get_payout_history(
    db:             DB,
    current_seller: CurrentSeller,
    status:         Optional[str] = Query(
        default=None,
        pattern="^(requested|approved|processing|completed|rejected)$",
    ),
    page: int = Query(default=1, ge=1),
) -> PaginatedPayouts:
    return await WalletService(db).get_payouts(
        seller_id=UUID(current_seller["seller_id"]),
        status=status,
        page=page,
    )


@router.get("/seller/wallet/commission-breakdown", response_model=CommissionBreakdownResponse)
async def get_commission_breakdown(
    db:             DB,
    current_seller: CurrentSeller,
    date_from:      Optional[str] = Query(default=None),
    date_to:        Optional[str] = Query(default=None),
    page:           int           = Query(default=1, ge=1),
) -> CommissionBreakdownResponse:
    return await WalletService(db).get_commission_breakdown(
        seller_id = UUID(current_seller["seller_id"]),
        date_from = date_from,
        date_to   = date_to,
        page      = page,
    )


# ── Admin wallet ───────────────────────────────────────────────────────────────

@router.get("/admin/wallet/overview", response_model=AdminWalletOverviewResponse)
async def admin_wallet_overview(
    db: DB, current_admin: CurrentAdmin
) -> AdminWalletOverviewResponse:
    return await WalletService(db).admin_overview()


@router.get("/admin/wallet/payouts", response_model=PaginatedPayouts)
async def admin_list_payouts(
    db:            DB,
    current_admin: CurrentAdmin,
    status:        Optional[str] = Query(
        default="requested",
        pattern="^(requested|approved|processing|completed|rejected)$",
    ),
    page: int = Query(default=1, ge=1),
) -> PaginatedPayouts:
    rows, total = await WalletService(db).payout_repo.list_admin(status=status, page=page)
    from app.schemas.wallet import PayoutResponse
    return PaginatedPayouts(
        data=[
            PayoutResponse(
                id=p.id, amount=int(p.amount), payment_method=p.payment_method,
                payment_detail=p.payment_detail, status=p.status.value,
                admin_note=p.admin_note, requested_at=p.requested_at,
                completed_at=p.completed_at,
            )
            for p in rows
        ],
        total=total, page=page, total_pages=max(1, (total + 24) // 25),
    )


@router.post("/admin/wallet/payouts/{payout_id}/approve", response_model=PayoutResponse)
async def admin_approve_payout(
    payout_id:     UUID,
    payload:       AdminPayoutActionRequest,
    db:            DB,
    current_admin: CurrentAdmin,
) -> PayoutResponse:
    return await WalletService(db).admin_approve_payout(
        payout_id=payout_id,
        admin_id=UUID(current_admin["sub"]),
        note=payload.admin_note,
    )


@router.post("/admin/wallet/payouts/{payout_id}/reject", response_model=PayoutResponse)
async def admin_reject_payout(
    payout_id:     UUID,
    payload:       AdminPayoutActionRequest,
    db:            DB,
    current_admin: CurrentAdmin,
) -> PayoutResponse:
    if not payload.admin_note:
        from fastapi import HTTPException
        raise HTTPException(status_code=422, detail="admin_note is required for rejection")
    return await WalletService(db).admin_reject_payout(
        payout_id=payout_id,
        admin_id=UUID(current_admin["sub"]),
        note=payload.admin_note,
    )