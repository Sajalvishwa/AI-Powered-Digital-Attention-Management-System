"""Focus session rules: one active session per user, valid state changes only."""
import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.focus_session import FocusSession
from app.models.user import User
from app.repositories import focus_repository as repo
from app.schemas.focus import FocusStart, FocusUpdate

_ALLOWED_FROM = {
    "pause": ("running",),
    "resume": ("paused",),
    "stop": ("running", "paused"),
    "cancel": ("running", "paused"),
}
_NEW_STATUS = {"pause": "paused", "resume": "running", "stop": "completed", "cancel": "cancelled"}


def start(db: Session, user: User, data: FocusStart) -> FocusSession:
    conflict = HTTPException(status.HTTP_409_CONFLICT, "A focus session is already active")
    if repo.get_active(db, user.id):
        raise conflict
    try:
        fs = repo.create(db, user.id, data.planned_min, data.label, datetime.now(timezone.utc))
        db.commit()
    except IntegrityError:  # unique index: two starts at the same time
        db.rollback()
        raise conflict
    return fs


def update(db: Session, user: User, focus_id: uuid.UUID, data: FocusUpdate) -> FocusSession:
    fs = repo.get_owned(db, focus_id, user.id)
    if fs is None:  # also when it belongs to someone else: do not reveal it exists
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Focus session not found")
    if fs.status not in _ALLOWED_FROM[data.action]:
        raise HTTPException(
            status.HTTP_409_CONFLICT, f"Cannot {data.action} a session that is {fs.status}"
        )
    fs.status = _NEW_STATUS[data.action]
    if data.action in ("stop", "cancel"):
        fs.ended_at = datetime.now(timezone.utc)
    if data.action == "stop" and data.switch_count is not None:
        fs.switch_count = data.switch_count
    db.commit()
    return fs


def active(db: Session, user: User) -> FocusSession | None:
    return repo.get_active(db, user.id)


def history(db: Session, user: User, limit: int, offset: int) -> list[FocusSession]:
    return repo.list_for_user(db, user.id, limit, offset)
