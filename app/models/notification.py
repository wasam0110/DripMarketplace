from __future__ import annotations

from uuid import UUID, uuid4
from datetime import datetime

from sqlalchemy import String, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Notification(Base):
    __tablename__ = "notifications"

    id:         Mapped[UUID]       = mapped_column(primary_key=True, default=uuid4)
    user_id:    Mapped[UUID]       = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    type:       Mapped[str]        = mapped_column(String(50))
    title:      Mapped[str]        = mapped_column(String(200))
    body:       Mapped[str]        = mapped_column(Text)
    action_url: Mapped[str | None] = mapped_column(String(500))
    is_read:    Mapped[bool]       = mapped_column(Boolean, default=False, server_default="false")
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
    updated_at:               Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()")


class EmailLog(Base):
    __tablename__ = "email_log"

    id:              Mapped[UUID]       = mapped_column(primary_key=True, default=uuid4)
    recipient_email: Mapped[str]        = mapped_column(String(254))
    subject:         Mapped[str]        = mapped_column(String(500))
    template_id:     Mapped[str | None] = mapped_column(String(100))
    status:          Mapped[str]        = mapped_column(String(20))   # sent / failed
    resend_id:       Mapped[str | None] = mapped_column(String(255))
    error_message:   Mapped[str | None] = mapped_column(Text)
    sent_at:         Mapped[datetime]   = mapped_column(DateTime(timezone=True), server_default="now()")