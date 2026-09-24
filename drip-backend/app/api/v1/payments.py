"""
app/api/v1/payments.py — PayFast + COD only.
"""

from __future__ import annotations

from uuid import UUID
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Query, Request, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, OptionalUser, CurrentAdmin
from app.schemas.payment import (
    InitiatePaymentRequest,
    PaymentInitResponse,
    PaymentStatusResponse,
    RetryPaymentRequest,
    RefundRequest,
    RefundResponse,
    GatewayStatusResponse,
    PaginatedPayments,
    TransferConfirmationRequest,
)
from app.services.payment_service import PaymentService

router = APIRouter(prefix="/payments", tags=["payments"])

DB = Annotated[AsyncSession, Depends(get_db)]


# ── Customer endpoints ─────────────────────────────────────────────────────────


@router.post("/initiate", response_model=PaymentInitResponse)
async def initiate_payment(
    payload: InitiatePaymentRequest,
    db: DB,
    current_user: OptionalUser,
    guest_token: str | None = Header(default=None, alias="X-Guest-Token"),
) -> PaymentInitResponse:
    """Initiate a PayFast or COD payment for an order."""
    return await PaymentService(db).initiate(
        order_id=payload.order_id,
        user_id=UUID(current_user["sub"]) if current_user else None,
        guest_token=guest_token,
    )


@router.get("/{order_id}/status", response_model=PaymentStatusResponse)
async def get_payment_status(
    order_id: UUID,
    db: DB,
    current_user: OptionalUser,
    guest_token: str | None = Header(default=None, alias="X-Guest-Token"),
) -> PaymentStatusResponse:
    return await PaymentService(db).get_status(
        order_id=order_id,
        user_id=UUID(current_user["sub"]) if current_user else None,
        guest_token=guest_token,
    )


@router.post("/{order_id}/retry", response_model=PaymentInitResponse)
async def retry_payment(
    order_id: UUID,
    payload: RetryPaymentRequest,
    db: DB,
    current_user: OptionalUser,
    guest_token: str | None = Header(default=None, alias="X-Guest-Token"),
) -> PaymentInitResponse:
    return await PaymentService(db).retry(
        order_id=order_id,
        user_id=UUID(current_user["sub"]) if current_user else None,
        guest_token=guest_token,
        payload=payload,
    )


# ── PayFast IPN callback (no auth — called by PayFast) ────────────────────────


@router.post("/callback/payfast", include_in_schema=False)
async def payfast_callback(request: Request, db: DB) -> dict:
    if int(request.headers.get("content-length", "0")) > 16384:
        raise HTTPException(413, "Callback too large")
    body = await request.body()
    if len(body) > 16384:
        raise HTTPException(413, "Callback too large")
    form_data = dict(await request.form())
    await PaymentService(db).handle_payfast_callback(form_data)
    return {"status": "ok"}


# ── Admin endpoints ────────────────────────────────────────────────────────────


@router.get("/gateway-status", response_model=GatewayStatusResponse)
async def gateway_status(db: DB, current_admin: CurrentAdmin) -> GatewayStatusResponse:
    return await PaymentService(db).gateway_status()


@router.get("", response_model=PaginatedPayments)
async def list_payments(
    db: DB,
    current_admin: CurrentAdmin,
    status: Optional[str] = Query(
        default=None, pattern="^(pending|processing|completed|failed|refunded)$"
    ),
    method: Optional[str] = Query(default=None, pattern="^(payfast|cod)$"),
    page: int = Query(default=1, ge=1),
) -> PaginatedPayments:
    return await PaymentService(db).list_admin(status=status, method=method, page=page)


@router.post("/{payment_id}/refund", response_model=RefundResponse)
async def refund_payment(
    payment_id: UUID,
    payload: RefundRequest,
    db: DB,
    current_admin: CurrentAdmin,
) -> RefundResponse:
    return await PaymentService(db).refund(
        payment_id=payment_id,
        admin_id=UUID(current_admin["sub"]),
        payload=payload,
    )


@router.post("/refunds/{refund_id}/confirm", response_model=RefundResponse)
async def confirm_refund(
    refund_id: UUID, payload: TransferConfirmationRequest, db: DB, current_admin: CurrentAdmin
):
    return await PaymentService(db).confirm_refund(
        refund_id, UUID(current_admin["sub"]), payload.reference
    )


@router.post("/{payment_id}/cod-collection")
async def record_cod_collection(
    payment_id: UUID, payload: TransferConfirmationRequest, db: DB, current_admin: CurrentAdmin
):
    return await PaymentService(db).record_cod_collection(
        payment_id, UUID(current_admin["sub"]), payload.reference
    )
