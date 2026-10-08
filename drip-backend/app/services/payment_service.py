"""Payment amounts use decimal PKR rupees, exactly as order totals do."""

from __future__ import annotations

from datetime import UTC, date, datetime
from uuid import UUID

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import BusinessRuleError, ExternalServiceError, NotFoundError
from app.integrations.payfast import PayFastClient, PayFastProtocolError
from app.models.order import OrderStatus, PaymentMethod, SellerOrderStatus
from app.models.payment import Payment, PaymentCallback, PaymentStatus, Refund
from app.repositories.payment_repo import PaymentRepository
from app.schemas.payment import (
    GatewayStatusResponse,
    PaginatedPayments,
    PayFastReconcileResponse,
    PaymentInitResponse,
    PaymentRowResponse,
    PaymentStatusResponse,
    RefundRequest,
    RefundResponse,
    RetryPaymentRequest,
)
from app.services.order_access import authorized_order


def _build_payfast() -> PayFastClient:
    if not settings.PAYFAST_ENABLED or not (
        settings.PAYFAST_MERCHANT_ID and settings.PAYFAST_SECURED_KEY
    ):
        raise ExternalServiceError("Online payments are not enabled")
    return PayFastClient(
        settings.PAYFAST_MERCHANT_ID,
        settings.PAYFAST_SECURED_KEY,
        settings.PAYFAST_MERCHANT_NAME,
        settings.PAYFAST_SANDBOX,
        token_url=settings.PAYFAST_TOKEN_URL,
        checkout_url=settings.PAYFAST_CHECKOUT_URL,
        api_base_url=settings.PAYFAST_API_BASE_URL,
        timeout_seconds=settings.PAYFAST_REQUEST_TIMEOUT_SECONDS,
    )


