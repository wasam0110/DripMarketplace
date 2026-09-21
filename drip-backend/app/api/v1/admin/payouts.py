from __future__ import annotations

from uuid import UUID
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, CurrentAdmin
from app.schemas.wallet import PaginatedPayouts, PayoutResponse
from app.services.wallet_service import WalletService
from app.models.wallet import PayoutStatus

router = APIRouter(prefix="/admin", tags=["admin"])
DB = Annotated[AsyncSession, Depends(get_db)]


class PayoutActionRequest(BaseModel):
    admin_note:        Optional[str] = None
    payment_reference: Optional[str] = None


@router.get("/payouts", response_model=PaginatedPayouts)
async def list_all_payouts(
    db:            DB,
    current_admin: CurrentAdmin,
    status:        Optional[str] = Query(
        default="requested",
        pattern="^(requested|approved|processing|completed|rejected)$",
    ),
    page: int = Query(default=1, ge=1),
) -> PaginatedPayouts:
    svc = WalletService(db)
    rows, total = await svc.payout_repo.list_admin(status=status, page=page)
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


@router.post("/payouts/{payout_id}/approve", response_model=PayoutResponse)
async def approve_payout(
    payout_id:     UUID,
    payload:       PayoutActionRequest,
    db:            DB,
    current_admin: CurrentAdmin,
) -> PayoutResponse:
    return await WalletService(db).admin_approve_payout(
        payout_id=payout_id,
        admin_id=UUID(current_admin["sub"]),
        note=payload.admin_note,
    )


@router.post("/payouts/{payout_id}/complete", response_model=PayoutResponse)
async def complete_payout(
    payout_id:     UUID,
    payload:       PayoutActionRequest,
    db:            DB,
    current_admin: CurrentAdmin,
) -> PayoutResponse:
    svc    = WalletService(db)
    payout = await svc.payout_repo.get_by_id(payout_id)
    if not payout:
        from app.core.exceptions import NotFoundError
        raise NotFoundError("Payout not found")
    await svc.payout_repo.update_status(
        payout_id, PayoutStatus.completed,
        approved_by=UUID(current_admin["sub"]),
        admin_note=payload.admin_note,
    )
    await db.commit()
    return PayoutResponse(
        id=payout.id, amount=int(payout.amount),
        payment_method=payout.payment_method, payment_detail=payout.payment_detail,
        status=PayoutStatus.completed.value, admin_note=payload.admin_note,
        requested_at=payout.requested_at, completed_at=payout.completed_at,
    )


@router.post("/payouts/{payout_id}/reject", response_model=PayoutResponse)
async def reject_payout(
    payout_id:     UUID,
    payload:       PayoutActionRequest,
    db:            DB,
    current_admin: CurrentAdmin,
) -> PayoutResponse:
    if not payload.admin_note:
        raise HTTPException(status_code=422, detail="admin_note required for rejection")
    return await WalletService(db).admin_reject_payout(
        payout_id=payout_id,
        admin_id=UUID(current_admin["sub"]),
        note=payload.admin_note,
    )