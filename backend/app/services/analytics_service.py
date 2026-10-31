from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from app.ml.features import DEFAULT_TZ, build_daily_features
from app.repositories import analytics_repository as repo


def compute_daily_metrics(db, user_id, day, tz=DEFAULT_TZ):
    start = datetime.combine(day, time.min, tzinfo=ZoneInfo(tz))
    end = start + timedelta(days=1)
    data = build_daily_features(
        repo.fetch_activity(db, user_id, start, end),
        repo.fetch_focus_sessions(db, user_id, start, end),
        tz,
    )
    repo.upsert_daily_metric(db, user_id, day, data)
    return data