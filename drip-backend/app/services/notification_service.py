"""services / notification service.

Business operations connecting API handlers, persistence, and provider integrations.
"""

from __future__ import annotations

import uuid
from html import escape
from typing import Optional
from urllib.parse import urlencode
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ExternalServiceError
from app.core.money import format_pkr
from app.core.public_urls import frontend_url
from app.models.notification import Notification
from app.models.user import User, UserRole
from app.repositories.notification_repo import NotificationRepository, EmailLogRepository
from app.schemas.notification import (
    NotificationListResponse,
    NotificationResponse,
    NotificationPreferencesResponse,
    UpdatePreferencesRequest,
    BroadcastRequest,
    BroadcastResponse,
    EmailLogResponse,
)

# ── Notification types ────────────────────────────────────────────────────────


class NotifType:
    ORDER_PLACED = "order_placed"
    ORDER_CONFIRMED = "order_confirmed"
    ORDER_SHIPPED = "order_shipped"
    ORDER_DELIVERED = "order_delivered"
    ORDER_CANCELLED = "order_cancelled"
    PAYOUT_DONE = "payout_completed"
    SELLER_APPROVED = "seller_approved"
    SELLER_REJECTED = "seller_rejected"
    NEW_REVIEW = "new_review"
    LOW_STOCK = "low_stock"
    BROADCAST = "broadcast"


