from __future__ import annotations

from decimal import Decimal
from uuid import UUID
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import (
    NotFoundError, BusinessRuleError, PermissionDeniedError, ExternalServiceError
)
from app.models.payment import Payment, PaymentStatus
from app.models.order import Order, OrderStatus, PaymentMethod
from app.repositories.payment_repo import PaymentRepository
from app.repositories.order_repo import OrderRepository
from app.integrations.jazzcash import JazzCashClient
from app.integrations.easypaisa import EasypaisaClient
from app.integrations.stripe_client import StripeClient
from app.schemas.payment import (
    PaymentInitResponse, PaymentStatusResponse,
    RetryPaymentRequest, RefundRequest, RefundResponse,
    GatewayStatusResponse,
)


def _build_jazzcash() -> JazzCashClient:
    return JazzCashClient(
        merchant_id    = settings.JAZZCASH_MERCHANT_ID,
        password       = settings.JAZZCASH_PASSWORD,
        integrity_salt = settings.JAZZCASH_INTEGRITY_SALT,
        sandbox        = getattr(settings, "JAZZCASH_SANDBOX", True),
    )


def _build_easypaisa() -> EasypaisaClient:
    return EasypaisaClient(
        store_id   = settings.EASYPAISA_STORE_ID,
        store_key  = settings.EASYPAISA_STORE_KEY,
        account_no = settings.EASYPAISA_ACCOUNT_NO,
        sandbox    = getattr(settings, "EASYPAISA_SANDBOX", True),
    )


def _build_stripe() -> StripeClient:
    return StripeClient(
        secret_key     = settings.STRIPE_SECRET_KEY,
        webhook_secret = settings.STRIPE_WEBHOOK_SECRET,
    )


RETRYABLE_ORDER_STATUSES = {OrderStatus.pending_payment}
REFUNDABLE_PAYMENT_STATUSES = {PaymentStatus.completed}


