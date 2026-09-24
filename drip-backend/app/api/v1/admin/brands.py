from __future__ import annotations

from uuid import UUID
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, CurrentAdmin
from app.schemas.admin import (
    PaginatedAdminSellers, AdminSellerDetailResponse,
    RejectSellerRequest, SuspendSellerRequest,
)
from app.services.admin_service import AdminService

router = APIRouter(prefix="/admin", tags=["admin"])
DB = Annotated[AsyncSession, Depends(get_db)]


@router.get("/sellers", response_model=PaginatedAdminSellers)
async def list_sellers(
    db:            DB,
    current_admin: CurrentAdmin,
    status:        Optional[str] = Query(
        default="all",
        pattern="^(all|pending_payment|pending_approval|active|suspended|rejected)$",
    ),
    q:        Optional[str] = Query(default=None, max_length=100),
    page:     int = Query(default=1, ge=1),
    per_page: int = Query(default=25, ge=1, le=100),
) -> PaginatedAdminSellers:
    return await AdminService(db).list_sellers(status, q, page, per_page)


@router.get("/sellers/{seller_id}", response_model=AdminSellerDetailResponse)
async def get_seller(
    seller_id:     UUID,
    db:            DB,
    current_admin: CurrentAdmin,
) -> AdminSellerDetailResponse:
    return await AdminService(db).get_seller(seller_id)


@router.post("/sellers/{seller_id}/approve")
async def approve_seller(
    seller_id:     UUID,
    db:            DB,
    current_admin: CurrentAdmin,
) -> dict:
    return await AdminService(db).approve_seller(seller_id, UUID(current_admin["sub"]))


@router.post("/sellers/{seller_id}/reject")
async def reject_seller(
    seller_id:     UUID,
    payload:       RejectSellerRequest,
    db:            DB,
    current_admin: CurrentAdmin,
) -> dict:
    return await AdminService(db).reject_seller(
        seller_id, UUID(current_admin["sub"]), payload.reason
    )


@router.post("/sellers/{seller_id}/suspend")
async def suspend_seller(
    seller_id:     UUID,
    payload:       SuspendSellerRequest,
    db:            DB,
    current_admin: CurrentAdmin,
) -> dict:
    return await AdminService(db).suspend_seller(
        seller_id, UUID(current_admin["sub"]), payload.reason
    )


@router.post("/sellers/{seller_id}/reinstate")
async def reinstate_seller(
    seller_id:     UUID,
    db:            DB,
    current_admin: CurrentAdmin,
) -> dict:
    return await AdminService(db).reinstate_seller(seller_id, UUID(current_admin["sub"]))

from app.schemas.admin import SellerRegistrationPaymentRequest

@router.post("/sellers/{seller_id}/registration-payment")
async def record_registration_payment(seller_id: UUID, payload: SellerRegistrationPaymentRequest, db: DB, current_admin: CurrentAdmin):
    from sqlalchemy import select
    from datetime import UTC, datetime
    from app.models.seller import Seller, SellerStatus
    from app.core.exceptions import BusinessRuleError, NotFoundError
    seller = await db.scalar(select(Seller).where(Seller.id == seller_id, Seller.deleted_at.is_(None)).with_for_update())
    if not seller:
        raise NotFoundError("Seller not found")
    if seller.registration_paid_at:
        if seller.registration_payment_reference != payload.reference or seller.registration_fee != payload.amount:
            raise BusinessRuleError("Registration payment is already recorded")
        return {"status": seller.status.value}
    if seller.status != SellerStatus.pending_payment or payload.amount != seller.registration_fee:
        raise BusinessRuleError("Payment must match the registration amount due")
    seller.registration_payment_reference = payload.reference
    seller.registration_paid_at = datetime.now(UTC)
    seller.registration_paid_by = UUID(current_admin["sub"])
    seller.status = SellerStatus.pending_approval
    await db.commit()
    return {"status": seller.status.value}
