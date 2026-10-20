"""models / notification.

SQLAlchemy persistence definitions shared by repositories and services.
"""

from __future__ import annotations

from sqlalchemy import Index as SchemaIndex

from sqlalchemy import text as sql_text

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Notification(Base):
    __tablename__ = "notifications"
    __table_args__ = (
        SchemaIndex("ix_notifications_created_at", "created_at"),
        SchemaIndex("ix_notifications_is_read", "is_read"),
        SchemaIndex("ix_notifications_user_id", "user_id"),
    )

    id:         Mapped[UUID]       = mapped_column(primary_key=True, default=uuid4, server_default=sql_text("gen_random_uuid()"))
    user_id:    Mapped[UUID]       = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    type:       Mapped[str]        = mapped_column(String(50))
    title:      Mapped[str]        = mapped_column(String(200))
    body:       Mapped[str]        = mapped_column(Text)
    action_url: Mapped[str | None] = mapped_column(String(500))
    is_read:    Mapped[bool]       = mapped_column(Boolean, default=False, server_default="false")
    read_at:    Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    created_at: Mapped[datetime]   = mapped_column(DateTime(timezone=True), server_default="now()")


class NotificationPreference(Base):
    __tablename__ = "notification_preferences"

    user_id:                  Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    order_updates_email:      Mapped[bool] = mapped_column(Boolean, default=True,  server_default="true")
    order_updates_push:       Mapped[bool] = mapped_column(Boolean, default=True,  server_default="true")
    promotions_email:         Mapped[bool] = mapped_column(Boolean, default=True,  server_default="true")
    payout_notifications:     Mapped[bool] = mapped_column(Boolean, default=True,  server_default="true")
    new_review_notifications: Mapped[bool] = mapped_column(Boolean, default=True,  server_default="true")
    low_stock_alerts:         Mapped[bool] = mapped_column(Boolean, default=True,  server_default="true")
    email_new_arrivals:       Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    sms_order_updates:        Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    whatsapp_order_updates:   Mapped[bool] = mapped_column(Boolean, default=True,  server_default="true")
    updated_at:               Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()")
    legacy_imported: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")


class EmailLog(Base):
    __tablename__ = "email_log"
    __table_args__ = (
        SchemaIndex("ix_email_log_recipient", "recipient_email"),
        SchemaIndex("ix_email_log_sent_at", "sent_at"),
UniqueConstraint("delivery_key", name="uq_email_log_delivery_key"),)

    id:              Mapped[UUID]       = mapped_column(primary_key=True, default=uuid4, server_default=sql_text("gen_random_uuid()"))
    recipient_email: Mapped[str]        = mapped_column(String(254))
    subject:         Mapped[str]        = mapped_column(String(500))
    template_id:     Mapped[str | None] = mapped_column(String(100))
    status:          Mapped[str]        = mapped_column(String(20))   # sent / failed
    resend_id:       Mapped[str | None] = mapped_column(String(255))
    error_message:   Mapped[str | None] = mapped_column(Text)
    delivery_key:    Mapped[str | None] = mapped_column(String(255))
    attempts:        Mapped[int]        = mapped_column(Integer, default=0, server_default="0")
    sent_at:         Mapped[datetime]   = mapped_column(DateTime(timezone=True), server_default="now()")


class NotificationOutbox(Base):
    """Durable hand-off between a business transaction and the ARQ queue."""

    __tablename__ = "notification_outbox"
    __table_args__ = (
        UniqueConstraint("event_key", name="uq_notification_outbox_event_key"),
        Index("ix_notification_outbox_pending", "published_at", "created_at"),
        Index("ix_notification_outbox_recovery", "completed_at", "dead_lettered_at", "published_at"),
    )

    id:           Mapped[UUID]       = mapped_column(primary_key=True, default=uuid4, server_default=text("gen_random_uuid()"))
    event_key:    Mapped[str]        = mapped_column(String(255), nullable=False)
    task_name:    Mapped[str]        = mapped_column(String(100), nullable=False)
    args:         Mapped[list]       = mapped_column(JSONB, nullable=False)
    attempts:     Mapped[int]        = mapped_column(Integer, default=0, server_default="0")
    last_error:   Mapped[str | None] = mapped_column(Text)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    dead_lettered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    delivery_attempts: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    replay_history: Mapped[list] = mapped_column(JSONB, default=list, server_default=text("'[]'::jsonb"))
    created_at:   Mapped[datetime]   = mapped_column(DateTime(timezone=True), server_default="now()")
