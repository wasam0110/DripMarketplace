from __future__ import annotations

from uuid import UUID
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Query, Request, Header
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, CurrentUser, CurrentAdmin
from app.schemas.payment import (
    InitiatePaymentRequest, PaymentInitResponse,
    PaymentStatusResponse, RetryPaymentRequest,
    RefundRequest, RefundResponse,
    GatewayStatusResponse, PaginatedPayments,
)
from app.services.payment_service import PaymentService

router = APIRouter(prefix="/payments", tags=["payments"])

DB = Annotated[AsyncSession, Depends(get_db)]


# ── Customer endpoints ─────────────────────────────────────────────────────────

@router.post("/initiate", response_model=PaymentInitResponse)
async def initiate_payment(
    payload:      InitiatePaymentRequest,
    db:           DB,
    current_user: CurrentUser,
) -> PaymentInitResponse:
    return await PaymentService(db).initiate(
        order_id=payload.order_id,
        user_id=UUID(current_user["sub"]),
    )


@router.get("/{order_id}/status", response_model=PaymentStatusResponse)
async def get_payment_status(
    order_id:     UUID,
    db:           DB,
    current_user: CurrentUser,
) -> PaymentStatusResponse:
    return await PaymentService(db).get_status(
        order_id=order_id,
        user_id=UUID(current_user["sub"]),
    )


@router.post("/{order_id}/retry", response_model=PaymentInitResponse)
async def retry_payment(
    order_id:     UUID,
    payload:      RetryPaymentRequest,
    db:           DB,
    current_user: CurrentUser,
) -> PaymentInitResponse:
    return await PaymentService(db).retry(
        order_id=order_id,
        user_id=UUID(current_user["sub"]),
        payload=payload,
    )


# ── Gateway callbacks (no auth — called by payment gateways) ───────────────────

@router.post("/callback/jazzcash", include_in_schema=False)
async def jazzcash_callback(request: Request, db: DB) -> dict:
    """JazzCash posts form-encoded data to this endpoint."""
    form_data = dict(await request.form())
    await PaymentService(db).handle_jazzcash_callback(form_data)
    return {"status": "ok"}   # Always 200 to gateway


@router.post("/callback/easypaisa", include_in_schema=False)
async def easypaisa_callback(request: Request, db: DB) -> dict:
    try:
        data = await request.json()
        await PaymentService(db).handle_easypaisa_callback(data)
    except Exception:
        pass
    return {"status": "ok"}


@router.post("/callback/stripe", include_in_schema=False)
async def stripe_callback(
    request: Request,
    db:      DB,
    stripe_signature: str = Header(alias="stripe-signature", default=""),
) -> dict:
    payload = await request.body()
    await PaymentService(db).handle_stripe_webhook(payload, stripe_signature)
    return {"status": "ok"}


# ── Admin endpoints ────────────────────────────────────────────────────────────

@router.get("/gateway-status", response_model=GatewayStatusResponse)
async def gateway_status(db: DB, current_admin: CurrentAdmin) -> GatewayStatusResponse:
    return await PaymentService(db).gateway_status()


@router.get("", response_model=PaginatedPayments)
async def list_payments(
    db:            DB,
    current_admin: CurrentAdmin,
    status:        Optional[str] = Query(default=None, pattern="^(pending|processing|completed|failed|refunded)$"),
    method:        Optional[str] = Query(default=None, pattern="^(jazzcash|easypaisa|card|cod)$"),
    page:          int           = Query(default=1, ge=1),
) -> PaginatedPayments:
    payments, total = await PaymentService(db).payment_repo.list_admin(
        status=status, method=method, page=page
    )
    return PaginatedPayments(
        data=[],   # Full serialization wired in Block 8 (Admin)
        total=total,
        page=page,
    )


@router.post("/{payment_id}/refund", response_model=RefundResponse)
async def refund_payment(
    payment_id:    UUID,
    payload:       RefundRequest,
    db:            DB,
    current_admin: CurrentAdmin,
) -> RefundResponse:
    return await PaymentService(db).refund(
        payment_id=payment_id,
        admin_id=UUID(current_admin["sub"]),
        payload=payload,
    )