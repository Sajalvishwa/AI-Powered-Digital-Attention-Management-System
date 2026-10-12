"""Daily scores. Filled by the ML/scoring engine in Weeks 3-4."""
import uuid
from datetime import date, datetime

from sqlalchemy import Date, Float, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, created_at_col, uuid_pk


class DailyScore(Base):
    __tablename__ = "daily_scores"
    __table_args__ = (UniqueConstraint("user_id", "day", name="uq_score_user_day"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE")
    )
    day: Mapped[date] = mapped_column(Date)
    focus_score: Mapped[float | None] = mapped_column(Float)
    productivity_score: Mapped[float | None] = mapped_column(Float)
    stability_score: Mapped[float | None] = mapped_column(Float)
    created_at: Mapped[datetime] = created_at_col()
