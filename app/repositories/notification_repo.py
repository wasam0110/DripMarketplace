from __future__ import annotations

from uuid import UUID
from typing import Optional, Sequence
from datetime import datetime

from sqlalchemy import select, update, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import Notification, NotificationPreference, EmailLog


class NotificationRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, **kwargs) -> Notification:
        n = Notification(**kwargs)
        self.db.add(n)
        await self.db.flush()
        return n

    async def list_by_user(
        self,
        user_id:     UUID,
        unread_only: bool = False,
        page:        int  = 1,
        per_page:    int  = 20,
    ) -> tuple[Sequence[Notification], int]:
        q = select(Notification).where(Notification.user_id == user_id)
        if unread_only:
            q = q.where(Notification.is_read.is_(False))

        count_q = select(func.count()).select_from(q.subquery())
        total   = (await self.db.execute(count_q)).scalar_one()

        q = q.order_by(desc(Notification.created_at)).offset((page - 1) * per_page).limit(per_page)
        result = await self.db.execute(q)
        return result.scalars().all(), total

    async def unread_count(self, user_id: UUID) -> int:
        result = await self.db.execute(
            select(func.count(Notification.id)).where(
                Notification.user_id == user_id,
                Notification.is_read.is_(False),
            )
        )
        return result.scalar_one() or 0

    async def mark_read(self, notification_id: UUID, user_id: UUID) -> bool:
        result = await self.db.execute(
            update(Notification)
            .where(Notification.id == notification_id, Notification.user_id == user_id)
            .values(is_read=True)
            .returning(Notification.id)
        )
        return result.scalar_one_or_none() is not None

    async def mark_all_read(self, user_id: UUID) -> int:
        result = await self.db.execute(
            update(Notification)
            .where(Notification.user_id == user_id, Notification.is_read.is_(False))
            .values(is_read=True)
            .returning(Notification.id)
        )
        return len(result.scalars().all())

    async def get_preferences(self, user_id: UUID) -> Optional[NotificationPreference]:
        result = await self.db.execute(
            select(NotificationPreference).where(NotificationPreference.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def upsert_preferences(self, user_id: UUID, **kwargs) -> NotificationPreference:
        existing = await self.get_preferences(user_id)
        if existing:
            for k, v in kwargs.items():
                if v is not None:
                    setattr(existing, k, v)
            existing.updated_at = datetime.utcnow()
        else:
            existing = NotificationPreference(user_id=user_id, **{k: v for k, v in kwargs.items() if v is not None})
            self.db.add(existing)
        await self.db.flush()
        return existing


class EmailLogRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, **kwargs) -> EmailLog:
        entry = EmailLog(**kwargs)
        self.db.add(entry)
        await self.db.flush()
        return entry

    async def list_admin(
        self,
        recipient_email: Optional[str] = None,
        date_from:       Optional[str] = None,
        page:            int = 1,
        per_page:        int = 25,
    ) -> tuple[Sequence[EmailLog], int]:
        q = select(EmailLog)
        if recipient_email:
            q = q.where(EmailLog.recipient_email.ilike(f"%{recipient_email}%"))
        if date_from:
            q = q.where(EmailLog.sent_at >= date_from)

        count_q = select(func.count()).select_from(q.subquery())
        total   = (await self.db.execute(count_q)).scalar_one()

        q = q.order_by(desc(EmailLog.sent_at)).offset((page - 1) * per_page).limit(per_page)
        result = await self.db.execute(q)
        return result.scalars().all(), total