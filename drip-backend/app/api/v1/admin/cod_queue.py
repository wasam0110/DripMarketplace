"""api / v1 / admin / cod queue.

HTTP handlers connect validated requests and access dependencies to backend services.
"""

from __future__ import annotations

from uuid import UUID
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, CurrentAdmin
from app.schemas.admin import CODQueueItem, CODVerifyRequest
from app.services.admin_service import AdminService

router = APIRouter(prefix="/admin", tags=["admin"])
DB = Annotated[AsyncSession, Depends(get_db)]


@router.get("/cod-queue", response_model=list[CODQueueItem])
async def list_cod_queue(
    db: DB, current_admin: CurrentAdmin
) -> list[CODQueueItem]:
    # Handle GET /cod-queue at this router boundary. Delegates to AdminService.list_cod_queue.
    # Access dependency: CurrentAdmin.
    return await AdminService(db).list_cod_queue()


@router.post("/cod-queue/{order_id}/verify")
async def verify_cod_order(
    order_id:      UUID,
    payload:       CODVerifyRequest,
    db:            DB,
    current_admin: CurrentAdmin,
) -> dict:
    # Handle POST /cod-queue/{order_id}/verify at this router boundary. Delegates to
    # AdminService.verify_cod. Access dependency: CurrentAdmin.
    return await AdminService(db).verify_cod(
        order_id=order_id,
        admin_id=UUID(current_admin["sub"]),
        note=payload.note,
    )


@router.post("/cod-queue/{order_id}/cancel")
async def cancel_cod_order(
    order_id:      UUID,
    payload:       CODVerifyRequest,
    db:            DB,
    current_admin: CurrentAdmin,
) -> dict:
    # Handle POST /cod-queue/{order_id}/cancel at this router boundary. Delegates to
    # AdminService.cancel_cod. Access dependency: CurrentAdmin.
    return await AdminService(db).cancel_cod(
        order_id=order_id,
        admin_id=UUID(current_admin["sub"]),
        reason=payload.note,
    )
