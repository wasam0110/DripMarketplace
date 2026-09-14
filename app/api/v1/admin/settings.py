from __future__ import annotations

from uuid import UUID
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, CurrentAdmin
from app.schemas.admin import UpdateSettingsRequest, PlatformSettingsResponse
from app.services.admin_service import AdminService

router = APIRouter(prefix="/admin", tags=["admin"])
DB = Annotated[AsyncSession, Depends(get_db)]


@router.get("/settings", response_model=PlatformSettingsResponse)
async def get_settings(db: DB, current_admin: CurrentAdmin) -> PlatformSettingsResponse:
    return await AdminService(db).get_settings()


@router.patch("/settings", response_model=PlatformSettingsResponse)
async def update_settings(
    payload:       UpdateSettingsRequest,
    db:            DB,
    current_admin: CurrentAdmin,
) -> PlatformSettingsResponse:
    updates = {k: v for k, v in payload.model_dump().items() if v is not None}
    return await AdminService(db).update_settings(updates, UUID(current_admin["sub"]))