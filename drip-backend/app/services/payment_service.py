"""Payment amounts use decimal PKR rupees, exactly as order totals do."""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal, InvalidOperation
from uuid import UUID, uuid4

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import BusinessRuleError, ExternalServiceError, NotFoundError
from app.core.public_urls import api_url, frontend_url
from app.integrations.payfast import PayFastClient, PayFastProtocolError
from app.models.order import Order, OrderStatus, PaymentMethod, SellerOrderStatus
from app.models.payment import Payment, PaymentCallback, PaymentStatus, Refund
from app.repositories.payment_repo import PaymentRepository
from app.schemas.payment import (
    AdminRefundDetailResponse,
    AdminRefundRowResponse,
    GatewayStatusResponse,
    PaginatedPayments,
    PaginatedRefunds,
    PayFastReconcileResponse,
    PaymentInitResponse,
    PaymentRefundHistoryResponse,
    PaymentRowResponse,
    PaymentStatusResponse,
    RefundAccountingResponse,
    RefundAllocationResponse,
    RefundHistoryEvent,
    RefundPaymentBalanceResponse,
    RefundRequest,
    RefundResponse,
    RetryPaymentRequest,
)
from app.services.notification_outbox import queue_notification
from app.services.order_access import authorized_order


def _build_payfast() -> PayFastClient:
    """Construct the configured PayFast adapter only when online payments are enabled."""
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


def _provider_money_matches(data: dict, amount: Decimal, currency: str) -> bool:
    """Require explicit, consistent monetary evidence from the authenticated API."""
    amounts = [data[key] for key in ("txnamt", "amount") if key in data]
    currencies = [data[key] for key in ("currency_code", "currency") if key in data]
    if not amounts or not currencies:
        return False
    try:
        values = [Decimal(str(value)) for value in amounts]
    except (InvalidOperation, ValueError):
        return False
    return all(value.is_finite() and value > 0 and value == amount for value in values) and all(
        isinstance(value, str) and value.strip().upper() == currency for value in currencies
    )


def _provider_outcome(status: str) -> str:
    """Recognize only explicit terminal states, never infer failure from an unknown code."""
    if status.upper() in {"00", "000", "SUCCESS", "COMPLETED", "PAID"}:
        return "completed"
    if status.upper() in {"FAILED", "DECLINED", "CANCELLED", "CANCELED"}:
        return "failed"
    return "unknown"


