"""api / v1 / returns.

HTTP handlers connect validated requests and access dependencies to backend services.
"""

from __future__ import annotations

from typing import Annotated, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentAdmin, CurrentSeller, CurrentUser, get_db
from app.schemas.return_ import (
    AddDisputeMessageRequest,
    AdminReturnActionRequest,
    AdminReturnDetailResponse,
    CreateReturnRequest,
    DisputeDetailResponse,
    DisputeMessageResponse,
    OpenDisputeRequest,
    PaginatedReturns,
    ResolveDisputeRequest,
    ReturnDetailResponse,
    SellerReturnDetailResponse,
)
from app.services.return_service import ReturnService

router = APIRouter(tags=["returns"])
DB = Annotated[AsyncSession, Depends(get_db)]


# ── Customer ───────────────────────────────────────────────────────────────────

@router.post("/returns/guest", response_model=ReturnDetailResponse, status_code=201)
async def request_guest_return(
    payload: CreateReturnRequest,
    db: DB,
    guest_token: str | None = Header(default=None, alias="X-Guest-Token"),
) -> ReturnDetailResponse:
    # Handle POST /returns/guest at this router boundary. Delegates to
    # ReturnService.request_guest_return.
    return await ReturnService(db).request_guest_return(guest_token, payload)


@router.get("/returns/guest/{return_id}", response_model=ReturnDetailResponse)
async def get_guest_return(
    return_id: UUID,
    db: DB,
    guest_token: str | None = Header(default=None, alias="X-Guest-Token"),
) -> ReturnDetailResponse:
    # Handle GET /returns/guest/{return_id} at this router boundary. Delegates to
    # ReturnService.get_guest_return.
    return await ReturnService(db).get_guest_return(return_id, guest_token)


@router.post("/returns", response_model=ReturnDetailResponse, status_code=201)
async def request_return(
    payload:      CreateReturnRequest,
    db:           DB,
    current_user: CurrentUser,
) -> ReturnDetailResponse:
    # Handle POST /returns at this router boundary. Delegates to ReturnService.request_return.
    # Access dependency: CurrentUser.
    return await ReturnService(db).request_return(UUID(current_user["sub"]), payload)


@router.get("/returns", response_model=PaginatedReturns)
async def list_returns(
    db:           DB,
    current_user: CurrentUser,
    page:         int = Query(default=1, ge=1),
) -> PaginatedReturns:
    # Handle GET /returns at this router boundary. Delegates to ReturnService.list_returns.
    # Access dependency: CurrentUser.
    return await ReturnService(db).list_returns(UUID(current_user["sub"]), page)


@router.get("/returns/{return_id}", response_model=ReturnDetailResponse)
async def get_return(
    return_id:    UUID,
    db:           DB,
    current_user: CurrentUser,
) -> ReturnDetailResponse:
    # Handle GET /returns/{return_id} at this router boundary. Delegates to
    # ReturnService.get_return. Access dependency: CurrentUser.
    return await ReturnService(db).get_return(return_id, UUID(current_user["sub"]))


@router.post("/returns/{return_id}/dispute", response_model=DisputeDetailResponse, status_code=201)
async def open_dispute(
    return_id:    UUID,
    payload:      OpenDisputeRequest,
    db:           DB,
    current_user: CurrentUser,
) -> DisputeDetailResponse:
    # Handle POST /returns/{return_id}/dispute at this router boundary. Delegates to
    # ReturnService.open_dispute. Access dependency: CurrentUser.
    return await ReturnService(db).open_dispute(return_id, UUID(current_user["sub"]), payload)


@router.get("/returns/{return_id}/dispute", response_model=DisputeDetailResponse)
async def get_dispute(
    return_id:    UUID,
    db:           DB,
    current_user: CurrentUser,
) -> DisputeDetailResponse:
    # Handle GET /returns/{return_id}/dispute at this router boundary. Delegates to
    # ReturnService.get_dispute. Access dependency: CurrentUser.
    return await ReturnService(db).get_dispute(return_id, UUID(current_user["sub"]))


