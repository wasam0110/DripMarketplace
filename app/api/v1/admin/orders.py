from __future__ import annotations

from uuid import UUID
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, CurrentAdmin
from app.schemas.admin import PaginatedAdminOrders
from app.services.admin_service import AdminService

router = APIRouter(prefix="/admin", tags=["admin"])
DB = Annotated[AsyncSession, Depends(get_db)]


@router.get("/orders", response_model=PaginatedAdminOrders)
async def list_all_orders(
    db:             DB,
    current_admin:  CurrentAdmin,
    status:         Optional[str] = Query(default=None),
    seller_id:      Optional[UUID] = Query(default=None),
    payment_method: Optional[str] = Query(default=None,
                    pattern="^(jazzcash|easypaisa|card|cod)$"),
    page:           int = Query(default=1, ge=1),
    per_page:       int = Query(default=25, ge=1, le=100),
) -> PaginatedAdminOrders:
    return await AdminService(db).list_orders(
        status=status,
        seller_id=seller_id,
        payment_method=payment_method,
        page=page,
        per_page=per_page,
    )