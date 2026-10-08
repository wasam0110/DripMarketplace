"""
app/api/v1/payments.py — PayFast + COD only.
"""

from __future__ import annotations

import ipaddress
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentAdmin, OptionalUser, get_db
from app.schemas.payment import (
    GatewayStatusResponse,
    InitiatePaymentRequest,
    PaginatedPayments,
    PayFastReconcileResponse,
    PaymentInitResponse,
    PaymentStatusResponse,
    RefundRequest,
    RefundResponse,
    RetryPaymentRequest,
    TransferConfirmationRequest,
)
from app.services.payment_service import PaymentService

router = APIRouter(prefix="/payments", tags=["payments"])

DB = Annotated[AsyncSession, Depends(get_db)]


# ── Customer endpoints ─────────────────────────────────────────────────────────


@router.post("/initiate", response_model=PaymentInitResponse)
async def initiate_payment(
    payload: InitiatePaymentRequest,
    request: Request,
    db: DB,
    current_user: OptionalUser,
    guest_token: str | None = Header(default=None, alias="X-Guest-Token"),
) -> PaymentInitResponse:
    """Initiate a PayFast or COD payment for an order."""
    return await PaymentService(db).initiate(
        order_id=payload.order_id,
        user_id=UUID(current_user["sub"]) if current_user else None,
        guest_token=guest_token,
        customer_ip=_client_ip(request),
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
    request: Request,
    db: DB,
    current_user: OptionalUser,
    guest_token: str | None = Header(default=None, alias="X-Guest-Token"),
) -> PaymentInitResponse:
    return await PaymentService(db).retry(
        order_id=order_id,
        user_id=UUID(current_user["sub"]) if current_user else None,
        guest_token=guest_token,
        payload=payload,
        customer_ip=_client_ip(request),
    )


# ── PayFast IPN callback (no auth — called by PayFast) ────────────────────────


def _matches_ip(value: str, allowed: list[str]) -> bool:
    try:
        address = ipaddress.ip_address(value)
        return any(address in ipaddress.ip_network(item, strict=False) for item in allowed)
    except ValueError:
        return False


def _client_ip(request: Request) -> str:
    """Trust forwarding headers only from explicitly configured reverse proxies."""
    peer = request.client.host if request.client else ""
    from app.core.config import settings

    if peer and _matches_ip(peer, settings.PAYFAST_TRUSTED_PROXY_IPS):
        forwarded = request.headers.get("X-Forwarded-For", "")
        if forwarded:
            candidate = forwarded.split(",", 1)[0].strip()
            try:
                return str(ipaddress.ip_address(candidate))
            except ValueError:
                pass
    return peer


@router.api_route("/callback/payfast", methods=["GET", "POST"], include_in_schema=False)
async def payfast_callback(request: Request, db: DB) -> dict:
    # ── IP allowlist ──────────────────────────────────────────────────────────
    # When PAYFAST_IPN_IPS is populated, only accept requests from those IPs.
    from app.core.config import settings

    allowed_ips = settings.PAYFAST_IPN_IPS
    if allowed_ips and not _matches_ip(_client_ip(request), allowed_ips):
        raise HTTPException(403, "Forbidden")

    try:
        declared_length = int(request.headers.get("content-length", "0"))
    except ValueError as exc:
        raise HTTPException(400, "Invalid content length") from exc
    if declared_length > 16384:
        raise HTTPException(413, "Callback too large")
    callback_data = dict(request.query_params)
    if request.method == "POST":
        body = await request.body()
        if len(body) > 16384:
            raise HTTPException(413, "Callback too large")
        callback_data.update(dict(await request.form()))
    await PaymentService(db).handle_payfast_callback(callback_data)
    return {"status": "ok"}


# ── Admin endpoints ────────────────────────────────────────────────────────────


@router.get("/gateway-status", response_model=GatewayStatusResponse)
async def gateway_status(db: DB, current_admin: CurrentAdmin) -> GatewayStatusResponse:
    return await PaymentService(db).gateway_status()


@router.post("/{order_id}/reconcile", response_model=PayFastReconcileResponse)
async def reconcile_payfast_payment(
    order_id: UUID, db: DB, current_admin: CurrentAdmin
) -> PayFastReconcileResponse:
    """Query PayFast for a missed callback and safely reconcile the order."""
    return await PaymentService(db).reconcile_payfast(order_id)


@router.get("", response_model=PaginatedPayments)
async def list_payments(
    db: DB,
    current_admin: CurrentAdmin,
    status: str | None = Query(
        default=None, pattern="^(pending|processing|completed|failed|refunded)$"
    ),
    method: str | None = Query(default=None, pattern="^(payfast|cod)$"),
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
