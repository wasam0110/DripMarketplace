"""services / notification outbox.

Business operations connecting API handlers, persistence, and provider integrations.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BusinessRuleError, NotFoundError
from app.models.notification import NotificationOutbox


async def queue_notification(
    db: AsyncSession,
    event_key: str,
    task_name: str,
    *task_args: object,
) -> None:
    """Persist one queue event in the caller's current database transaction."""
    statement = (
        insert(NotificationOutbox)
        .values(
            event_key=event_key,
            task_name=task_name,
            args=[*task_args, event_key],
        )
        .on_conflict_do_nothing(index_elements=[NotificationOutbox.event_key])
    )
    await db.execute(statement)


async def list_failed_notifications(db: AsyncSession, page: int, per_page: int) -> dict:
    """List unresolved failed outbox events for administrative recovery."""
    rows = await db.scalars(
        select(NotificationOutbox)
        .where(NotificationOutbox.dead_lettered_at.is_not(None))
        .order_by(NotificationOutbox.dead_lettered_at, NotificationOutbox.id)
        .offset((page - 1) * per_page)
        .limit(per_page)
    )
    return {
        "page": page,
        "data": [
            {
                "id": row.id,
                "event_key": row.event_key,
                "task_name": row.task_name,
                "publication_attempts": row.attempts,
                "delivery_attempts": row.delivery_attempts,
                "last_error": row.last_error,
                "dead_lettered_at": row.dead_lettered_at,
                "replay_history": row.replay_history,
            }
            for row in rows
        ],
    }


async def replay_failed_notification(
    db: AsyncSession,
    event_id: UUID,
    admin_id: UUID,
    reason: str,
) -> dict:
    """Reset an eligible failed outbox event so the worker can attempt delivery again."""
    row = await db.scalar(
        select(NotificationOutbox)
        .where(NotificationOutbox.id == event_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if row is None:
        raise NotFoundError("Notification event not found")
    if not row.dead_lettered_at or row.completed_at:
        raise BusinessRuleError("Only unresolved failed notifications can be replayed")
    row.replay_history = [
        *row.replay_history,
        {
            "admin_id": str(admin_id),
            "reason": reason,
            "requested_at": datetime.now(UTC).isoformat(),
            "publication_attempts": row.attempts,
            "delivery_attempts": row.delivery_attempts,
            "last_error": row.last_error,
        },
    ]
    row.attempts = row.delivery_attempts = 0
    row.dead_lettered_at = row.published_at = None
    row.last_error = None
    await db.commit()
    return {"id": row.id, "status": "pending"}
