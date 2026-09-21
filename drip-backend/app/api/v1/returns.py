from __future__ import annotations

from uuid import UUID
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, CurrentUser, CurrentAdmin
from app.schemas.return_ import (
    CreateReturnRequest, ReturnDetailResponse, PaginatedReturns,
    OpenDisputeRequest, AddDisputeMessageRequest,
    DisputeDetailResponse, DisputeMessageResponse,
    AdminReturnActionRequest, ResolveDisputeRequest,
)
from app.services.return_service import ReturnService

router = APIRouter(tags=["returns"])
DB = Annotated[AsyncSession, Depends(get_db)]


# ── Customer ───────────────────────────────────────────────────────────────────

@router.post("/returns", response_model=ReturnDetailResponse, status_code=201)
async def request_return(
    payload:      CreateReturnRequest,
    db:           DB,
    current_user: CurrentUser,
) -> ReturnDetailResponse:
    return await ReturnService(db).request_return(UUID(current_user["sub"]), payload)


@router.get("/returns", response_model=PaginatedReturns)
async def list_returns(
    db:           DB,
    current_user: CurrentUser,
    page:         int = Query(default=1, ge=1),
) -> PaginatedReturns:
    return await ReturnService(db).list_returns(UUID(current_user["sub"]), page)


@router.get("/returns/{return_id}", response_model=ReturnDetailResponse)
async def get_return(
    return_id:    UUID,
    db:           DB,
    current_user: CurrentUser,
) -> ReturnDetailResponse:
    return await ReturnService(db).get_return(return_id, UUID(current_user["sub"]))


@router.post("/returns/{return_id}/dispute", response_model=DisputeDetailResponse, status_code=201)
async def open_dispute(
    return_id:    UUID,
    payload:      OpenDisputeRequest,
    db:           DB,
    current_user: CurrentUser,
) -> DisputeDetailResponse:
    return await ReturnService(db).open_dispute(return_id, UUID(current_user["sub"]), payload)


@router.get("/returns/{return_id}/dispute", response_model=DisputeDetailResponse)
async def get_dispute(
    return_id:    UUID,
    db:           DB,
    current_user: CurrentUser,
) -> DisputeDetailResponse:
    return await ReturnService(db).get_dispute(return_id, UUID(current_user["sub"]))


@router.post("/returns/{return_id}/dispute/messages", response_model=DisputeMessageResponse, status_code=201)
async def add_dispute_message(
    return_id:    UUID,
    payload:      AddDisputeMessageRequest,
    db:           DB,
    current_user: CurrentUser,
) -> DisputeMessageResponse:
    return await ReturnService(db).add_message(return_id, UUID(current_user["sub"]), payload)


# ── Admin ──────────────────────────────────────────────────────────────────────

@router.get("/admin/returns", response_model=PaginatedReturns)
async def admin_list_returns(
    db:            DB,
    current_admin: CurrentAdmin,
    status:        Optional[str] = Query(
        default=None,
        pattern="^(requested|approved|rejected|received|refunded)$",
    ),
    page: int = Query(default=1, ge=1),
) -> PaginatedReturns:
    return await ReturnService(db).admin_list_returns(status, page)


@router.post("/admin/returns/{return_id}/approve")
async def admin_approve_return(
    return_id:     UUID,
    payload:       AdminReturnActionRequest,
    db:            DB,
    current_admin: CurrentAdmin,
) -> dict:
    return await ReturnService(db).approve_return(return_id, UUID(current_admin["sub"]), payload)


@router.post("/admin/returns/{return_id}/reject")
async def admin_reject_return(
    return_id:     UUID,
    payload:       AdminReturnActionRequest,
    db:            DB,
    current_admin: CurrentAdmin,
) -> dict:
    return await ReturnService(db).reject_return(return_id, UUID(current_admin["sub"]), payload)


@router.post("/admin/returns/{return_id}/received")
async def admin_mark_received(
    return_id:     UUID,
    payload:       AdminReturnActionRequest,
    db:            DB,
    current_admin: CurrentAdmin,
) -> dict:
    return await ReturnService(db).mark_received(return_id, UUID(current_admin["sub"]), payload)


@router.post("/admin/returns/{return_id}/refund")
async def admin_process_refund(
    return_id:     UUID,
    payload:       AdminReturnActionRequest,
    db:            DB,
    current_admin: CurrentAdmin,
) -> dict:
    return await ReturnService(db).process_refund(return_id, UUID(current_admin["sub"]), payload)


@router.get("/admin/disputes")
async def admin_list_disputes(
    db:            DB,
    current_admin: CurrentAdmin,
    status:        Optional[str] = Query(
        default=None,
        pattern="^(open|under_review|resolved_customer|resolved_seller|closed)$",
    ),
    page: int = Query(default=1, ge=1),
) -> dict:
    return await ReturnService(db).admin_list_disputes(status, page)


@router.post("/admin/disputes/{dispute_id}/resolve", response_model=DisputeDetailResponse)
async def admin_resolve_dispute(
    dispute_id:    UUID,
    payload:       ResolveDisputeRequest,
    db:            DB,
    current_admin: CurrentAdmin,
) -> DisputeDetailResponse:
    return await ReturnService(db).resolve_dispute(dispute_id, UUID(current_admin["sub"]), payload)