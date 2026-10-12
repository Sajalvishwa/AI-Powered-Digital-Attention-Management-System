import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import TIMESTAMPTZ, Base, uuid_pk


class NotificationEvent(Base):
    """Table ready now; actual tracking is deferred (see memory.md decision #7)."""

    __tablename__ = "notification_events"
    __table_args__ = (
        UniqueConstraint("user_id", "client_id", name="uq_notif_user_client"),
        Index("idx_notif_user_time", "user_id", "received_at"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    client_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True))
    user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE")
    )
    app_name: Mapped[str] = mapped_column(String(255))
    received_at: Mapped[datetime] = mapped_column(TIMESTAMPTZ)
