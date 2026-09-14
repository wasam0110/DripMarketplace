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