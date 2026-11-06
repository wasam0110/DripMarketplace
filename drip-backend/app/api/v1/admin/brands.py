"""api / v1 / admin / brands.

HTTP handlers connect validated requests and access dependencies to backend services.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentAdmin, get_db
from app.core.exceptions import BusinessRuleError, NotFoundError
from app.models.seller import Seller, SellerStatus
from app.schemas.admin import (
    AdminSellerDetailResponse,
    PaginatedAdminSellers,
    RejectSellerRequest,
    SellerRegistrationPaymentRequest,
    SuspendSellerRequest,
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
    # Handle GET /sellers at this router boundary. Delegates to AdminService.list_sellers.
    # Access dependency: CurrentAdmin.
    return await AdminService(db).list_sellers(status, q, page, per_page)


@router.get("/sellers/{seller_id}", response_model=AdminSellerDetailResponse)
async def get_seller(
    seller_id:     UUID,
    db:            DB,
    current_admin: CurrentAdmin,
) -> AdminSellerDetailResponse:
    # Handle GET /sellers/{seller_id} at this router boundary. Delegates to
    # AdminService.get_seller. Access dependency: CurrentAdmin.
    return await AdminService(db).get_seller(seller_id)


@router.post("/sellers/{seller_id}/approve")
async def approve_seller(
    seller_id:     UUID,
    db:            DB,
    current_admin: CurrentAdmin,
) -> dict:
    # Handle POST /sellers/{seller_id}/approve at this router boundary. Delegates to
    # AdminService.approve_seller. Access dependency: CurrentAdmin.
    return await AdminService(db).approve_seller(seller_id, UUID(current_admin["sub"]))


@router.post("/sellers/{seller_id}/reject")
async def reject_seller(
    seller_id:     UUID,
    payload:       RejectSellerRequest,
    db:            DB,
    current_admin: CurrentAdmin,
) -> dict:
    # Handle POST /sellers/{seller_id}/reject at this router boundary. Delegates to
    # AdminService.reject_seller. Access dependency: CurrentAdmin.
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
    # Handle POST /sellers/{seller_id}/suspend at this router boundary. Delegates to
    # AdminService.suspend_seller. Access dependency: CurrentAdmin.
    return await AdminService(db).suspend_seller(
        seller_id, UUID(current_admin["sub"]), payload.reason
    )


@router.post("/sellers/{seller_id}/reinstate")
async def reinstate_seller(
    seller_id:     UUID,
    db:            DB,
    current_admin: CurrentAdmin,
) -> dict:
    # Handle POST /sellers/{seller_id}/reinstate at this router boundary. Delegates to
    # AdminService.reinstate_seller. Access dependency: CurrentAdmin.
    return await AdminService(db).reinstate_seller(seller_id, UUID(current_admin["sub"]))

@router.post("/sellers/{seller_id}/registration-payment")
async def record_registration_payment(
    seller_id: UUID,
    payload: SellerRegistrationPaymentRequest,
    db: DB,
    current_admin: CurrentAdmin,
) -> dict[str, str]:
    # Handle POST /sellers/{seller_id}/registration-payment at this router boundary. Access
    # dependency: CurrentAdmin.
    seller = await db.scalar(
        select(Seller)
        .where(Seller.id == seller_id, Seller.deleted_at.is_(None))
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if not seller:
        raise NotFoundError("Seller not found")
    if seller.registration_paid_at:
        if (
            seller.registration_payment_reference != payload.reference
            or seller.registration_fee != payload.amount
        ):
            raise BusinessRuleError("Registration payment is already recorded")
        return {"status": seller.status.value}
    if seller.registration_payment_reference is not None or seller.registration_paid_by is not None:
        raise BusinessRuleError("Incomplete registration payment record requires reconciliation")
    if seller.status != SellerStatus.pending_payment or payload.amount != seller.registration_fee:
        raise BusinessRuleError("Payment must match the registration amount due")
    seller.registration_payment_reference = payload.reference
    seller.registration_paid_at = datetime.now(UTC)
    seller.registration_paid_by = UUID(current_admin["sub"])
    seller.status = SellerStatus.pending_approval
    await db.commit()
    return {"status": seller.status.value}
