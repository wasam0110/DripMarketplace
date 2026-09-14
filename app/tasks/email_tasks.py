"""
app/tasks/email_tasks.py
─────────────────────────
ARQ background tasks for email delivery.
These run in the worker process, not the API process.
"""
from __future__ import annotations

from app.core.logging import get_logger
from app.integrations.resend_client import (
    send_cod_timeout_email,
    send_order_confirmation_email,
    send_password_reset_email,
    send_seller_approved_email,
    send_shipping_notification_email,
    send_verification_email,
)

logger = get_logger(__name__)


async def task_send_verification_email(
    ctx: dict,
    email: str,
    first_name: str,
    token: str,
) -> None:
    """Send email verification link after registration."""
    ok = await send_verification_email(email, first_name, token)
    if not ok:
        logger.error("task.verification_email_failed", email=email)
        raise RuntimeError("Email delivery failed — will retry")


async def task_send_password_reset_email(
    ctx: dict,
    email: str,
    first_name: str,
    token: str,
) -> None:
    """Send password reset link."""
    ok = await send_password_reset_email(email, first_name, token)
    if not ok:
        logger.error("task.password_reset_email_failed", email=email)
        raise RuntimeError("Email delivery failed — will retry")


async def task_send_order_confirmation(
    ctx: dict,
    email: str,
    name: str,
    order_number: str,
    total: int,
    items: list[dict],
) -> None:
    ok = await send_order_confirmation_email(email, name, order_number, total, items)
    if not ok:
        logger.error("task.order_confirmation_failed", order_number=order_number)
        raise RuntimeError("Email delivery failed — will retry")


async def task_send_shipping_notification(
    ctx: dict,
    email: str,
    name: str,
    order_number: str,
    tracking_number: str,
    courier_name: str,
    brand_name: str,
) -> None:
    ok = await send_shipping_notification_email(
        email, name, order_number, tracking_number, courier_name, brand_name
    )
    if not ok:
        logger.error("task.shipping_notification_failed", order_number=order_number)
        raise RuntimeError("Email delivery failed — will retry")


async def task_send_cod_timeout(
    ctx: dict,
    email: str,
    name: str,
    order_number: str,
) -> None:
    ok = await send_cod_timeout_email(email, name, order_number)
    if not ok:
        logger.error("task.cod_timeout_email_failed", order_number=order_number)


async def task_send_seller_approved(
    ctx: dict,
    email: str,
    brand_name: str,
    dashboard_url: str,
) -> None:
    ok = await send_seller_approved_email(email, brand_name, dashboard_url)
    if not ok:
        logger.error("task.seller_approved_email_failed", brand_name=brand_name)