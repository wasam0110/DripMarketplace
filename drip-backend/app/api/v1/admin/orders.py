"""api / v1 / admin / orders.

HTTP handlers connect validated requests and access dependencies to backend services.
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentAdmin, get_db
from app.models.order import OrderStatus, PaymentMethod
from app.schemas.admin import AdminOrderDetailResponse, PaginatedAdminOrders
from app.services.admin_service import AdminService

router = APIRouter(prefix="/admin", tags=["admin"])
DB = Annotated[AsyncSession, Depends(get_db)]


@router.get("/orders", response_model=PaginatedAdminOrders)
async def list_all_orders(
    db: DB,
    current_admin: CurrentAdmin,
    status: OrderStatus | None = Query(default=None),
    seller_id: UUID | None = Query(default=None),
    payment_method: PaymentMethod | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=25, ge=1, le=100),
) -> PaginatedAdminOrders:
    # Handle GET /orders at this router boundary. Delegates to AdminService.list_orders. Access
    # dependency: CurrentAdmin.
    return await AdminService(db).list_orders(
        status=status,
        seller_id=seller_id,
        payment_method=payment_method,
        page=page,
        per_page=per_page,
    )


@router.get("/orders/{order_id}", response_model=AdminOrderDetailResponse)
async def admin_order_detail(
    order_id: UUID, db: DB, current_admin: CurrentAdmin
) -> AdminOrderDetailResponse:
    """Inspect saved order/fulfilment snapshots without performing a payment action."""
    return await AdminService(db).get_order_detail(order_id)
