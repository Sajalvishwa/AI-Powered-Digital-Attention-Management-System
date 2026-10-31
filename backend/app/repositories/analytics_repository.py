from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from app.models.activity_log import ActivitySession
from app.models.daily_metric import DailyMetric
from app.models.focus_session import FocusSession
from app.models.notification_event import NotificationEvent
from app.models.score import DailyScore

_ACT = ("app_name", "is_idle", "started_at", "ended_at", "focus_session_id")
_FOC = ("started_at", "ended_at", "status")


def fetch_activity(db, user_id, start, end):
    q = (select(ActivitySession).where(
        ActivitySession.user_id == user_id,
        ActivitySession.started_at >= start,
        ActivitySession.started_at < end,
    ).order_by(ActivitySession.started_at))
    return [{k: getattr(r, k) for k in _ACT} for r in db.scalars(q)]


def fetch_focus_sessions(db, user_id, start, end):
    q = select(FocusSession).where(
        FocusSession.user_id == user_id,
        FocusSession.started_at >= start,
        FocusSession.started_at < end,
    )
    return [{k: getattr(r, k) for k in _FOC} for r in db.scalars(q)]


def upsert_daily_metric(db, user_id, day, data):
    stmt = insert(DailyMetric).values(user_id=user_id, day=day, **data)
    stmt = stmt.on_conflict_do_update(
        constraint="uq_metric_user_day", set_=data
    )
    db.execute(stmt)
    db.commit()


def fetch_metrics_range(db, user_id, start_day, end_day):
    q = (select(DailyMetric).where(
        DailyMetric.user_id == user_id,
        DailyMetric.day >= start_day,
        DailyMetric.day <= end_day,
    ).order_by(DailyMetric.day))
    return list(db.scalars(q))

def fetch_notifications(db, user_id, start, end):
    q = select(NotificationEvent).where(
        NotificationEvent.user_id == user_id,
        NotificationEvent.received_at >= start,
        NotificationEvent.received_at < end,
    )
    return [{"app_name": r.app_name, "received_at": r.received_at} for r in db.scalars(q)]


def upsert_daily_score(db, user_id, day, data):
    stmt = insert(DailyScore).values(user_id=user_id, day=day, **data)
    stmt = stmt.on_conflict_do_update(constraint="uq_score_user_day", set_=data)
    db.execute(stmt)
    db.commit()


def fetch_scores_range(db, user_id, start_day, end_day):
    q = (select(DailyScore).where(
        DailyScore.user_id == user_id,
        DailyScore.day >= start_day,
        DailyScore.day <= end_day,
    ).order_by(DailyScore.day))
    return list(db.scalars(q))