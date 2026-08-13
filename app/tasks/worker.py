"""
app/tasks/worker.py — ARQ worker with Block 2 email tasks registered.
"""

from __future__ import annotations
from app.tasks.order_tasks import cod_verification_timeout, send_order_confirmation

from arq.connections import RedisSettings

from app.core.config import settings
from app.core.logging import configure_logging, get_logger
from app.tasks.email_tasks import (
    task_send_verification_email,
    task_send_password_reset_email,
    task_send_order_confirmation,
    task_send_shipping_notification,
    task_send_cod_timeout,
    task_send_seller_approved,
)

logger = get_logger(__name__)


async def startup(ctx: dict) -> None:
    configure_logging()

    from app.core.database import init_db
    from app.core.redis import init_redis

    await init_db()
    await init_redis()

    logger.info("worker.started")


async def shutdown(ctx: dict) -> None:
    from app.core.database import close_db
    from app.core.redis import close_redis

    await close_db()
    await close_redis()

    logger.info("worker.stopped")


class WorkerSettings:
    functions = [
        task_send_verification_email,
        task_send_password_reset_email,
        task_send_order_confirmation,
        task_send_shipping_notification,
        task_send_cod_timeout,
        task_send_seller_approved,
        cod_verification_timeout,
        send_order_confirmation,
    ]

    redis_settings = RedisSettings.from_dsn(settings.REDIS_URL)

    on_startup = startup
    on_shutdown = shutdown

    max_jobs = 10
    job_timeout = 300
    keep_result = 3600
    retry_jobs = True
    max_tries = 3
    queue_name = "drip:default"