class PaymentService:
    def __init__(self, db: AsyncSession) -> None:
        self.db           = db
        self.payment_repo = PaymentRepository(db)
        self.order_repo   = OrderRepository(db)

    # ── Initiate ──────────────────────────────────────────────────────────────

    async def initiate(
        self, order_id: UUID, user_id: UUID
    ) -> PaymentInitResponse:
        order = await self.order_repo.get_by_id(order_id, user_id=user_id)
        if not order:
            raise NotFoundError("Order not found")
        if order.status not in (OrderStatus.pending_payment, OrderStatus.pending_cod_verification):
            raise BusinessRuleError(
                f"Order is not awaiting payment (status: {order.status.value})"
            )

        # Check if payment already exists and is pending
        existing = await self.payment_repo.get_by_order_id(order_id)
        if existing and existing.status == PaymentStatus.completed:
            raise BusinessRuleError("Payment already completed for this order")

        method = PaymentMethod(order.payment_method)
        amount = order.total

        # Create Payment record
        payment = await self.payment_repo.create(
            order_id = order_id,
            method   = method.value,
            status   = PaymentStatus.pending,
            amount   = amount,
        )

        payment_url          = None
        stripe_client_secret = None

        if method == PaymentMethod.jazzcash:
            jc     = _build_jazzcash()
            phone  = order.address.phone if order.address else ""
            result = await jc.initiate_wallet_payment(
                order_number = order.order_number,
                amount_pkr   = int(amount),
                mobile       = phone,
            )
            payment_url = result.get("payment_url")
            await self.payment_repo.update_status(
                payment.id,
                PaymentStatus.processing,
                gateway_reference=result["txn_ref"],
            )

        elif method == PaymentMethod.easypaisa:
            ep     = _build_easypaisa()
            email  = order.guest_email or ""
            result = await ep.initiate_payment(
                order_number = order.order_number,
                amount_pkr   = int(amount),
                email        = email,
            )
            payment_url = result.get("payment_url")
            await self.payment_repo.update_status(
                payment.id,
                PaymentStatus.processing,
                gateway_reference=result["order_ref"],
            )

        elif method == PaymentMethod.card:
            sc     = _build_stripe()
            result = await sc.create_payment_intent(
                amount_pkr   = int(amount),
                order_id     = str(order_id),
                order_number = order.order_number,
            )
            stripe_client_secret = result["client_secret"]
            await self.payment_repo.update_status(
                payment.id,
                PaymentStatus.processing,
                gateway_reference=result["payment_intent_id"],
            )

        elif method == PaymentMethod.cod:
            # COD — no external payment needed
            payment_url = None

        await self.db.commit()

        from datetime import timedelta
        return PaymentInitResponse(
            payment_id           = payment.id,
            method               = method.value,
            payment_url          = payment_url,
            stripe_client_secret = stripe_client_secret,
            expires_at           = datetime.now(timezone.utc) + timedelta(minutes=30),
        )

    # ── Callbacks ─────────────────────────────────────────────────────────────

    async def handle_jazzcash_callback(self, form_data: dict) -> None:
        """Process JazzCash POST callback — always responds 200 to gateway."""
        jc         = _build_jazzcash()
        verified   = jc.verify_callback(dict(form_data))
        txn_ref    = form_data.get("pp_TxnRefNo", "")
        resp_code  = form_data.get("pp_ResponseCode", "")

        payment = await self.payment_repo.get_by_gateway_reference(txn_ref)
        await self.payment_repo.log_callback(
            gateway    = "jazzcash",
            raw_payload= dict(form_data),
            payment_id = payment.id if payment else None,
            is_verified= verified,
        )

        if not verified or not payment:
            await self.db.commit()
            return

        if jc.is_success(resp_code):
            await self._confirm_payment(payment, gateway_payload=dict(form_data))
        else:
            await self._fail_payment(
                payment,
                reason=f"JazzCash declined: {resp_code}",
                gateway_payload=dict(form_data),
            )
        await self.db.commit()

    async def handle_easypaisa_callback(self, data: dict) -> None:
        ep         = _build_easypaisa()
        data_copy  = dict(data)
        verified   = ep.verify_callback(data_copy)
        resp_code  = data.get("responseCode", "")
        order_ref  = data.get("orderId", "")

        payment = await self.payment_repo.get_by_gateway_reference(order_ref)
        await self.payment_repo.log_callback(
            gateway    = "easypaisa",
            raw_payload= data,
            payment_id = payment.id if payment else None,
            is_verified= verified,
        )

        if not verified or not payment:
            await self.db.commit()
            return

        if ep.is_success(resp_code):
            await self._confirm_payment(payment, gateway_payload=data)
        else:
            await self._fail_payment(
                payment,
                reason=f"Easypaisa declined: {resp_code}",
                gateway_payload=data,
            )
        await self.db.commit()

    async def handle_stripe_webhook(self, payload: bytes, signature: str) -> None:
        sc = _build_stripe()
        try:
            event = sc.verify_webhook(payload, signature)
        except Exception:
            return  # Invalid signature — silently discard

        event_type       = event.get("type", "")
        payment_intent_id = sc.get_payment_intent_id(event)
        order_id         = sc.get_order_id_from_event(event)

        if not payment_intent_id:
            return

        payment = await self.payment_repo.get_by_gateway_reference(payment_intent_id)
        await self.payment_repo.log_callback(
            gateway    = "stripe",
            raw_payload= event,
            payment_id = payment.id if payment else None,
            is_verified= True,
        )

        if not payment:
            await self.db.commit()
            return

        if event_type == "payment_intent.succeeded":
            await self._confirm_payment(payment, gateway_payload=event)
        elif event_type in ("payment_intent.payment_failed", "payment_intent.canceled"):
            failure_msg = event.get("data", {}).get("object", {}).get("last_payment_error", {}).get("message", "")
            await self._fail_payment(payment, reason=failure_msg, gateway_payload=event)

        await self.db.commit()

    # ── Status ────────────────────────────────────────────────────────────────

    async def get_status(
        self, order_id: UUID, user_id: UUID
    ) -> PaymentStatusResponse:
        order = await self.order_repo.get_by_id(order_id, user_id=user_id)
        if not order:
            raise NotFoundError("Order not found")

        payment = await self.payment_repo.get_by_order_id(order_id)
        if not payment:
            raise NotFoundError("Payment not found for this order")

        return PaymentStatusResponse(
            order_id          = order_id,
            payment_id        = payment.id,
            status            = payment.status.value,
            method            = payment.method,
            amount            = int(payment.amount),
            gateway_reference = payment.gateway_reference,
            paid_at           = payment.paid_at,
        )

    # ── Retry ─────────────────────────────────────────────────────────────────

    async def retry(
        self,
        order_id: UUID,
        user_id:  UUID,
        payload:  RetryPaymentRequest,
    ) -> PaymentInitResponse:
        order = await self.order_repo.get_by_id(order_id, user_id=user_id)
        if not order:
            raise NotFoundError("Order not found")
        if order.status not in RETRYABLE_ORDER_STATUSES:
            raise BusinessRuleError(
                f"Order cannot be retried at status '{order.status.value}'"
            )

        # Mark existing payment as failed
        existing = await self.payment_repo.get_by_order_id(order_id)
        if existing and existing.status != PaymentStatus.failed:
            await self.payment_repo.update_status(existing.id, PaymentStatus.failed)

        # Update order payment method if changed
        if payload.payment_method != order.payment_method.value:
            from sqlalchemy import update as sa_update
            from app.models.order import Order as OrderModel
            await self.db.execute(
                sa_update(OrderModel)
                .where(OrderModel.id == order_id)
                .values(payment_method=PaymentMethod(payload.payment_method))
            )
            await self.db.flush()

        await self.db.commit()
        return await self.initiate(order_id, user_id)

    # ── Admin refund ──────────────────────────────────────────────────────────

    async def refund(
        self,
        payment_id:  UUID,
        admin_id:    UUID,
        payload:     RefundRequest,
    ) -> RefundResponse:
        payment = await self.payment_repo.get_by_id(payment_id)
        if not payment:
            raise NotFoundError("Payment not found")
        if payment.status not in REFUNDABLE_PAYMENT_STATUSES:
            raise BusinessRuleError("Only completed payments can be refunded")

        already_refunded = await self.payment_repo.get_total_refunded(payment_id)
        refundable       = payment.amount - already_refunded
        if Decimal(payload.amount) > refundable:
            raise BusinessRuleError(
                f"Cannot refund PKR {payload.amount:,}. "
                f"Maximum refundable: PKR {int(refundable):,}"
            )

        gateway_ref = None
        # Gateway-specific refund — only Stripe supported immediately
        if payment.method == "card" and payment.gateway_reference:
            try:
                sc     = _build_stripe()
                result = stripe.Refund.create(
                    payment_intent = payment.gateway_reference,
                    amount         = payload.amount * 100,
                )
                gateway_ref = result.id
            except Exception as e:
                raise ExternalServiceError(f"Stripe refund failed: {e}") from e

        refund = await self.payment_repo.create_refund(
            payment_id   = payment_id,
            amount       = Decimal(payload.amount),
            reason       = payload.reason,
            gateway_ref  = gateway_ref,
            processed_by = admin_id,
            processed_at = datetime.utcnow(),
        )
        await self.db.commit()

        return RefundResponse(
            refund_id  = refund.id,
            payment_id = payment_id,
            amount     = payload.amount,
            reason     = payload.reason,
            gateway_ref= gateway_ref,
            created_at = refund.created_at,
        )

    # ── Gateway health ────────────────────────────────────────────────────────

    async def gateway_status(self) -> GatewayStatusResponse:
        """Quick connectivity check for each gateway."""
        results = {}
        for name in ("jazzcash", "easypaisa", "stripe"):
            try:
                async with __import__("httpx").AsyncClient(timeout=5) as c:
                    if name == "stripe":
                        await c.get("https://api.stripe.com/v1")
                    elif name == "jazzcash":
                        await c.get("https://sandbox.jazzcash.com.pk")
                    else:
                        await c.get("https://easypaisa.com.pk")
                results[name] = "ok"
            except Exception:
                results[name] = "down"
        return GatewayStatusResponse(**results)

    # ── Internal helpers ──────────────────────────────────────────────────────

    async def _confirm_payment(
        self, payment: Payment, gateway_payload: Optional[dict] = None
    ) -> None:
        await self.payment_repo.update_status(
            payment.id,
            PaymentStatus.completed,
            gateway_payload=gateway_payload,
            paid_at=datetime.utcnow(),
        )
        await self.order_repo.update_status(
            payment.order_id,
            OrderStatus.payment_confirmed,
            note="Payment confirmed by gateway",
        )
        # Commission settlement triggered in Block 7

    async def _fail_payment(
        self,
        payment: Payment,
        reason: str = "",
        gateway_payload: Optional[dict] = None,
    ) -> None:
        await self.payment_repo.update_status(
            payment.id,
            PaymentStatus.failed,
            failure_reason=reason,
            gateway_payload=gateway_payload,
        )