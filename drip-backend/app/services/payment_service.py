"""
app/services/payment_service.py
────────────────────────────────
Payment business logic — PayFast + COD only.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import (
    BusinessRuleError, NotFoundError, ExternalServiceError
)
from app.core.logging import get_logger
from app.integrations.payfast import PayFastClient
from app.models.order import Order, OrderStatus, PaymentMethod
from app.models.payment import Payment, PaymentCallback, PaymentStatus
from app.repositories.order_repo import OrderRepository
from app.repositories.payment_repo import PaymentRepository
from app.schemas.payment import (
    PaymentInitResponse, PaymentStatusResponse,
    RetryPaymentRequest, RefundRequest, RefundResponse,
    GatewayStatusResponse,
)

logger = get_logger(__name__)


def _build_payfast() -> PayFastClient:
    return PayFastClient(
        merchant_id = settings.PAYFAST_MERCHANT_ID,
        secured_key = settings.PAYFAST_SECURED_KEY,
        sandbox     = getattr(settings, "PAYFAST_SANDBOX", True),
    )


RETRYABLE_ORDER_STATUSES    = {OrderStatus.pending_payment}
REFUNDABLE_PAYMENT_STATUSES = {PaymentStatus.completed}


class PaymentService:
    def __init__(self, db: AsyncSession) -> None:
        self.db           = db
        self.payment_repo = PaymentRepository(db)
        self.order_repo   = OrderRepository(db)

    # ── Initiate ──────────────────────────────────────────────────────────────

    async def initiate(
        self, order_id: uuid.UUID, user_id: uuid.UUID
    ) -> PaymentInitResponse:
        order = await self.order_repo.get_by_id(order_id, user_id=user_id)
        if not order:
            raise NotFoundError("Order not found")

        if order.status not in (
            OrderStatus.pending_payment,
            OrderStatus.pending_cod_verification,
        ):
            raise BusinessRuleError(
                f"Order is not awaiting payment (status: {order.status.value})"
            )

        existing = await self.payment_repo.get_by_order_id(order_id)
        if existing and existing.status == PaymentStatus.completed:
            raise BusinessRuleError("Payment already completed for this order")

        if order.payment_method == PaymentMethod.cod:
            return await self._initiate_cod(order)
        if order.payment_method == PaymentMethod.payfast:
            return await self._initiate_payfast(order, user_id)

        raise BusinessRuleError(
            f"Unsupported payment method: {order.payment_method.value}"
        )

    async def _initiate_cod(self, order: Order) -> PaymentInitResponse:
        payment = await self.payment_repo.create(
            order_id=order.id,
            method=PaymentMethod.cod.value,
            amount=Decimal(order.total) / 100,
            status=PaymentStatus.pending,
        )
        logger.info("cod_payment_initiated", order_id=str(order.id))
        return PaymentInitResponse(
            payment_id=payment.id,
            method="cod",
        )

    async def _initiate_payfast(
        self, order: Order, user_id: uuid.UUID
    ) -> PaymentInitResponse:
        from app.models.user import User
        user = await self.db.get(User, user_id)

        payment = await self.payment_repo.create(
            order_id=order.id,
            method=PaymentMethod.payfast.value,
            amount=Decimal(order.total) / 100,
            status=PaymentStatus.pending,
        )

        pf = _build_payfast()
        amount_pkr = int(order.total // 100)  # convert paisa → rupees

        payload = pf.build_checkout_payload(
            order_id=str(order.id),
            amount=amount_pkr,
            description=f"DRIP Order #{order.order_number}",
            return_url=f"{settings.FRONTEND_URL}/order/success/{order.id}",
            cancel_url=f"{settings.FRONTEND_URL}/checkout?cancelled=1",
            ipn_url=f"{settings.API_BASE_URL}/api/v1/payments/callback/payfast",
            customer_email=user.email if user else "",
            customer_name=f"{user.first_name or ''} {user.last_name or ''}".strip() if user else "",
        )

        logger.info("payfast_payment_initiated", order_id=str(order.id), payment_id=str(payment.id))
        return PaymentInitResponse(
            payment_id=payment.id,
            method="payfast",
            checkout_url=pf.base_url,
            payfast_payload=payload,
        )

    # ── Status ────────────────────────────────────────────────────────────────

    async def get_status(
        self, order_id: uuid.UUID, user_id: uuid.UUID
    ) -> PaymentStatusResponse:
        order = await self.order_repo.get_by_id(order_id, user_id=user_id)
        if not order:
            raise NotFoundError("Order not found")

        payment = await self.payment_repo.get_by_order_id(order_id)
        if not payment:
            raise NotFoundError("Payment not found")

        return PaymentStatusResponse(
            order_id=order_id,
            payment_id=payment.id,
            status=payment.status.value,
            method=payment.method,
            amount=int(payment.amount * 100),
            gateway_reference=payment.gateway_reference,
            paid_at=payment.paid_at,
        )

    # ── Retry ─────────────────────────────────────────────────────────────────

    async def retry(
        self,
        order_id: uuid.UUID,
        user_id:  uuid.UUID,
        payload:  RetryPaymentRequest,
    ) -> PaymentInitResponse:
        order = await self.order_repo.get_by_id(order_id, user_id=user_id)
        if not order:
            raise NotFoundError("Order not found")
        if order.status not in RETRYABLE_ORDER_STATUSES:
            raise BusinessRuleError("This order cannot be retried")

        # Update payment method on the order
        from sqlalchemy import update
        from app.models.order import Order as OrderModel
        await self.db.execute(
            update(OrderModel)
            .where(OrderModel.id == order_id)
            .values(payment_method=payload.payment_method)
        )
        await self.db.commit()
        await self.db.refresh(order)

        return await self.initiate(order_id=order_id, user_id=user_id)

    # ── IPN callback ──────────────────────────────────────────────────────────

    async def handle_payfast_callback(self, data: dict) -> None:
        """Process PayFast IPN callback."""
        # Log the raw callback first
        callback = PaymentCallback(
            gateway=     "payfast",
            raw_payload= data,
            is_verified= False,
        )
        self.db.add(callback)
        await self.db.flush()

        try:
            pf     = _build_payfast()
            parsed = pf.parse_ipn(data)   # raises ValueError if sig invalid
        except ValueError as e:
            logger.warning("payfast_ipn_invalid_signature", error=str(e))
            return

        # Mark callback as verified
        callback.is_verified = True

        order_id_str = parsed["order_id"]
        try:
            order_id = uuid.UUID(order_id_str)
        except ValueError:
            logger.error("payfast_ipn_invalid_order_id", raw=order_id_str)
            return

        payment = await self.payment_repo.get_by_order_id(order_id)
        if not payment:
            logger.error("payfast_ipn_payment_not_found", order_id=order_id_str)
            return

        callback.payment_id = payment.id

        if parsed["status"] == "completed":
            payment.status            = PaymentStatus.completed
            payment.gateway_reference = parsed["txn_id"]
            payment.gateway_payload   = parsed["raw"]
            payment.paid_at           = datetime.now(timezone.utc)

            # Advance order
            from sqlalchemy import update as sa_update
            from app.models.order import Order as OrderModel
            await self.db.execute(
                sa_update(OrderModel)
                .where(OrderModel.id == order_id)
                .values(status=OrderStatus.payment_confirmed)
            )
            logger.info("payfast_payment_confirmed", order_id=order_id_str)

        elif parsed["status"] == "failed":
            payment.status        = PaymentStatus.failed
            payment.failure_reason= "PayFast reported payment failure"
            logger.warning("payfast_payment_failed", order_id=order_id_str)

        elif parsed["status"] == "refunded":
            payment.status = PaymentStatus.refunded
            logger.info("payfast_payment_refunded", order_id=order_id_str)

        await self.db.commit()

    # ── Refund ────────────────────────────────────────────────────────────────

    async def refund(
        self,
        payment_id: uuid.UUID,
        admin_id:   uuid.UUID,
        payload:    RefundRequest,
    ) -> RefundResponse:
        payment = await self.payment_repo.get_by_id(payment_id)
        if not payment:
            raise NotFoundError("Payment not found")
        if payment.status not in REFUNDABLE_PAYMENT_STATUSES:
            raise BusinessRuleError("Only completed payments can be refunded")

        # PayFast does not have an automated refund API — manual process
        from app.models.payment import Refund
        refund = Refund(
            payment_id=  payment_id,
            amount=      Decimal(payload.amount) / 100,
            reason=      payload.reason,
            gateway_ref= None,   # filled in manually after processing
            processed_by=admin_id,
        )
        self.db.add(refund)
        payment.status = PaymentStatus.refunded
        await self.db.commit()
        await self.db.refresh(refund)

        logger.info("refund_created", payment_id=str(payment_id), amount=payload.amount)
        return RefundResponse(
            refund_id=  refund.id,
            payment_id= payment_id,
            amount=     payload.amount,
            reason=     payload.reason,
            gateway_ref=None,
            created_at= refund.created_at,
        )

    # ── Gateway status ────────────────────────────────────────────────────────

    async def gateway_status(self) -> GatewayStatusResponse:
        pf_ok = bool(settings.PAYFAST_MERCHANT_ID and settings.PAYFAST_SECURED_KEY)
        return GatewayStatusResponse(
            payfast="configured" if pf_ok else "not_configured",
            cod="active",
        )