class NotificationService:
    def __init__(self, db: AsyncSession) -> None:
        """Bind NotificationService to its injected dependencies for subsequent operations."""
        self.db = db
        self.repo = NotificationRepository(db)
        self.log_repo = EmailLogRepository(db)

    # ── In-app notifications ───────────────────────────────────────────────────

    async def create(
        self,
        user_id: UUID,
        type: str,
        title: str,
        body: str,
        action_url: Optional[str] = None,
        event_key: Optional[str] = None,
    ) -> Notification | None:
        """Persist an in-app notification, using a deterministic ID when delivery is
        deduplicated.
        """
        user = await self.db.scalar(select(User).where(User.id == user_id).with_for_update()
                                    .execution_options(populate_existing=True))
        if user is None or user.deleted_at is not None:
            return None
        if event_key:
            notification_id = uuid.uuid5(
                uuid.NAMESPACE_URL, f"wearhowz:notification:{event_key}:{user_id}"
            )
            return await self.repo.create_once(
                notification_id,
                user_id=user_id,
                type=type,
                title=title,
                body=body,
                action_url=action_url,
            )
        return await self.repo.create(
            user_id=user_id,
            type=type,
            title=title,
            body=body,
            action_url=action_url,
        )

    async def list_notifications(
        self,
        user_id: UUID,
        unread_only: bool = False,
        page: int = 1,
        per_page: int = 20,
    ) -> NotificationListResponse:
        """Return the user's notification page and unread count."""
        rows, total = await self.repo.list_by_user(user_id, unread_only, page, per_page)
        unread_count = await self.repo.unread_count(user_id)
        return NotificationListResponse(
            data=[NotificationResponse.model_validate(n) for n in rows],
            unread_count=unread_count,
            total=total,
            page=page,
        )

    async def mark_read(self, notification_id: UUID, user_id: UUID) -> bool:
        """Mark an owned notification read through the notification repository."""
        result = await self.repo.mark_read(notification_id, user_id)
        await self.db.commit()
        return result

    async def mark_all_read(self, user_id: UUID) -> int:
        """Mark all of the user's unread notifications through the repository."""
        count = await self.repo.mark_all_read(user_id)
        await self.db.commit()
        return count

    # ── Preferences ───────────────────────────────────────────────────────────

    async def get_preferences(
        self, user_id: UUID, *, commit: bool = True
    ) -> NotificationPreferencesResponse:
        """Load the user's canonical notification preferences for delivery decisions."""
        from app.services.legacy_preferences import import_legacy_preferences

        prefs = await import_legacy_preferences(self.db, user_id)
        if commit:
            await self.db.commit()
        return NotificationPreferencesResponse.model_validate(prefs)

    async def update_preferences(
        self, user_id: UUID, payload: UpdatePreferencesRequest
    ) -> NotificationPreferencesResponse:
        """Persist supported delivery-preference updates and return the canonical response."""
        updates = {k: v for k, v in payload.model_dump().items() if v is not None}
        from app.services.legacy_preferences import import_legacy_preferences

        await import_legacy_preferences(self.db, user_id)
        prefs = await self.repo.upsert_preferences(user_id, **updates)
        await self.db.commit()
        return NotificationPreferencesResponse.model_validate(prefs)

    # ── Email sending ─────────────────────────────────────────────────────────

    async def send_email(
        self,
        to: str,
        subject: str,
        html: str,
        template_id: Optional[str] = None,
        delivery_key: Optional[str] = None,
    ) -> str | None:
        """Send and durably log email; failures deliberately reach ARQ retry."""
        entry = (
            await self.log_repo.get_by_delivery_key(delivery_key)
            if delivery_key
            else None
        )
        if entry and entry.status == "sent":
            return entry.resend_id
        if entry is None:
            entry = await self.log_repo.create(
                recipient_email=to,
                subject=subject,
                template_id=template_id,
                status="pending",
                resend_id=None,
                error_message=None,
                delivery_key=delivery_key,
                attempts=0,
            )
        entry.attempts += 1
        try:
            from app.integrations.resend_client import ResendClient

            client = ResendClient()
            entry.resend_id = await client.send(to=to, subject=subject, html=html)
        except Exception as exc:
            entry.status = "failed"
            entry.error_message = str(exc)[:2000]
            await self.db.commit()
            raise ExternalServiceError("Email delivery is temporarily unavailable") from exc
        entry.status = "sent"
        entry.error_message = None
        await self.db.commit()
        return entry.resend_id

    # ── Order emails ──────────────────────────────────────────────────────────

    async def notify_order_placed(
        self, order_id: UUID, event_key: Optional[str] = None
    ) -> None:
        """Create order-confirmation notifications and email from persisted order details."""
        from sqlalchemy.orm import selectinload
        from app.models.order import Order

        result = await self.db.execute(
            select(Order)
            .options(
                selectinload(Order.items),
                selectinload(Order.address),
                selectinload(Order.seller_orders),
            )
            .where(Order.id == order_id)
        )
        order = result.scalar_one_or_none()
        if not order:
            return
        event_key = event_key or f"order:{order.id}:placed"
        if order.user_id:
            user = await self.db.scalar(select(User).where(User.id == order.user_id).with_for_update()
                                        .execution_options(populate_existing=True))
            if user is None or user.deleted_at is not None:
                return

        # In-app notification
        if order.user_id:
            await self.create(
                user_id=order.user_id,
                type=NotifType.ORDER_PLACED,
                title=f"Order #{order.order_number} placed",
                body=f"Your order of PKR {format_pkr(order.total)} has been received.",
                action_url=f"/orders/{order.id}",
                event_key=f"{event_key}:in_app",
            )

        # Email
        recipient = order.guest_email or ""
        if order.user_id:
            user_result = await self.db.execute(select(User).where(User.id == order.user_id))
            user = user_result.scalar_one_or_none()
            recipient = user.email if user else ""

        if recipient:
            items_html = "".join(
                f"<tr><td>{escape(i.product_name)} &mdash; {escape(i.variant_label)}</td>"
                f"<td style='text-align:right'>PKR {format_pkr(i.unit_price)} × {i.quantity}</td>"
                f"<td style='text-align:right'>PKR {format_pkr(i.subtotal)}</td></tr>"
                for i in order.items
            )
            tracking_url = frontend_url(f"/orders/{order.id}")
            if order.user_id is None:
                from app.services.order_access import create_guest_token

                tracking_url = (
                    f"{tracking_url}?"
                    f"{urlencode({'guest_token': create_guest_token(order.id)})}"
                )
            order_number = escape(order.order_number)
            payment_method = escape(order.payment_method.value.upper())
            html = f"""
            <h2>Order Confirmed &mdash; #{order_number}</h2>
            <p>Thank you for your order! Here's your summary:</p>
            <table width="100%">
              <thead><tr><th>Item</th><th>Price</th><th>Subtotal</th></tr></thead>
              <tbody>{items_html}</tbody>
            </table>
            <p><strong>Shipping fee:</strong> PKR {format_pkr(order.shipping_fee)}</p>
            <p><strong>Total:</strong> PKR {format_pkr(order.total)}</p>
            <p>Payment method: {payment_method}</p>
            <p><a href="{escape(tracking_url, quote=True)}">Track your order &rarr;</a></p>
            """
            await self.send_email(
                to=recipient,
                subject=f"WearHowZ Order #{order.order_number} Confirmed",
                html=html,
                template_id="order_placed",
                delivery_key=f"{event_key}:email",
            )
        await self.db.commit()

    async def notify_order_status(
        self, order_id: UUID, new_status: str, event_key: Optional[str] = None
    ) -> None:
        """Apply delivery preferences to an order-status notification and email."""
        from app.models.order import Order

        result = await self.db.execute(select(Order).where(Order.id == order_id))
        order = result.scalar_one_or_none()
        if not order:
            return
        event_key = event_key or f"order:{order.id}:status:{new_status}"

        status_messages = {
            "payment_confirmed": (
                "Payment confirmed ✓",
                "Your payment has been received and your order is being prepared.",
            ),
            "processing": ("Order being prepared 📦", "Sellers are packing your items."),
            "shipped": ("Your order is on the way 🚚", "Your order has been shipped."),
            "delivered": ("Order delivered ✓", "Your order has been delivered. Enjoy!"),
            "cancelled": ("Order cancelled", "Your order has been cancelled."),
        }

        title, body = status_messages.get(
            new_status, (f"Order update — {new_status}", f"Your order status: {new_status}")
        )

        recipient = order.guest_email or ""
        email_enabled = order.user_id is None
        push_enabled = order.user_id is not None
        if order.user_id:
            user_result = await self.db.execute(select(User).where(User.id == order.user_id).with_for_update()
                                               .execution_options(populate_existing=True))
            user = user_result.scalar_one_or_none()
            if user is None or user.deleted_at is not None:
                return
            recipient = user.email if user else ""
            prefs = await self.get_preferences(order.user_id, commit=False)
            email_enabled = prefs.order_updates_email
            push_enabled = prefs.order_updates_push

        if order.user_id and push_enabled:
            await self.create(
                user_id=order.user_id,
                type=f"order_{new_status}",
                title=f"#{order.order_number}: {title}",
                body=body,
                action_url=f"/orders/{order.id}",
                event_key=f"{event_key}:in_app",
            )
        if recipient and email_enabled:
            tracking_url = frontend_url(f"/orders/{order.id}")
            if order.user_id is None:
                from app.services.order_access import create_guest_token

                tracking_url = (
                    f"{tracking_url}?"
                    f"{urlencode({'guest_token': create_guest_token(order.id)})}"
                )
            html = (
                f"<h2>{escape(title)}</h2>"
                f"<p>{escape(body)}</p>"
                f'<p><a href="{escape(tracking_url, quote=True)}">'
                "Track your order &rarr;</a></p>"
            )
            await self.send_email(
                to=recipient,
                subject=f"WearHowZ order #{order.order_number}: {title}",
                html=html,
                template_id="order_status",
                delivery_key=f"{event_key}:email",
            )
        await self.db.commit()

    async def notify_payout(
        self, payout_id: UUID, status: str, event_key: Optional[str] = None
    ) -> None:
        """Create the seller's payout-status notification under their delivery preferences."""
        from app.models.wallet import Payout
        from app.models.seller import Seller

        result = await self.db.execute(select(Payout).where(Payout.id == payout_id))
        payout = result.scalar_one_or_none()
        if not payout:
            return

        seller_result = await self.db.execute(select(Seller).where(Seller.id == payout.seller_id))
        seller = seller_result.scalar_one_or_none()
        if not seller:
            return
        prefs = await self.get_preferences(seller.user_id, commit=False)
        if not prefs.payout_notifications:
            await self.db.commit()  # Persist any one-time legacy preference import.
            return
        event_key = event_key or f"payout:{payout.id}:status:{status}"

        messages = {
            "approved": (
                "Payout approved ✓",
                f"Your withdrawal of PKR {format_pkr(payout.amount)} has been approved.",
            ),
            "completed": (
                "Payout sent 💰",
                f"PKR {format_pkr(payout.amount)} has been sent to {payout.payment_detail}.",
            ),
            "rejected": (
                "Payout rejected",
                "Your withdrawal request was rejected. Funds returned to wallet.",
            ),
        }
        title, body = messages.get(status, (f"Payout {status}", ""))

        await self.create(
            user_id=seller.user_id,
            type=NotifType.PAYOUT_DONE,
            title=title,
            body=body,
            action_url="/seller/wallet/payouts",
            event_key=f"{event_key}:in_app",
        )
        await self.db.commit()

    async def notify_seller_decision(
        self,
        seller_id: UUID,
        approved: bool,
        reason: Optional[str] = None,
        event_key: Optional[str] = None,
    ) -> None:
        """Create the seller's application-decision notification."""
        from app.models.seller import Seller

        result = await self.db.execute(select(Seller).where(Seller.id == seller_id))
        seller = result.scalar_one_or_none()
        if not seller:
            return
        event_key = event_key or (
            f"seller:{seller.id}:decision:{'approved' if approved else 'rejected'}"
        )

        if approved:
            title = f"🎉 {seller.brand_name} is now live on WearHowZ!"
            body = "Your seller application has been approved. Start listing products."
            type_ = NotifType.SELLER_APPROVED
            url = "/seller/products"
        else:
            title = "Application update"
            body = (
                f"Your application was not approved. Reason: {reason or 'See email for details.'}"
            )
            type_ = NotifType.SELLER_REJECTED
            url = "/seller/register"

        await self.create(
            user_id=seller.user_id,
            type=type_,
            title=title,
            body=body,
            action_url=url,
            event_key=f"{event_key}:in_app",
        )
        await self.db.commit()

    # ── Admin broadcast ───────────────────────────────────────────────────────

    async def broadcast(self, payload: BroadcastRequest, admin_id: UUID) -> BroadcastResponse:
        """Queue notifications for the selected active audience through the durable outbox."""
        if payload.audience == "all":
            result = await self.db.execute(select(User.id).where(User.deleted_at.is_(None)))
        elif payload.audience == "customers":
            result = await self.db.execute(select(User.id).where(User.role == UserRole.customer, User.deleted_at.is_(None)))
        else:  # sellers
            result = await self.db.execute(select(User.id).where(User.role == UserRole.seller, User.deleted_at.is_(None)))

        user_ids = result.scalars().all()

        # Commit the event to the outbox; its publisher retries Redis safely.
        task_id = str(uuid.uuid4())
        from app.services.notification_outbox import queue_notification

        await queue_notification(
            self.db,
            f"broadcast:{task_id}",
            "broadcast_notification",
            [str(uid) for uid in user_ids],
            payload.title,
            payload.body,
            payload.action_url,
            task_id,
        )
        await self.db.commit()

        return BroadcastResponse(recipient_count=len(user_ids), task_id=task_id)

    # ── Email log ─────────────────────────────────────────────────────────────

    async def get_email_log(
        self,
        recipient_email: Optional[str] = None,
        date_from: Optional[str] = None,
        page: int = 1,
    ) -> dict:
        """Read delivery-log entries for administrative troubleshooting."""
        rows, total = await self.log_repo.list_admin(recipient_email, date_from, page)
        return {
            "data": [EmailLogResponse.model_validate(r) for r in rows],
            "total": total,
            "page": page,
        }
