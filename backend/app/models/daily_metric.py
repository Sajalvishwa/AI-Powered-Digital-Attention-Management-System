import uuid
from datetime import date, datetime

from sqlalchemy import Date, Float, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, created_at_col, uuid_pk


class DailyMetric(Base):
    __tablename__ = "daily_metrics"
    __table_args__ = (UniqueConstraint("user_id", "day", name="uq_metric_user_day"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE")
    )
    day: Mapped[date] = mapped_column(Date)
    active_min: Mapped[float] = mapped_column(Float, default=0)
    idle_min: Mapped[float] = mapped_column(Float, default=0)
    focus_min: Mapped[float] = mapped_column(Float, default=0)  # time inside focus sessions
    session_count: Mapped[int] = mapped_column(Integer, default=0)
    avg_session_min: Mapped[float] = mapped_column(Float, default=0)
    longest_session_min: Mapped[float] = mapped_column(Float, default=0)
    switch_count: Mapped[int] = mapped_column(Integer, default=0)
    hourly_active_min: Mapped[list] = mapped_column(JSONB)
    hourly_focus_min: Mapped[list] = mapped_column(JSONB)
    hourly_switches: Mapped[list] = mapped_column(JSONB)
    top_apps: Mapped[dict] = mapped_column(JSONB)
    created_at: Mapped[datetime] = created_at_col()