class PaymentService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.payment_repo = PaymentRepository(db)

    async def initiate(
        self,
        order_id: UUID,
        user_id: UUID | None = None,
        guest_token: str | None = None,
        customer_ip: str = "",
    ) -> PaymentInitResponse:
        order = await authorized_order(self.db, order_id, user_id, guest_token, lock=True)
        if order.status not in (OrderStatus.pending_payment, OrderStatus.pending_cod_verification):
            raise BusinessRuleError("Order is not awaiting payment")
        payment = await self.payment_repo.get_by_order_id(order.id)
        if payment and payment.status in (PaymentStatus.completed, PaymentStatus.refunded):
            raise BusinessRuleError("Payment has already completed")
        if payment is None:
            payment = await self.payment_repo.create(
                order_id=order.id,
                method=order.payment_method.value,
                amount=order.total,
                currency="PKR",
                status=PaymentStatus.pending,
            )
        if payment.amount != order.total or payment.method != order.payment_method.value:
            raise BusinessRuleError("Payment does not match this order; contact support")
        if order.payment_method == PaymentMethod.cod:
            await self.db.commit()
            return PaymentInitResponse(payment_id=payment.id, method="cod")
        pf = _build_payfast()
        from app.models.user import User

        user = await self.db.get(User, user_id) if user_id else None
        customer_email = user.email if user else order.guest_email or ""
        customer_mobile = user.phone if user else order.guest_phone or ""
        try:
            token = await pf.get_checkout_token(basket_id=str(order.id), amount=order.total)
            checkout = pf.build_checkout_payload(
                token=token,
                basket_id=str(order.id),
                amount=order.total,
                description=f"WearHowZ order {order.order_number}",
                success_url=f"{settings.FRONTEND_URL}/order/success/{order.id}",
                failure_url=f"{settings.FRONTEND_URL}/checkout?payment=failed",
                checkout_url=f"{settings.API_BASE_URL}/api/v1/payments/callback/payfast",
                customer_email=customer_email,
                customer_mobile=customer_mobile,
                order_date=(order.created_at or datetime.now(UTC)).date(),
            )
        except (httpx.HTTPError, PayFastProtocolError) as exc:
            raise ExternalServiceError("PayFast checkout is temporarily unavailable") from exc
        # Do not persist PayFast's one-time TOKEN or correlation SIGNATURE.
        payment.gateway_payload = {
            "checkout_request": {
                "basket_id": str(order.id),
                "amount": f"{order.total:.2f}",
                "currency": "PKR",
                "order_date": (order.created_at or datetime.now(UTC)).date().isoformat(),
                "customer_ip": customer_ip,
            }
        }
        payment.status = PaymentStatus.pending
        await self.db.commit()
        return PaymentInitResponse(
            payment_id=payment.id,
            method="payfast",
            checkout_url=pf.base_url,
            payfast_payload=checkout,
        )

    async def get_status(
        self, order_id: UUID, user_id: UUID | None = None, guest_token: str | None = None
    ) -> PaymentStatusResponse:
        await authorized_order(self.db, order_id, user_id, guest_token)
        payment = await self.payment_repo.get_by_order_id(order_id)
        if payment is None:
            raise NotFoundError("Payment not found")
        return PaymentStatusResponse(
            order_id=order_id,
            payment_id=payment.id,
            status=payment.status.value,
            method=payment.method,
            amount=payment.amount,
            gateway_reference=payment.gateway_reference,
            paid_at=payment.paid_at,
        )

    async def retry(
        self,
        order_id: UUID,
        user_id: UUID | None,
        payload: RetryPaymentRequest,
        guest_token: str | None = None,
        customer_ip: str = "",
    ) -> PaymentInitResponse:
        order = await authorized_order(self.db, order_id, user_id, guest_token, lock=True)
        if order.status != OrderStatus.pending_payment:
            raise BusinessRuleError("This order cannot be retried")
        payment = await self.payment_repo.get_by_order_id(order.id)
        if payment and payment.status not in (PaymentStatus.pending, PaymentStatus.failed):
            raise BusinessRuleError("This payment cannot be retried")
        if payment and payment.status == PaymentStatus.pending and payment.gateway_payload:
            if payload.payment_method.value != payment.method:
                raise BusinessRuleError(
                    "An online payment is still pending; its method cannot be changed"
                )
        if (
            payload.payment_method == PaymentMethod.cod
            and order.total > settings.MAX_COD_ORDER_AMOUNT
        ):
            raise BusinessRuleError("Order exceeds the COD limit")
        if payload.payment_method == PaymentMethod.payfast:
            _build_payfast()
        order.payment_method = payload.payment_method
        order.status = (
            OrderStatus.pending_cod_verification
            if payload.payment_method == PaymentMethod.cod
            else OrderStatus.pending_payment
        )
        if payment:
            payment.method = payload.payment_method.value
            if payment.status == PaymentStatus.failed:
                payment.gateway_payload = None
            payment.status = PaymentStatus.pending
            payment.failure_reason = None
        await self.db.flush()
        response = await self.initiate(order.id, user_id, guest_token, customer_ip)
        if order.payment_method == PaymentMethod.cod:
            from app.services.order_service import OrderService

            await OrderService(self.db)._enqueue_cod_timeout(str(order.id))
        return response

    async def handle_payfast_callback(self, data: dict) -> None:
        pf = _build_payfast()
        callback = PaymentCallback(gateway="payfast", raw_payload=data, is_verified=False)
        self.db.add(callback)
        try:
            parsed = pf.parse_callback(data)
            order_id = UUID(parsed["order_id"])
        except (ValueError, KeyError, TypeError):
            await self.db.commit()  # Persist rejected callback audit, without changing payment.
            raise BusinessRuleError("Invalid payment callback") from None
        from app.repositories.order_repo import OrderRepository

        repo = OrderRepository(self.db)
        order = await repo.get_by_id(order_id, for_update=True)
        payment = await self.payment_repo.get_by_order_id(order_id)
        callback.is_verified = True
        if not order or not payment or payment.method != "payfast":
            await self.db.commit()
            raise BusinessRuleError("Payment callback does not match an online payment")
        callback.payment_id = payment.id
        if (
            (parsed["amount"] is not None and parsed["amount"] != payment.amount)
            or parsed.get("currency") != payment.currency
            or payment.amount != order.total
            or not parsed["txn_id"]
        ):
            await self.db.commit()
            raise BusinessRuleError(
                "Payment callback does not match the expected amount or currency"
            )
        duplicate = await self.payment_repo.get_by_gateway_reference(parsed["txn_id"])
        if duplicate is not None and duplicate.id != payment.id:
            await self.db.commit()
            raise BusinessRuleError("Payment reference already belongs to another order")
        # Duplicate and delayed notifications cannot regress paid/fulfilled state.
        if payment.status in (PaymentStatus.completed, PaymentStatus.refunded):
            if payment.gateway_reference != parsed["txn_id"]:
                await self.db.commit()
                raise BusinessRuleError("Unexpected transaction reference")
            await self.db.commit()
            return
        if order.status != OrderStatus.pending_payment:
            payment.failure_reason = "Late callback requires manual reconciliation"
            await self.db.commit()
            raise BusinessRuleError("Order requires payment reconciliation")
        if parsed["status"] == "completed":
            payment.status = PaymentStatus.completed
            payment.gateway_reference = parsed["txn_id"]
            payment.paid_at = datetime.now(UTC)
            payment.failure_reason = None
            await repo.update_status(
                order.id, OrderStatus.payment_confirmed, note="Verified payment callback"
            )
        elif parsed["status"] == "failed":
            payment.status = PaymentStatus.failed
            detail = parsed.get("error_message") or "Gateway reported failure"
            payment.failure_reason = f"PayFast {parsed['error_code']}: {detail}"[:500]
        payment.gateway_payload = {**(payment.gateway_payload or {}), "callback": parsed["raw"]}
        await self.db.commit()

    async def reconcile_payfast(self, order_id: UUID) -> PayFastReconcileResponse:
        """Reconcile a pending PayFast payment using the provider status API."""
        from app.repositories.order_repo import OrderRepository

        order_repo = OrderRepository(self.db)
        order = await order_repo.get_by_id(order_id, for_update=True)
        payment = await self.db.scalar(
            select(Payment).where(Payment.order_id == order_id).with_for_update()
        )
        if not order or not payment:
            raise NotFoundError("Payment not found")
        if payment.method != "payfast":
            raise BusinessRuleError("Only PayFast payments can be reconciled")

        request_data = (payment.gateway_payload or {}).get("checkout_request", {})
        raw_order_date = request_data.get("order_date")
        try:
            order_date = (
                date.fromisoformat(raw_order_date) if raw_order_date else order.created_at.date()
            )
        except (TypeError, ValueError) as exc:
            raise BusinessRuleError("Stored PayFast order date is invalid") from exc
        customer_ip = str(request_data.get("customer_ip") or "").strip()
        if not payment.gateway_reference and not customer_ip:
            raise BusinessRuleError("Customer IP is missing; manual reconciliation is required")

        try:
            provider = await _build_payfast().check_status(
                basket_id=str(order.id),
                order_date=order_date,
                customer_ip=customer_ip,
                transaction_id=payment.gateway_reference or "",
            )
        except (httpx.HTTPError, PayFastProtocolError) as exc:
            raise ExternalServiceError("PayFast reconciliation is temporarily unavailable") from exc

        normalized = {str(key).lower(): value for key, value in provider.items()}
        provider_status = str(
            normalized.get("status_code")
            or normalized.get("payment_status")
            or normalized.get("status")
            or normalized.get("code")
            or "unknown"
        ).strip()
        provider_basket = str(normalized.get("basket_id") or "").strip()
        transaction_id = str(normalized.get("transaction_id") or "").strip()
        identifiers_match = provider_basket == str(order.id) and bool(transaction_id)
        if payment.gateway_reference and transaction_id != payment.gateway_reference:
            identifiers_match = False
        duplicate = (
            await self.payment_repo.get_by_gateway_reference(transaction_id)
            if transaction_id
            else None
        )
        if duplicate is not None and duplicate.id != payment.id:
            identifiers_match = False

        audit = PaymentCallback(
            payment_id=payment.id,
            gateway="payfast_reconciliation",
            raw_payload=provider,
            is_verified=identifiers_match,
        )
        self.db.add(audit)

        status_key = provider_status.upper()
        success = status_key in {"00", "000", "SUCCESS", "COMPLETED", "PAID"}
        failed = status_key in {"FAILED", "DECLINED", "CANCELLED", "CANCELED"}
        detail = "Provider response recorded; no local state changed"
        if not identifiers_match:
            detail = "Provider identifiers did not match this payment"
        elif success:
            if payment.status in (PaymentStatus.completed, PaymentStatus.refunded):
                if payment.gateway_reference != transaction_id:
                    identifiers_match = False
                    audit.is_verified = False
                    detail = "Completed payment has a different transaction reference"
                else:
                    detail = "Payment was already reconciled"
            elif order.status == OrderStatus.pending_payment:
                payment.status = PaymentStatus.completed
                payment.gateway_reference = transaction_id
                payment.paid_at = datetime.now(UTC)
                payment.failure_reason = None
                await order_repo.update_status(
                    order.id,
                    OrderStatus.payment_confirmed,
                    note="Verified using PayFast status API",
                )
                detail = "Payment reconciled successfully"
            else:
                detail = "Paid transaction requires manual order-state review"
        elif failed and payment.status == PaymentStatus.pending:
            payment.status = PaymentStatus.failed
            payment.failure_reason = str(
                normalized.get("status_msg") or "PayFast status API reported failure"
            )[:500]
            detail = "Payment marked failed from provider status"

        payment.gateway_payload = {
            **(payment.gateway_payload or {}),
            "last_reconciliation": provider,
        }
        await self.db.commit()
        return PayFastReconcileResponse(
            order_id=order.id,
            payment_id=payment.id,
            provider_status=provider_status,
            local_status=payment.status.value,
            transaction_id=transaction_id or None,
            matched=identifiers_match,
            detail=detail,
        )

    async def refund(
        self, payment_id: UUID, admin_id: UUID, payload: RefundRequest
    ) -> RefundResponse:
        payment = await self.db.scalar(
            select(Payment).where(Payment.id == payment_id).with_for_update()
        )
        if not payment:
            raise NotFoundError("Payment not found")
        if payload.idempotency_key:
            existing = await self.db.scalar(
                select(Refund).where(
                    Refund.payment_id == payment_id,
                    Refund.idempotency_key == payload.idempotency_key,
                )
            )
            if existing:
                if existing.amount != payload.amount or existing.reason != payload.reason:
                    raise BusinessRuleError(
                        "Idempotency key was already used with different refund details"
                    )
                return self._refund_response(existing)
        if payment.status != PaymentStatus.completed:
            raise BusinessRuleError("Only completed payments can be refunded")
        reserved = await self.payment_repo.get_total_refunded(payment.id)
        if payload.amount > payment.amount - reserved:
            raise BusinessRuleError("Refund exceeds the remaining refundable amount")
        refund = Refund(
            payment_id=payment.id,
            amount=payload.amount,
            reason=payload.reason,
            processed_by=admin_id,
            idempotency_key=payload.idempotency_key,
        )
        self.db.add(refund)
        # Requesting a manual refund never claims money has been transferred.
        await self.db.commit()
        await self.db.refresh(refund)
        return self._refund_response(refund)

    async def confirm_refund(
        self, refund_id: UUID, admin_id: UUID, reference: str
    ) -> RefundResponse:
        """Confirm a refund with a given reference."""
        refund = await self.db.get(Refund, refund_id)
        if not refund:
            raise NotFoundError("Refund not found")
        payment = await self.db.scalar(
            select(Payment).where(Payment.id == refund.payment_id).with_for_update()
        )
        await self.db.refresh(refund)
        if refund.processed_at:
            if refund.gateway_ref != reference:
                raise BusinessRuleError("Refund already confirmed with a different reference")
            return self._refund_response(refund)

        # ── Step 1: inventory restock and return status ───────────────────────
        returned = None
        if refund.return_id:
            from sqlalchemy import update

            from app.models.order import OrderItem
            from app.models.product import ProductInventory
            from app.models.return_ import ReturnStatus
            from app.repositories.return_repo import ReturnRepository

            returned = await ReturnRepository(self.db).get_by_id(refund.return_id)
            if returned and returned.status == ReturnStatus.received:
                for item in returned.items:
                    order_item = await self.db.get(OrderItem, item.order_item_id)
                    await self.db.execute(
                        update(ProductInventory)
                        .where(ProductInventory.variant_id == order_item.variant_id)
                        .values(stock=ProductInventory.stock + item.quantity)
                    )
                returned.status = ReturnStatus.refunded
                returned.resolved_at = datetime.now(UTC)

        # ── Step 2: mark refund as confirmed ─────────────────────────────────
        refund.gateway_ref = reference
        refund.processed_at = datetime.now(UTC)
        refund.processed_by = admin_id
        await self.db.flush()

        # ── Step 3: reverse seller earnings (idempotent, best-effort) ─────────
        # All mutations are in the same transaction so either all commit or none do.
        from app.services.commission_service import CommissionService

        comm = CommissionService(self.db)
        if returned is not None:
            # Return-linked refund: reverse exactly this seller_order's ledger.
            await comm.reverse_for_refund(
                refund.id,
                seller_order_id=returned.seller_order_id,
                refund_amount=refund.amount,
                commit=False,
            )
        else:
            # Direct admin refund: split proportionally across all settled sellers.
            await comm.reverse_for_refund(
                refund.id,
                order_id=payment.order_id,
                refund_amount=refund.amount,
                commit=False,
            )

        # ── Step 4: mark payment fully refunded when total confirmed ──────────
        from sqlalchemy import func

        confirmed = await self.db.scalar(
            select(func.coalesce(func.sum(Refund.amount), 0)).where(
                Refund.payment_id == payment.id, Refund.processed_at.is_not(None)
            )
        )
        if confirmed >= payment.amount:
            payment.status = PaymentStatus.refunded

        await self.db.commit()
        return self._refund_response(refund)

    @staticmethod
    def _refund_response(refund: Refund) -> RefundResponse:
        return RefundResponse(
            refund_id=refund.id,
            payment_id=refund.payment_id,
            amount=refund.amount,
            reason=refund.reason or "",
            gateway_ref=refund.gateway_ref,
            created_at=refund.created_at,
            status="completed" if refund.processed_at else "pending",
            processed_at=refund.processed_at,
        )

    async def record_cod_collection(self, payment_id: UUID, admin_id: UUID, reference: str):
        payment = await self.db.get(Payment, payment_id)
        if not payment:
            raise NotFoundError("Payment not found")
        from app.repositories.order_repo import OrderRepository

        order = await OrderRepository(self.db).get_by_id(payment.order_id, for_update=True)
        await self.db.refresh(payment)
        if payment.method != "cod" or order.status not in (
            OrderStatus.delivered,
            OrderStatus.completed,
        ):
            raise BusinessRuleError("COD collection can only be recorded after delivery")
        if payment.status == PaymentStatus.completed:
            if payment.gateway_reference != reference:
                raise BusinessRuleError(
                    "Collection was already recorded with a different reference"
                )
            return {"status": "completed"}
        if payment.status != PaymentStatus.pending:
            raise BusinessRuleError("Payment cannot be collected in its current state")
        payment.status = PaymentStatus.completed
        payment.paid_at = datetime.now(UTC)
        payment.gateway_reference = reference
        from app.services.commission_service import CommissionService

        for seller_order in order.seller_orders:
            if seller_order.status == SellerOrderStatus.delivered:
                await CommissionService(self.db).settle(seller_order.id, commit=False)
        await self.db.commit()
        return {"status": "completed"}

    async def list_admin(self, **filters) -> PaginatedPayments:
        rows, total = await self.payment_repo.list_admin(**filters)
        return PaginatedPayments(
            data=[
                PaymentRowResponse(
                    id=p.id,
                    order_id=p.order_id,
                    order_number=p.order.order_number,
                    method=p.method,
                    status=p.status.value,
                    amount=p.amount,
                    gateway_reference=p.gateway_reference,
                    paid_at=p.paid_at,
                    created_at=p.created_at,
                )
                for p in rows
            ],
            total=total,
            page=filters.get("page", 1),
        )

    async def gateway_status(self) -> GatewayStatusResponse:
        state = (
            "disabled_pending_verification"
            if not settings.PAYFAST_ENABLED
            else "configured"
            if settings.PAYFAST_MERCHANT_ID and settings.PAYFAST_SECURED_KEY
            else "not_configured"
        )
        return GatewayStatusResponse(payfast=state, cod="active")
