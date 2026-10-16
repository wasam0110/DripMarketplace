"""
app/tasks/email_tasks.py
─────────────────────────
ARQ background tasks for email delivery.
These run in the worker process, not the API process.
"""

from __future__ import annotations

from arq import Retry

from app.core.config import settings
from app.core.logging import get_logger
from app.integrations.resend_client import (
    send_cod_timeout_email,
    send_order_confirmation_email,
    send_password_reset_email,
    send_seller_approved_email,
    send_shipping_notification_email,
    send_verification_email,
)
from app.services.queued_email_privacy import checked_email_recipient

logger = get_logger(__name__)


async def task_send_verification_email(
    ctx: dict,
    email: str,
    first_name: str,
    token: str,
) -> None:
    """Send email verification link after registration."""
    async with checked_email_recipient(ctx, email, token=token, purpose="verification") as name:
        if name is None:
            return
        ok = await send_verification_email(email, name, token)
        if not ok:
            logger.error("task.verification_email_failed")
            raise Retry(defer=30 * ctx.get("job_try", 1))


async def task_send_password_reset_email(
    ctx: dict,
    email: str,
    first_name: str,
    token: str,
) -> None:
    """Send password reset link."""
    async with checked_email_recipient(ctx, email, token=token, purpose="password_reset") as name:
        if name is None:
            return
        ok = await send_password_reset_email(email, name, token)
        if not ok:
            logger.error("task.password_reset_email_failed")
            raise Retry(defer=30 * ctx.get("job_try", 1))


async def task_send_order_confirmation(
    ctx: dict,
    email: str,
    name: str,
    order_number: str,
    total: int,
    items: list[dict],
) -> None:
    async with checked_email_recipient(ctx, email, order_number=order_number) as current_name:
        if current_name is None:
            return
        ok = await send_order_confirmation_email(email, current_name, order_number, total, items)
        if not ok:
            logger.error("task.order_confirmation_failed", order_number=order_number)
            raise Retry(defer=30 * ctx.get("job_try", 1))


async def task_send_shipping_notification(
    ctx: dict,
    email: str,
    name: str,
    order_number: str,
    tracking_number: str,
    courier_name: str,
    brand_name: str,
) -> None:
    async with checked_email_recipient(
        ctx, email, order_number=order_number, order_updates=True
    ) as current_name:
        if current_name is None:
            return
        ok = await send_shipping_notification_email(
            email, current_name, order_number, tracking_number, courier_name, brand_name
        )
        if not ok:
            logger.error("task.shipping_notification_failed", order_number=order_number)
            raise Retry(defer=30 * ctx.get("job_try", 1))


async def task_send_cod_timeout(
    ctx: dict,
    email: str,
    name: str,
    order_number: str,
) -> None:
    async with checked_email_recipient(
        ctx, email, order_number=order_number, order_updates=True
    ) as current_name:
        if current_name is None:
            return
        ok = await send_cod_timeout_email(email, current_name, order_number)
        if not ok:
            logger.error("task.cod_timeout_email_failed", order_number=order_number)
            raise Retry(defer=30 * ctx.get("job_try", 1))


async def task_send_seller_approved(
    ctx: dict,
    email: str,
    brand_name: str,
    dashboard_url: str,
) -> None:
    async with checked_email_recipient(ctx, email, brand_name=brand_name) as current_name:
        if current_name is None:
            return
        ok = await send_seller_approved_email(
            email, brand_name, f"{settings.FRONTEND_URL}/seller/dashboard"
        )
        if not ok:
            logger.error("task.seller_approved_email_failed")
            raise Retry(defer=30 * ctx.get("job_try", 1))