@router.post("/returns/{return_id}/dispute/messages", response_model=DisputeMessageResponse, status_code=201)
async def add_dispute_message(
    return_id:    UUID,
    payload:      AddDisputeMessageRequest,
    db:           DB,
    current_user: CurrentUser,
) -> DisputeMessageResponse:
    # Handle POST /returns/{return_id}/dispute/messages at this router boundary. Delegates to
    # ReturnService.add_message. Access dependency: CurrentUser.
    return await ReturnService(db).add_message(return_id, UUID(current_user["sub"]), payload)


# ── Admin ──────────────────────────────────────────────────────────────────────

@router.get("/seller/returns", response_model=PaginatedReturns)
async def seller_list_returns(
    db: DB,
    current_seller: CurrentSeller,
    status: Optional[str] = Query(
        default=None,
        pattern="^(requested|approved|rejected|received|refunded)$",
    ),
    page: int = Query(default=1, ge=1),
) -> PaginatedReturns:
    # Handle GET /seller/returns at this router boundary. Delegates to
    # ReturnService.seller_list_returns. Access dependency: CurrentSeller.
    return await ReturnService(db).seller_list_returns(
        UUID(current_seller["seller_id"]), status, page
    )


@router.get("/seller/returns/{return_id}", response_model=SellerReturnDetailResponse)
async def seller_get_return(
    return_id: UUID,
    db: DB,
    current_seller: CurrentSeller,
) -> SellerReturnDetailResponse:
    # Handle GET /seller/returns/{return_id} at this router boundary. Delegates to
    # ReturnService.get_seller_return. Access dependency: CurrentSeller.
    return await ReturnService(db).get_seller_return(
        return_id, UUID(current_seller["seller_id"])
    )


@router.post("/seller/returns/{return_id}/approve")
async def seller_approve_return(
    return_id: UUID,
    payload: AdminReturnActionRequest,
    db: DB,
    current_seller: CurrentSeller,
) -> dict:
    # Handle POST /seller/returns/{return_id}/approve at this router boundary. Delegates to
    # ReturnService.seller_approve_return. Access dependency: CurrentSeller.
    return await ReturnService(db).seller_approve_return(
        return_id, UUID(current_seller["seller_id"]), payload
    )


@router.post("/seller/returns/{return_id}/reject")
async def seller_reject_return(
    return_id: UUID,
    payload: AdminReturnActionRequest,
    db: DB,
    current_seller: CurrentSeller,
) -> dict:
    # Handle POST /seller/returns/{return_id}/reject at this router boundary. Delegates to
    # ReturnService.seller_reject_return. Access dependency: CurrentSeller.
    return await ReturnService(db).seller_reject_return(
        return_id, UUID(current_seller["seller_id"]), payload
    )


@router.post("/seller/returns/{return_id}/received")
async def seller_mark_received(
    return_id: UUID,
    payload: AdminReturnActionRequest,
    db: DB,
    current_seller: CurrentSeller,
) -> dict:
    # Handle POST /seller/returns/{return_id}/received at this router boundary. Delegates to
    # ReturnService.seller_mark_received. Access dependency: CurrentSeller.
    return await ReturnService(db).seller_mark_received(
        return_id, UUID(current_seller["seller_id"]), payload
    )


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
    # Handle GET /admin/returns at this router boundary. Delegates to
    # ReturnService.admin_list_returns. Access dependency: CurrentAdmin.
    return await ReturnService(db).admin_list_returns(status, page)


@router.get("/admin/returns/{return_id}", response_model=AdminReturnDetailResponse)
async def admin_get_return(
    return_id:     UUID,
    db:            DB,
    current_admin: CurrentAdmin,
) -> AdminReturnDetailResponse:
    # Handle GET /admin/returns/{return_id} at this router boundary. Delegates to
    # ReturnService.get_admin_return. Access dependency: CurrentAdmin.
    return await ReturnService(db).get_admin_return(return_id)


