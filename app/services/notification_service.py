from __future__ import annotations

import uuid
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import Notification
from app.models.user import User, UserRole
from app.repositories.notification_repo import NotificationRepository, EmailLogRepository
from app.schemas.notification import (
    NotificationListResponse, NotificationResponse,
    NotificationPreferencesResponse, UpdatePreferencesRequest,
    BroadcastRequest, BroadcastResponse, EmailLogResponse,
)

# ── Notification types ────────────────────────────────────────────────────────

class NotifType:
    ORDER_PLACED    = "order_placed"
    ORDER_CONFIRMED = "order_confirmed"
    ORDER_SHIPPED   = "order_shipped"
    ORDER_DELIVERED = "order_delivered"
    ORDER_CANCELLED = "order_cancelled"
    PAYOUT_DONE     = "payout_completed"
    SELLER_APPROVED = "seller_approved"
    SELLER_REJECTED = "seller_rejected"
    NEW_REVIEW      = "new_review"
    LOW_STOCK       = "low_stock"
    BROADCAST       = "broadcast"


class NotificationService:
    def __init__(self, db: AsyncSession) -> None:
        self.db      = db
        self.repo    = NotificationRepository(db)
        self.log_repo= EmailLogRepository(db)

    # ── In-app notifications ───────────────────────────────────────────────────

    async def create(
        self,
        user_id:    UUID,
        type:       str,
        title:      str,
        body:       str,
        action_url: Optional[str] = None,
    ) -> Notification:
        return await self.repo.create(
            user_id=user_id, type=type, title=title,
            body=body, action_url=action_url,
        )

    async def list_notifications(
        self,
        user_id:     UUID,
        unread_only: bool = False,
        page:        int  = 1,
        per_page:    int  = 20,
    ) -> NotificationListResponse:
        rows, total   = await self.repo.list_by_user(user_id, unread_only, page, per_page)
        unread_count  = await self.repo.unread_count(user_id)
        return NotificationListResponse(
            data         = [NotificationResponse.model_validate(n) for n in rows],
            unread_count = unread_count,
            total        = total,
            page         = page,
        )

    async def mark_read(self, notification_id: UUID, user_id: UUID) -> bool:
        result = await self.repo.mark_read(notification_id, user_id)
        await self.db.commit()
        return result

    async def mark_all_read(self, user_id: UUID) -> int:
        count = await self.repo.mark_all_read(user_id)
        await self.db.commit()
        return count

    # ── Preferences ───────────────────────────────────────────────────────────

    async def get_preferences(self, user_id: UUID) -> NotificationPreferencesResponse:
        prefs = await self.repo.get_preferences(user_id)
        if not prefs:
            # Return defaults
            return NotificationPreferencesResponse(
                order_updates_email=True, order_updates_push=True,
                promotions_email=True, payout_notifications=True,
                new_review_notifications=True, low_stock_alerts=True,
            )
        return NotificationPreferencesResponse.model_validate(prefs)

    async def update_preferences(
        self, user_id: UUID, payload: UpdatePreferencesRequest
    ) -> NotificationPreferencesResponse:
        updates = {k: v for k, v in payload.model_dump().items() if v is not None}
        prefs   = await self.repo.upsert_preferences(user_id, **updates)
        await self.db.commit()
        return NotificationPreferencesResponse.model_validate(prefs)

    # ── Email sending ─────────────────────────────────────────────────────────

    async def send_email(
        self,
        to:          str,
        subject:     str,
        html:        str,
        template_id: Optional[str] = None,
    ) -> str | None:
        """Send email via Resend and log the result."""
        resend_id     = None
        status        = "failed"
        error_message = None

        try:
            from app.integrations.resend_client import ResendClient
            client    = ResendClient()
            resend_id = await client.send(to=to, subject=subject, html=html)
            status    = "sent"
        except Exception as exc:
            error_message = str(exc)

        await self.log_repo.create(
            recipient_email = to,
            subject         = subject,
            template_id     = template_id,
            status          = status,
            resend_id       = resend_id,
            error_message   = error_message,
        )
        await self.db.commit()
        return resend_id

    # ── Order emails ──────────────────────────────────────────────────────────

    async def notify_order_placed(self, order_id: UUID) -> None:
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

        # In-app notification
        if order.user_id:
            await self.create(
                user_id    = order.user_id,
                type       = NotifType.ORDER_PLACED,
                title      = f"Order #{order.order_number} placed",
                body       = f"Your order of PKR {int(order.total):,} has been received.",
                action_url = f"/orders/{order.id}",
            )

        # Email
        recipient = order.guest_email or ""
        if order.user_id:
            user_result = await self.db.execute(
                select(User).where(User.id == order.user_id)
            )
            user      = user_result.scalar_one_or_none()
            recipient = user.email if user else ""

        if recipient:
            items_html = "".join(
                f"<tr><td>{i.product_name} — {i.variant_label}</td>"
                f"<td style='text-align:right'>PKR {int(i.unit_price):,} × {i.quantity}</td>"
                f"<td style='text-align:right'>PKR {int(i.subtotal):,}</td></tr>"
                for i in order.items
            )
            html = f"""
            <h2>Order Confirmed — #{order.order_number}</h2>
            <p>Thank you for your order! Here's your summary:</p>
            <table width="100%">
              <thead><tr><th>Item</th><th>Price</th><th>Subtotal</th></tr></thead>
              <tbody>{items_html}</tbody>
            </table>
            <p><strong>Shipping fee:</strong> PKR {int(order.shipping_fee):,}</p>
            <p><strong>Total:</strong> PKR {int(order.total):,}</p>
            <p>Payment method: {order.payment_method.value.upper()}</p>
            <p><a href="https://drip.pk/orders/{order.id}">Track your order →</a></p>
            """
            await self.send_email(
                to          = recipient,
                subject     = f"DRIP Order #{order.order_number} Confirmed",
                html        = html,
                template_id = "order_placed",
            )
        await self.db.commit()

    async def notify_order_status(self, order_id: UUID, new_status: str) -> None:
        from app.models.order import Order
        result = await self.db.execute(select(Order).where(Order.id == order_id))
        order  = result.scalar_one_or_none()
        if not order or not order.user_id:
            return

        status_messages = {
            "payment_confirmed": ("Payment confirmed ✓", "Your payment has been received and your order is being prepared."),
            "processing":        ("Order being prepared 📦", "Sellers are packing your items."),
            "shipped":           ("Your order is on the way 🚚", "Your order has been shipped."),
            "delivered":         ("Order delivered ✓", "Your order has been delivered. Enjoy!"),
            "cancelled":         ("Order cancelled", "Your order has been cancelled."),
        }

        title, body = status_messages.get(
            new_status, (f"Order update — {new_status}", f"Your order status: {new_status}")
        )

        await self.create(
            user_id    = order.user_id,
            type       = f"order_{new_status}",
            title      = f"#{order.order_number}: {title}",
            body       = body,
            action_url = f"/orders/{order.id}",
        )
        await self.db.commit()

    async def notify_payout(self, payout_id: UUID, status: str) -> None:
        from app.models.wallet import Payout
        from app.models.seller import Seller
        result = await self.db.execute(select(Payout).where(Payout.id == payout_id))
        payout = result.scalar_one_or_none()
        if not payout:
            return

        seller_result = await self.db.execute(
            select(Seller).where(Seller.id == payout.seller_id)
        )
        seller = seller_result.scalar_one_or_none()
        if not seller:
            return

        messages = {
            "approved":  ("Payout approved ✓",       f"Your withdrawal of PKR {int(payout.amount):,} has been approved."),
            "completed": ("Payout sent 💰",           f"PKR {int(payout.amount):,} has been sent to {payout.payment_detail}."),
            "rejected":  ("Payout rejected",          f"Your withdrawal request was rejected. Funds returned to wallet."),
        }
        title, body = messages.get(status, (f"Payout {status}", ""))

        await self.create(
            user_id    = seller.user_id,
            type       = NotifType.PAYOUT_DONE,
            title      = title,
            body       = body,
            action_url = "/seller/wallet/payouts",
        )
        await self.db.commit()

    async def notify_seller_decision(
        self, seller_id: UUID, approved: bool, reason: Optional[str] = None
    ) -> None:
        from app.models.seller import Seller
        result = await self.db.execute(select(Seller).where(Seller.id == seller_id))
        seller = result.scalar_one_or_none()
        if not seller:
            return

        if approved:
            title = f"🎉 {seller.brand_name} is now live on DRIP!"
            body  = "Your seller application has been approved. Start listing products."
            type_ = NotifType.SELLER_APPROVED
            url   = "/seller/products"
        else:
            title = "Application update"
            body  = f"Your application was not approved. Reason: {reason or 'See email for details.'}"
            type_ = NotifType.SELLER_REJECTED
            url   = "/seller/register"

        await self.create(user_id=seller.user_id, type=type_, title=title, body=body, action_url=url)
        await self.db.commit()

    # ── Admin broadcast ───────────────────────────────────────────────────────

    async def broadcast(
        self, payload: BroadcastRequest, admin_id: UUID
    ) -> BroadcastResponse:
        if payload.audience == "all":
            result = await self.db.execute(select(User.id))
        elif payload.audience == "customers":
            result = await self.db.execute(
                select(User.id).where(User.role == UserRole.customer)
            )
        else:  # sellers
            result = await self.db.execute(
                select(User.id).where(User.role == UserRole.seller)
            )

        user_ids = result.scalars().all()

        # Enqueue ARQ task instead of doing synchronously
        task_id = str(uuid.uuid4())
        try:
            from arq import create_pool
            from arq.connections import RedisSettings
            from app.core.config import settings as app_settings
            pool = await create_pool(RedisSettings.from_dsn(str(app_settings.REDIS_URL)))
            await pool.enqueue_job(
                "broadcast_notification",
                [str(uid) for uid in user_ids],
                payload.title,
                payload.body,
                payload.action_url,
                task_id,
            )
            await pool.aclose()
        except Exception:
            pass  # Non-critical — log and continue

        return BroadcastResponse(recipient_count=len(user_ids), task_id=task_id)

    # ── Email log ─────────────────────────────────────────────────────────────

    async def get_email_log(
        self,
        recipient_email: Optional[str] = None,
        date_from:       Optional[str] = None,
        page:            int = 1,
    ) -> dict:
        rows, total = await self.log_repo.list_admin(recipient_email, date_from, page)
        return {
            "data":  [EmailLogResponse.model_validate(r) for r in rows],
            "total": total,
            "page":  page,
        }