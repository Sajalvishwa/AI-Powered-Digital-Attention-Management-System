import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, ForeignKey, Index, Integer, String, text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import TIMESTAMPTZ, Base, created_at_col, uuid_pk


class FocusSession(Base):
    __tablename__ = "focus_sessions"
    __table_args__ = (
        CheckConstraint("planned_min > 0", name="chk_fs_planned"),
        CheckConstraint(
            "status IN ('running','paused','completed','cancelled')", name="chk_fs_status"
        ),
        Index("idx_focus_user_started", "user_id", "started_at"),
        # only one running/paused session per user
        Index(
            "uq_one_running_focus",
            "user_id",
            unique=True,
            postgresql_where=text("status IN ('running','paused')"),
        ),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE")
    )
    label: Mapped[str | None] = mapped_column(String(120))
    planned_min: Mapped[int] = mapped_column(Integer)
    started_at: Mapped[datetime] = mapped_column(TIMESTAMPTZ)
    ended_at: Mapped[datetime | None] = mapped_column(TIMESTAMPTZ)
    status: Mapped[str] = mapped_column(String(12), default="running", server_default="running")
    switch_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    created_at: Mapped[datetime] = created_at_col()
