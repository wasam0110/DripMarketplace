from __future__ import annotations

from uuid import UUID
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, CurrentUser, CurrentAdmin
from app.schemas.notification import (
    NotificationListResponse, NotificationPreferencesResponse,
    UpdatePreferencesRequest, BroadcastRequest, BroadcastResponse,
    MarkReadResponse,
)
from app.services.notification_service import NotificationService

router = APIRouter(tags=["notifications"])
DB = Annotated[AsyncSession, Depends(get_db)]


# ── User endpoints ─────────────────────────────────────────────────────────────

@router.get("/notifications", response_model=NotificationListResponse)
async def list_notifications(
    db:           DB,
    current_user: CurrentUser,
    unread_only:  bool = Query(default=False),
    page:         int  = Query(default=1, ge=1),
    per_page:     int  = Query(default=20, ge=1, le=100),
) -> NotificationListResponse:
    return await NotificationService(db).list_notifications(
        user_id=UUID(current_user["sub"]),
        unread_only=unread_only,
        page=page,
        per_page=per_page,
    )


@router.post("/notifications/{notification_id}/read")
async def mark_notification_read(
    notification_id: UUID,
    db:              DB,
    current_user:    CurrentUser,
) -> dict:
    found = await NotificationService(db).mark_read(
        notification_id=notification_id,
        user_id=UUID(current_user["sub"]),
    )
    return {"marked": found}


@router.post("/notifications/read-all", response_model=MarkReadResponse)
async def mark_all_read(
    db:           DB,
    current_user: CurrentUser,
) -> MarkReadResponse:
    count = await NotificationService(db).mark_all_read(UUID(current_user["sub"]))
    return MarkReadResponse(updated_count=count)


@router.get("/notifications/preferences", response_model=NotificationPreferencesResponse)
async def get_preferences(
    db:           DB,
    current_user: CurrentUser,
) -> NotificationPreferencesResponse:
    return await NotificationService(db).get_preferences(UUID(current_user["sub"]))


@router.patch("/notifications/preferences", response_model=NotificationPreferencesResponse)
async def update_preferences(
    payload:      UpdatePreferencesRequest,
    db:           DB,
    current_user: CurrentUser,
) -> NotificationPreferencesResponse:
    return await NotificationService(db).update_preferences(
        user_id=UUID(current_user["sub"]), payload=payload
    )


# ── Admin endpoints ────────────────────────────────────────────────────────────

@router.post("/admin/notifications/broadcast",
             response_model=BroadcastResponse, status_code=202)
async def broadcast_notification(
    payload:       BroadcastRequest,
    db:            DB,
    current_admin: CurrentAdmin,
) -> BroadcastResponse:
    return await NotificationService(db).broadcast(
        payload=payload, admin_id=UUID(current_admin["sub"])
    )


@router.get("/admin/notifications/email-log")
async def get_email_log(
    db:              DB,
    current_admin:   CurrentAdmin,
    recipient_email: Optional[str] = Query(default=None),
    date_from:       Optional[str] = Query(default=None),
    page:            int           = Query(default=1, ge=1),
) -> dict:
    return await NotificationService(db).get_email_log(
        recipient_email=recipient_email, date_from=date_from, page=page
    )