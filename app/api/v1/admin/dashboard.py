from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, CurrentAdmin
from app.schemas.admin import AdminDashboardResponse
from app.services.admin_service import AdminService

router = APIRouter(prefix="/admin", tags=["admin"])
DB = Annotated[AsyncSession, Depends(get_db)]


@router.get("/dashboard", response_model=AdminDashboardResponse)
async def admin_dashboard(
    db:            DB,
    current_admin: CurrentAdmin,
    period:        str = Query(default="month", pattern="^(today|week|month|quarter|year)$"),
) -> AdminDashboardResponse:
    return await AdminService(db).get_dashboard(period)