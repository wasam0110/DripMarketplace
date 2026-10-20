"""
app/tasks/worker.py — ARQ worker with all tasks registered.
"""
from __future__ import annotations

from arq import cron
from arq.connections import RedisSettings

from app.core.config import settings
from app.core.logging import configure_logging, get_logger

# ── Email tasks ────────────────────────────────────────────────────────────────
from app.tasks.email_tasks import (
    task_send_verification_email,
    task_send_password_reset_email,
    task_send_order_confirmation,
    task_send_shipping_notification,
    task_send_cod_timeout,
    task_send_seller_approved,
)

# ── Order tasks ────────────────────────────────────────────────────────────────
# Confirmation delivery is registered from notification_tasks below so it uses
# the durable outbox's retry and idempotency handling.
from app.tasks.order_tasks import (
    cod_verification_timeout,
    expire_pending_orders,
)

# ── Wallet / commission tasks ──────────────────────────────────────────────────
from app.tasks.wallet_tasks import settle_commission, move_pending_to_available

# ── Notification tasks ─────────────────────────────────────────────────────────
from app.tasks.notification_tasks import (
    send_order_confirmation,
    send_order_status_update,
    send_payout_notification,
    notify_seller_decision,
    broadcast_notification,
    dispatch_notification_outbox,
    deliver_notification_outbox,
)

# ── Cleanup tasks (all scheduled via cron_jobs below) ─────────────────────────
from app.tasks.cleanup_tasks import (
    cleanup_abandoned_carts,
    cleanup_expired_sessions,
    cleanup_soft_deleted_users,
    cleanup_expired_reset_tokens,
    archive_old_notifications,
    cleanup_orphaned_images,
)

logger = get_logger(__name__)


async def startup(ctx: dict) -> None:
    """Initialize logging, database, and Redis; clean up partial startup failures."""
    configure_logging()
    from contextlib import AsyncExitStack
    from app.core.database import close_db, init_db
    from app.core.redis import close_redis, init_redis
    async with AsyncExitStack() as cleanup:
        cleanup.push_async_callback(close_db)
        await init_db()
        cleanup.push_async_callback(close_redis)
        await init_redis()
        cleanup.pop_all()  # Normal shutdown owns successfully initialized resources.
    logger.info("worker.started")


async def shutdown(ctx: dict) -> None:
    """Close Redis and always release database resources during worker shutdown."""
    from app.core.database import close_db
    from app.core.redis import close_redis
    try:
        await close_redis()
    finally:
        await close_db()
    logger.info("worker.stopped")


class WorkerSettings:
    functions = [
        # Email delivery
        task_send_verification_email,
        task_send_password_reset_email,
        task_send_order_confirmation,
        task_send_shipping_notification,
        task_send_cod_timeout,
        task_send_seller_approved,
        # Order lifecycle
        cod_verification_timeout,
        expire_pending_orders,
        # Notifications (in-app + email)
        send_order_confirmation,
        send_order_status_update,
        send_payout_notification,
        notify_seller_decision,
        broadcast_notification,
        dispatch_notification_outbox,
        deliver_notification_outbox,
        # Wallet / commission
        settle_commission,
        move_pending_to_available,
        # Cleanup (triggered by cron — also enqueue-able for on-demand runs)
        cleanup_abandoned_carts,
        cleanup_expired_sessions,
        cleanup_soft_deleted_users,
        cleanup_expired_reset_tokens,
        archive_old_notifications,
        cleanup_orphaned_images,
    ]

    redis_settings = RedisSettings.from_dsn(settings.REDIS_URL)

    on_startup  = startup
    on_shutdown = shutdown

    max_jobs    = 10
    job_timeout = 300
    # ARQ also uses this default for exhausted retries / pre-execution failures,
    # bypassing per-function retention. Results contain original job args (PII
    # and auth tokens). Durable notification status lives in the DB outbox.
    keep_result = 0
    keep_result_forever = False
    log_results = False
    retry_jobs  = True
    max_tries   = 3
    queue_name  = "arq:queue"

    cron_jobs = [
        # Durable notification outbox publisher — every minute.
        cron(dispatch_notification_outbox, minute=set(range(60))),
        # Wallet hold release — every 10 minutes.
        cron(move_pending_to_available, minute={0, 10, 20, 30, 40, 50}),
        # Expired COD / pending-payment sweep — every 5 minutes.
        cron(expire_pending_orders, minute=set(range(0, 60, 5))),
        # Nightly maintenance tasks (staggered to avoid DB spikes).
        cron(cleanup_abandoned_carts,      hour={2},  minute={0}),
        cron(cleanup_expired_reset_tokens, hour={2},  minute={30}),
        cron(cleanup_expired_sessions,     hour={3},  minute={0}),
        cron(cleanup_orphaned_images,      hour={3},  minute={30}),
        cron(cleanup_soft_deleted_users,   hour={4},  minute={0}),
        cron(archive_old_notifications,    hour={5},  minute={0}),
    ]
