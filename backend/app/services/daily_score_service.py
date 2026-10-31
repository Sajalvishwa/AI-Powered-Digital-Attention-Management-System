from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from app.ml.distraction import notification_impact
from app.ml.features import DEFAULT_TZ
from app.ml.focus_score import (
    completed_lengths_min, focus_score, productivity_score,
    stability_score, trend_slope,
)
from app.repositories import analytics_repository as repo
from app.services.analytics_service import compute_daily_metrics
from app.ml.focus_score import trailing_run


def compute_and_save_scores(db, user_id, day, tz=DEFAULT_TZ):
    start = datetime.combine(day, time.min, tzinfo=ZoneInfo(tz))
    end = start + timedelta(days=1)

    features = compute_daily_metrics(db, user_id, day, tz)  # also saves daily_metrics
    activity = repo.fetch_activity(db, user_id, start, end)
    focus = repo.fetch_focus_sessions(db, user_id, start, end)
    notifs = repo.fetch_notifications(db, user_id, start, end)

    impact = notification_impact(activity, notifs)
    scores = {
        "focus_score": focus_score(features, impact["impact_rate"]),
        "productivity_score": productivity_score(features["top_apps"]),
        "stability_score": stability_score(completed_lengths_min(focus)),
    }
    repo.upsert_daily_score(db, user_id, day, scores)
    return scores


def concentration_trend(db, user_id, day):
    """Slope of focus_score over the last 7 days (days without a score are skipped)."""
    rows = repo.fetch_scores_range(db, user_id, day - timedelta(days=6), day)
    return trend_slope(trailing_run([(r.day, r.focus_score) for r in rows if r.focus_score is not None]))