class PaymentService:
    def __init__(self, db: AsyncSession) -> None:
        """Bind PaymentService to its injected dependencies for subsequent operations."""
        self.db = db
        self.payment_repo = PaymentRepository(db)

    async def initiate(
        self,
        order_id: UUID,
        user_id: UUID | None = None,
        guest_token: str | None = None,
        customer_ip: str = "",
    ) -> PaymentInitResponse:
        """Validate the order and payment state before initiating the selected supported
        method.
        """
        order = await authorized_order(self.db, order_id, user_id, guest_token, lock=True)
        if order.payment_method.value not in {"payfast", "cod"}:
            raise BusinessRuleError("Historical payment methods cannot initiate new payments")
        if order.status not in (OrderStatus.pending_payment, OrderStatus.pending_cod_verification):
            raise BusinessRuleError("Order is not awaiting payment")
        payment = await self.payment_repo.get_by_order_id(order.id)
        if payment is not None:
            await self.db.refresh(payment)
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
        if payment.status != PaymentStatus.pending or payment.gateway_payload:
            raise BusinessRuleError(
                "An existing online attempt requires reconciliation before retry"
            )
        return await self._start_payfast(order, payment, user_id, guest_token, customer_ip, pf)

    async def _start_payfast(
        self,
        order: Order,
        payment: Payment,
        user_id: UUID | None,
        guest_token: str | None,
        customer_ip: str,
        pf: PayFastClient,
    ) -> PaymentInitResponse:
        """Persist a claim before provider I/O; ambiguity must never mint another attempt."""
        from app.models.user import User

        user = await self.db.get(User, user_id) if user_id else None
        customer_email = user.email if user else order.guest_email or ""
        customer_mobile = user.phone if user else order.guest_phone or ""
        if user and not customer_mobile and order.address:
            customer_mobile = order.address.phone
        attempt_id = uuid4()
        order_id, payment_id = order.id, payment.id
        order_date = (order.created_at or datetime.now(UTC)).date()
        request_data = {
            "basket_id": str(attempt_id),
            "amount": f"{order.total:.2f}",
            "currency": "PKR",
            "order_date": order_date.isoformat(),
            "customer_ip": customer_ip,
        }
        attempt = PaymentCallback(
            id=attempt_id,
            payment_id=payment_id,
            gateway="payfast_attempt",
            raw_payload={**request_data, "order_id": str(order_id), "state": "starting"},
            is_verified=False,
        )
        self.db.add(attempt)
        payment.gateway_payload = {
            "active_attempt_id": str(attempt_id),
            "checkout_request": request_data,
        }
        payment.status = PaymentStatus.pending
        payment.failure_reason = None
        amount, description = order.total, f"WearHowZ order {order.order_number}"
        await self.db.commit()
        try:
            token = await pf.get_checkout_token(basket_id=str(attempt_id), amount=amount)
            checkout = pf.build_checkout_payload(
                token=token,
                basket_id=str(attempt_id),
                amount=amount,
                description=description,
                success_url=frontend_url(f"/order/success/{order_id}"),
                failure_url=frontend_url(f"/payments/{order_id}", payment="failed"),
                checkout_url=api_url("/api/v1/payments/callback/payfast"),
                customer_email=customer_email,
                customer_mobile=customer_mobile,
                order_date=order_date,
            )
        except (httpx.HTTPError, PayFastProtocolError) as exc:
            raise ExternalServiceError("PayFast checkout is temporarily unavailable") from exc
        # Reacquire after the durable claim; cancellation/reconciliation may have run meanwhile.
        order = await authorized_order(self.db, order_id, user_id, guest_token, lock=True)
        await self.db.refresh(order)
        await self.db.refresh(payment)
        await self.db.refresh(attempt)
        if (
            order.status != OrderStatus.pending_payment
            or payment.status != PaymentStatus.pending
            or (payment.gateway_payload or {}).get("active_attempt_id") != str(attempt_id)
            or attempt.raw_payload.get("state") != "starting"
        ):
            raise BusinessRuleError("Payment changed during initiation; check its status")
        attempt.raw_payload = {**attempt.raw_payload, "state": "ready"}
        await self.db.commit()
        return PaymentInitResponse(
            payment_id=payment_id,
            attempt_id=attempt_id,
            method="payfast",
            checkout_url=pf.base_url,
            payfast_payload=checkout,
        )

    async def get_status(
        self, order_id: UUID, user_id: UUID | None = None, guest_token: str | None = None
    ) -> PaymentStatusResponse:
        """Read the authorized order's payment status for checkout polling."""
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
        """Validate retry eligibility and coordinate any permitted payment-method
        transition.
        """
        order = await authorized_order(self.db, order_id, user_id, guest_token, lock=True)
        if order.status != OrderStatus.pending_payment:
            raise BusinessRuleError("This order cannot be retried")
        payment = await self.payment_repo.get_by_order_id(order.id)
        if payment is not None:
            await self.db.refresh(payment)
        if payment and payment.method == "payfast":
            if payload.payment_method != PaymentMethod.payfast:
                raise BusinessRuleError(
                    "Online attempts cannot be switched to another payment method"
                )
            if payment.status != PaymentStatus.failed:
                raise BusinessRuleError("Unresolved or completed online payments cannot be retried")
            attempt = await self._active_attempt(payment)
            if (
                attempt is None
                or not attempt.is_verified
                or attempt.raw_payload.get("state") != "failed"
            ):
                raise BusinessRuleError(
                    "Provider-confirmed attempt failure is required before retry"
                )
            result = await self.reconcile_payfast(order.id, _commit=False)
            if (
                not result.matched
                or result.provider_status.upper()
                not in {"FAILED", "DECLINED", "CANCELLED", "CANCELED"}
                or result.local_status != "failed"
            ):
                # Preserve any newly discovered successful payment, without starting another.
                await self.db.commit()
                raise BusinessRuleError("Provider has not confirmed retry eligibility")
            return await self._start_payfast(
                order, payment, user_id, guest_token, customer_ip, _build_payfast()
            )
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

    async def _active_attempt(self, payment: Payment) -> PaymentCallback | None:
        """Legacy payments have no trusted attempt identity and cannot be auto-retried."""
        raw = (payment.gateway_payload or {}).get("active_attempt_id")
        if not raw:
            return None
        try:
            attempt_id = UUID(raw)
        except (TypeError, ValueError) as exc:
            raise BusinessRuleError(
                "Invalid payment attempt; manual reconciliation required"
            ) from exc
        attempt = await self.db.get(PaymentCallback, attempt_id)
        if not attempt or attempt.gateway != "payfast_attempt" or attempt.payment_id != payment.id:
            raise BusinessRuleError("Payment attempt unavailable; manual reconciliation required")
        await self.db.refresh(attempt)
        return attempt

    async def handle_payfast_callback(self, data: dict) -> None:
        """Validate callback identity and amount before provider-backed reconciliation."""
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

        callback_attempt = await self.db.get(PaymentCallback, order_id)
        if callback_attempt and callback_attempt.gateway == "payfast_attempt":
            linked_payment = await self.payment_repo.get_by_id(callback_attempt.payment_id)
            if not linked_payment:
                raise BusinessRuleError("Payment attempt unavailable")
            order_id = linked_payment.order_id
        repo = OrderRepository(self.db)
        order = await repo.get_by_id(order_id, for_update=True)
        payment = await self.payment_repo.get_by_order_id(order_id)
        if payment is not None:
            # Mapping a basket can cache the payment before waiting on the order lock.
            await self.db.refresh(payment)
        if not order or not payment or payment.method != "payfast":
            await self.db.commit()
            raise BusinessRuleError("Payment callback does not match an online payment")
        callback.payment_id = payment.id
        attempt = await self._active_attempt(payment)
        if attempt and (not callback_attempt or callback_attempt.id != attempt.id):
            await self.db.commit()
            raise BusinessRuleError("Stale payment attempt requires manual reconciliation")
        if (
            (parsed["amount"] is not None and parsed["amount"] != payment.amount)
            or (parsed.get("currency") is not None and parsed["currency"] != payment.currency)
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
            callback.is_verified = True
            await self.db.commit()
            return
        if order.status != OrderStatus.pending_payment:
            payment.failure_reason = "Late callback requires manual reconciliation"
            await self.db.commit()
            raise BusinessRuleError("Order requires payment reconciliation")
        if parsed["status"] in ("completed", "failed"):
            # The callback hash does not bind amount, currency or transaction ID.
            # Only the authenticated status API may authorize the paid transition.
            try:
                result = await self.reconcile_payfast(
                    order.id, expected_transaction_id=parsed["txn_id"], _commit=False
                )
            except (ExternalServiceError, BusinessRuleError):
                await self.db.commit()  # Retain the unverified callback attempt.
                raise
            if (
                not result.matched
                or result.local_status != parsed["status"]
                or _provider_outcome(result.provider_status) != parsed["status"]
            ):
                await self.db.commit()
                raise BusinessRuleError("Payment could not be confirmed by PayFast")
            callback.is_verified = True
        payment.gateway_payload = {**(payment.gateway_payload or {}), "callback": parsed["raw"]}
        await self.db.commit()

    async def reconcile_payfast(
        self, order_id: UUID, *, expected_transaction_id: str | None = None, _commit: bool = True
    ) -> PayFastReconcileResponse:
        """Reconcile a pending PayFast payment using the provider status API."""
        from app.repositories.order_repo import OrderRepository

        order_repo = OrderRepository(self.db)
        order = await order_repo.get_by_id(order_id, for_update=True)
        payment = await self.db.scalar(
            select(Payment)
            .where(Payment.order_id == order_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        if not order or not payment:
            raise NotFoundError("Payment not found")
        if payment.method != "payfast":
            raise BusinessRuleError("Only PayFast payments can be reconciled")
        attempt = await self._active_attempt(payment)
        basket_id = str(attempt.id) if attempt else str(order.id)

        request_data = (payment.gateway_payload or {}).get("checkout_request", {})
        raw_order_date = request_data.get("order_date")
        try:
            order_date = (
                date.fromisoformat(raw_order_date) if raw_order_date else order.created_at.date()
            )
        except (TypeError, ValueError) as exc:
            raise BusinessRuleError("Stored PayFast order date is invalid") from exc
        customer_ip = str(request_data.get("customer_ip") or "").strip()
        lookup_transaction_id = (
            payment.gateway_reference
            or expected_transaction_id
            or (attempt.raw_payload.get("transaction_id", "") if attempt else "")
        )
        if not lookup_transaction_id and not customer_ip:
            raise BusinessRuleError("Customer IP is missing; manual reconciliation is required")

        try:
            provider = await _build_payfast().check_status(
                basket_id=basket_id,
                order_date=order_date,
                customer_ip=customer_ip,
                transaction_id=lookup_transaction_id,
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
        status_values = [
            str(normalized[key]).strip()
            for key in ("status_code", "payment_status", "status", "code")
            if normalized.get(key) is not None and str(normalized[key]).strip()
        ]
        if len({_provider_outcome(value) for value in status_values}) > 1:
            provider_status = "AMBIGUOUS"
        provider_basket = str(normalized.get("basket_id") or "").strip()
        transaction_id = str(normalized.get("transaction_id") or "").strip()
        identifiers_match = provider_basket == basket_id and bool(transaction_id)
        if attempt and attempt.raw_payload.get("transaction_id") not in (None, "", transaction_id):
            identifiers_match = False
        if payment.gateway_reference and transaction_id != payment.gateway_reference:
            identifiers_match = False
        if expected_transaction_id and transaction_id != expected_transaction_id:
            identifiers_match = False
        duplicate = (
            await self.payment_repo.get_by_gateway_reference(transaction_id)
            if transaction_id
            else None
        )
        if duplicate is not None and duplicate.id != payment.id:
            identifiers_match = False
        evidence_matches = (
            identifiers_match
            and payment.amount == order.total
            and _provider_money_matches(normalized, payment.amount, payment.currency)
        )

        audit = PaymentCallback(
            payment_id=payment.id,
            gateway="payfast_reconciliation",
            raw_payload=provider,
            is_verified=evidence_matches,
        )
        self.db.add(audit)

        success = _provider_outcome(provider_status) == "completed"
        failed = _provider_outcome(provider_status) == "failed"
        detail = "Provider response recorded; no local state changed"
        if not evidence_matches:
            detail = "Provider identifiers, amount or currency did not match this payment"
        elif success:
            if payment.status in (PaymentStatus.completed, PaymentStatus.refunded):
                if payment.gateway_reference != transaction_id:
                    evidence_matches = False
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
                await queue_notification(
                    self.db,
                    f"order:{order.id}:status:payment_confirmed",
                    "send_order_status_update",
                    str(order.id),
                    OrderStatus.payment_confirmed.value,
                )
                detail = "Payment reconciled successfully"
            else:
                detail = "Paid transaction requires manual order-state review"
        elif failed and payment.status in (
            PaymentStatus.pending,
            PaymentStatus.processing,
            PaymentStatus.failed,
        ):
            payment.status = PaymentStatus.failed
            payment.failure_reason = str(
                normalized.get("status_msg") or "PayFast status API reported failure"
            )[:500]
            detail = "Payment marked failed from provider status"

        if (
            attempt
            and evidence_matches
            and (success or failed)
            and not (
                failed
                and (
                    attempt.raw_payload.get("state") == "completed"
                    or payment.status in (PaymentStatus.completed, PaymentStatus.refunded)
                )
            )
        ):
            # An older callback cannot overwrite the current attempt; resolution above is scoped.
            attempt.raw_payload = {
                **attempt.raw_payload,
                "state": "completed" if success else "failed",
                "transaction_id": transaction_id,
            }
            attempt.is_verified = True

        payment.gateway_payload = {
            **(payment.gateway_payload or {}),
            "last_reconciliation": provider,
        }
        if _commit:
            await self.db.commit()
        else:
            await self.db.flush()
        return PayFastReconcileResponse(
            order_id=order.id,
            payment_id=payment.id,
            provider_status=provider_status,
            local_status=payment.status.value,
            transaction_id=transaction_id or None,
            matched=evidence_matches,
            detail=detail,
        )

    async def refund(
        self,
        payment_id: UUID,
        admin_id: UUID,
        payload: RefundRequest,
        *,
        return_id: UUID | None = None,
        commit: bool = True,
    ) -> RefundResponse:
        """Create or reuse an idempotent refund request within the remaining refundable
        balance.
        """
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
                if return_id is not None:
                    if existing.return_id not in (None, return_id):
                        raise BusinessRuleError(
                            "Idempotency key is already linked to another return"
                        )
                    # Repair a request created by the former two-commit flow. The
                    # caller still owns the transaction and decides whether to commit.
                    if existing.return_id is None:
                        existing.return_id = return_id
                        if commit:
                            await self.db.commit()
                            await self.db.refresh(existing)
                        else:
                            await self.db.flush()
                return self._refund_response(existing)
        if payment.status != PaymentStatus.completed:
            raise BusinessRuleError("Only completed payments can be refunded")
        reserved = await self.payment_repo.get_total_refunded(payment.id)
        if payload.amount > payment.amount - reserved:
            raise BusinessRuleError("Refund exceeds the remaining refundable amount")
        refund = Refund(
            payment_id=payment.id,
            return_id=return_id,
            amount=payload.amount,
            reason=payload.reason,
            requested_by=admin_id,
            idempotency_key=payload.idempotency_key,
        )
        self.db.add(refund)
        # Requesting a manual refund never claims money has been transferred.
        if commit:
            await self.db.commit()
        else:
            await self.db.flush()
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
        """Convert a stored refund into its customer-facing response model."""
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

    async def list_admin_refunds(
        self, status: str | None = None, payment_id: UUID | None = None, page: int = 1
    ) -> PaginatedRefunds:
        """Paginate refunds with their administrative accounting summaries."""
        rows, total = await self.payment_repo.list_refunds_admin(
            status=status, payment_id=payment_id, page=page
        )
        return PaginatedRefunds(
            data=[self._refund_admin_row(refund) for refund in rows],
            total=total,
            page=page,
        )

    async def get_admin_refund(self, refund_id: UUID) -> AdminRefundDetailResponse:
        """Assemble refund details, history, balances, and seller reconciliation
        allocations.
        """
        refund = await self.payment_repo.get_refund_admin(refund_id)
        if not refund:
            raise NotFoundError("Refund not found")
        history = [
            RefundHistoryEvent(
                event="requested",
                occurred_at=refund.created_at,
                actor_id=refund.requested_by,
            )
        ]
        if refund.processed_at:
            history.append(
                RefundHistoryEvent(
                    event="completed",
                    occurred_at=refund.processed_at,
                    actor_id=refund.processed_by,
                    transfer_reference=refund.gateway_ref,
                )
            )
        return AdminRefundDetailResponse(
            **self._refund_admin_row(refund).model_dump(),
            payment=self._refund_payment_balance(refund.payment),
            history=history,
        )

    async def get_payment_refund_history(self, payment_id: UUID) -> PaymentRefundHistoryResponse:
        """Assemble the payment's refund history and remaining refundable balance."""
        payment = await self.payment_repo.get_payment_refunds(payment_id)
        if not payment:
            raise NotFoundError("Payment not found")
        refunds = sorted(
            payment.refunds,
            key=lambda refund: (refund.created_at, refund.id),
            reverse=True,
        )
        return PaymentRefundHistoryResponse(
            **self._refund_payment_balance(payment).model_dump(),
            refunds=[self._refund_admin_row(refund, payment) for refund in refunds],
        )

    @staticmethod
    def _refund_admin_row(refund: Refund, payment: Payment | None = None) -> AdminRefundRowResponse:
        """Serialize the refund and its seller-allocation accounting for administrator
        reads.
        """
        payment = payment or refund.payment
        accounting = refund.accounting
        accounting_response = None
        if accounting is not None:
            accounting_response = RefundAccountingResponse(
                merchandise_amount=accounting.merchandise_amount,
                shipping_amount=accounting.shipping_amount,
                commission_reversal_amount=accounting.commission_reversal_amount,
                seller_reversal_amount=accounting.seller_reversal_amount,
                recovered_amount=accounting.recovered_amount,
                settlement_offset_amount=accounting.settlement_offset_amount,
                platform_shortfall_amount=accounting.platform_shortfall_amount,
                platform_funded_amount=accounting.platform_funded_amount,
                reconciled=accounting.reconciled_at is not None,
                allocations=[
                    RefundAllocationResponse(
                        seller_order_id=row.seller_order_id,
                        seller_id=row.seller_id,
                        merchandise_amount=row.merchandise_amount,
                        commission_rate=row.commission_rate,
                        commission_reversal_amount=row.commission_reversal_amount,
                        seller_reversal_amount=row.seller_reversal_amount,
                        recovered_amount=row.recovered_amount,
                        settlement_offset_amount=row.settlement_offset_amount,
                        platform_shortfall_amount=row.platform_shortfall_amount,
                        reconciled=row.applied_at is not None,
                    )
                    for row in sorted(accounting.allocations, key=lambda value: value.id)
                ],
            )
        return AdminRefundRowResponse(
            refund_id=refund.id,
            payment_id=refund.payment_id,
            order_id=payment.order_id,
            order_number=payment.order.order_number,
            return_id=refund.return_id,
            status="completed" if refund.processed_at else "pending",
            amount=refund.amount,
            reason=refund.reason or "",
            transfer_reference=refund.gateway_ref,
            requested_by=refund.requested_by,
            confirmed_by=refund.processed_by if refund.processed_at else None,
            requested_at=refund.created_at,
            processed_at=refund.processed_at,
            accounting=accounting_response,
        )

    @staticmethod
    def _refund_payment_balance(payment: Payment) -> RefundPaymentBalanceResponse:
        """Calculate requested, confirmed, and remaining refund amounts for a payment."""
        pending = sum(
            (refund.amount for refund in payment.refunds if not refund.processed_at),
            Decimal("0"),
        )
        completed = sum(
            (refund.amount for refund in payment.refunds if refund.processed_at),
            Decimal("0"),
        )
        reserved = pending + completed
        remaining = max(payment.amount - reserved, Decimal("0"))
        return RefundPaymentBalanceResponse(
            payment_id=payment.id,
            order_id=payment.order_id,
            order_number=payment.order.order_number,
            payment_status=payment.status.value,
            payment_method=payment.method,
            payment_amount=payment.amount,
            pending_refund_amount=pending,
            completed_refund_amount=completed,
            reserved_refund_amount=reserved,
            remaining_refundable_amount=remaining,
            can_request_refund=(
                payment.status == PaymentStatus.completed and remaining > Decimal("0")
            ),
        )

    async def record_cod_collection(self, payment_id: UUID, admin_id: UUID, reference: str):
        """Confirm a delivered COD payment and settle eligible seller orders idempotently."""
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
        """Paginate payments for administrative reconciliation."""
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
        """Report supported payment-method availability from runtime configuration."""
        state = (
            "disabled_pending_verification"
            if not settings.PAYFAST_ENABLED
            else "configured"
            if settings.PAYFAST_MERCHANT_ID and settings.PAYFAST_SECURED_KEY
            else "not_configured"
        )
        return GatewayStatusResponse(payfast=state, cod="active")
