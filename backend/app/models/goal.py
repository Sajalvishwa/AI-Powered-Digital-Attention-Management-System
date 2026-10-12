import uuid
from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Index, Integer, String, text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, created_at_col, uuid_pk


class Goal(Base):
    __tablename__ = "goals"
    __table_args__ = (
        CheckConstraint(
            "type IN ('daily_focus_min','max_task_switches','max_app_min')", name="chk_goal_type"
        ),
        CheckConstraint("target_value > 0", name="chk_goal_target"),
        Index("idx_goals_user", "user_id", postgresql_where=text("is_active")),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE")
    )
    type: Mapped[str] = mapped_column(String(30))
    target_value: Mapped[int] = mapped_column(Integer)
    app_name: Mapped[str | None] = mapped_column(String(255))  # only for max_app_min
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default=text("true"))
    created_at: Mapped[datetime] = created_at_col()
