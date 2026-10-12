"""DB queries for focus sessions."""
import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.focus_session import FocusSession


def get_active(db: Session, user_id: uuid.UUID) -> FocusSession | None:
    stmt = select(FocusSession).where(
        FocusSession.user_id == user_id, FocusSession.status.in_(("running", "paused"))
    )
    return db.scalar(stmt)


def get_owned(db: Session, focus_id: uuid.UUID, user_id: uuid.UUID) -> FocusSession | None:
    stmt = select(FocusSession).where(FocusSession.id == focus_id, FocusSession.user_id == user_id)
    return db.scalar(stmt)


def create(
    db: Session, user_id: uuid.UUID, planned_min: int, label: str | None, started_at: datetime
) -> FocusSession:
    fs = FocusSession(
        user_id=user_id, planned_min=planned_min, label=label, started_at=started_at
    )
    db.add(fs)
    db.flush()
    return fs


def list_for_user(db: Session, user_id: uuid.UUID, limit: int, offset: int) -> list[FocusSession]:
    stmt = (
        select(FocusSession)
        .where(FocusSession.user_id == user_id)
        .order_by(FocusSession.started_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return list(db.scalars(stmt).all())


def existing_ids(db: Session, user_id: uuid.UUID, ids: set[uuid.UUID]) -> set[uuid.UUID]:
    """Which of these focus session ids really belong to this user."""
    if not ids:
        return set()
    stmt = select(FocusSession.id).where(FocusSession.user_id == user_id, FocusSession.id.in_(ids))
    return set(db.scalars(stmt).all())