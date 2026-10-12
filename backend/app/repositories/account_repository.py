"""Bulk deletes for 'delete my data'. Always filtered by user_id."""
import uuid

from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.models.activity_log import ActivitySession
from app.models.focus_session import FocusSession
from app.models.goal import Goal
from app.models.notification_event import NotificationEvent
from app.models.score import DailyScore

# order matters a little: activity first, then the rows it may point to
_TABLES = (
    ("activity_sessions", ActivitySession),
    ("focus_sessions", FocusSession),
    ("goals", Goal),
    ("notification_events", NotificationEvent),
    ("daily_scores", DailyScore),
)


def delete_all_user_data(db: Session, user_id: uuid.UUID) -> dict[str, int]:
    counts: dict[str, int] = {}
    for name, model in _TABLES:
        result = db.execute(delete(model).where(model.user_id == user_id))
        counts[name] = result.rowcount or 0
    return counts
