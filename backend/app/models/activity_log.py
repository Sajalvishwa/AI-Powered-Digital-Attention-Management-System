import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Computed,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import TIMESTAMPTZ, Base, created_at_col, uuid_pk


class ActivitySession(Base):
    """One continuous stretch in one app (or idle). Core table of the project."""

    __tablename__ = "activity_sessions"
    __table_args__ = (
        CheckConstraint("ended_at >= started_at", name="chk_time_order"),
        UniqueConstraint("user_id", "client_id", name="uq_user_client"),
        Index("idx_act_user_started", "user_id", "started_at"),
        Index("idx_act_user_app", "user_id", "app_name"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    client_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True))  # idempotency key
    user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE")
    )
    device_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("devices.id", ondelete="SET NULL")
    )
    app_name: Mapped[str] = mapped_column(String(255))
    window_title: Mapped[str | None] = mapped_column(Text)  # NULL unless user opted in
    is_idle: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text("false"))
    started_at: Mapped[datetime] = mapped_column(TIMESTAMPTZ)
    ended_at: Mapped[datetime] = mapped_column(TIMESTAMPTZ)
    duration_sec: Mapped[int | None] = mapped_column(
        Integer,
        Computed("EXTRACT(EPOCH FROM (ended_at - started_at))::int", persisted=True),
    )
    focus_session_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("focus_sessions.id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = created_at_col()