@router.post("/admin/returns/{return_id}/approve")
async def admin_approve_return(
    return_id:     UUID,
    payload:       AdminReturnActionRequest,
    db:            DB,
    current_admin: CurrentAdmin,
) -> dict:
    # Handle POST /admin/returns/{return_id}/approve at this router boundary. Delegates to
    # ReturnService.approve_return. Access dependency: CurrentAdmin.
    return await ReturnService(db).approve_return(return_id, UUID(current_admin["sub"]), payload)


@router.post("/admin/returns/{return_id}/reject")
async def admin_reject_return(
    return_id:     UUID,
    payload:       AdminReturnActionRequest,
    db:            DB,
    current_admin: CurrentAdmin,
) -> dict:
    # Handle POST /admin/returns/{return_id}/reject at this router boundary. Delegates to
    # ReturnService.reject_return. Access dependency: CurrentAdmin.
    return await ReturnService(db).reject_return(return_id, UUID(current_admin["sub"]), payload)


@router.post("/admin/returns/{return_id}/received")
async def admin_mark_received(
    return_id:     UUID,
    payload:       AdminReturnActionRequest,
    db:            DB,
    current_admin: CurrentAdmin,
) -> dict:
    # Handle POST /admin/returns/{return_id}/received at this router boundary. Delegates to
    # ReturnService.mark_received. Access dependency: CurrentAdmin.
    return await ReturnService(db).mark_received(return_id, UUID(current_admin["sub"]), payload)


@router.post("/admin/returns/{return_id}/refund")
async def admin_process_refund(
    return_id:     UUID,
    payload:       AdminReturnActionRequest,
    db:            DB,
    current_admin: CurrentAdmin,
) -> dict:
    # Handle POST /admin/returns/{return_id}/refund at this router boundary. Delegates to
    # ReturnService.process_refund. Access dependency: CurrentAdmin.
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
    # Handle GET /admin/disputes at this router boundary. Delegates to
    # ReturnService.admin_list_disputes. Access dependency: CurrentAdmin.
    return await ReturnService(db).admin_list_disputes(status, page)


@router.get("/admin/disputes/{dispute_id}", response_model=DisputeDetailResponse)
async def admin_get_dispute(
    dispute_id: UUID,
    db: DB,
    current_admin: CurrentAdmin,
) -> DisputeDetailResponse:
    # Handle GET /admin/disputes/{dispute_id} at this router boundary. Delegates to
    # ReturnService.get_admin_dispute. Access dependency: CurrentAdmin.
    return await ReturnService(db).get_admin_dispute(dispute_id)


@router.post(
    "/admin/disputes/{dispute_id}/messages",
    response_model=DisputeMessageResponse,
    status_code=201,
)
async def admin_add_dispute_message(
    dispute_id: UUID,
    payload: AddDisputeMessageRequest,
    db: DB,
    current_admin: CurrentAdmin,
) -> DisputeMessageResponse:
    # Handle POST /admin/disputes/{dispute_id}/messages at this router boundary. Delegates to
    # ReturnService.add_admin_message. Access dependency: CurrentAdmin.
    return await ReturnService(db).add_admin_message(
        dispute_id, UUID(current_admin["sub"]), payload
    )


@router.post("/admin/disputes/{dispute_id}/resolve", response_model=DisputeDetailResponse)
async def admin_resolve_dispute(
    dispute_id:    UUID,
    payload:       ResolveDisputeRequest,
    db:            DB,
    current_admin: CurrentAdmin,
) -> DisputeDetailResponse:
    # Handle POST /admin/disputes/{dispute_id}/resolve at this router boundary. Delegates to
    # ReturnService.resolve_dispute. Access dependency: CurrentAdmin.
    return await ReturnService(db).resolve_dispute(dispute_id, UUID(current_admin["sub"]), payload)
