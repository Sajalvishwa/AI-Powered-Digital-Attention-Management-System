from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from app.ml.distraction import (
    focus_loss_events, frequent_interruptions, high_switch_hours,
    interruption_events, notification_impact,
)
from app.ml.features import DEFAULT_TZ
from app.ml.insights import attention_leaks, build_insights, daily_summary
from app.repositories import analytics_repository as repo
from app.services.daily_score_service import compute_and_save_scores, concentration_trend
from app.services.prediction_service import get_predictions

FEATURE_KEYS = (
    "active_min", "idle_min", "focus_min", "session_count", "avg_session_min",
    "longest_session_min", "switch_count", "hourly_active_min",
    "hourly_focus_min", "hourly_switches", "top_apps",
)


def build_day_report(db, user_id, day, tz=DEFAULT_TZ):
    scores = compute_and_save_scores(db, user_id, day, tz)  # also saves daily_metrics
    row = repo.fetch_metrics_range(db, user_id, day, day)[0]
    features = {k: getattr(row, k) for k in FEATURE_KEYS}

    start = datetime.combine(day, time.min, tzinfo=ZoneInfo(tz))
    end = start + timedelta(days=1)
    activity = repo.fetch_activity(db, user_id, start, end)
    focus = repo.fetch_focus_sessions(db, user_id, start, end)
    notifs = repo.fetch_notifications(db, user_id, start, end)

    events = interruption_events(activity)
    clusters = frequent_interruptions(events)
    high = high_switch_hours(features["hourly_switches"])
    impact = notification_impact(activity, notifs)
    leaks = attention_leaks(events)
    preds = get_predictions(db, user_id, day, tz)
    insights = build_insights(features, scores, leaks, clusters, high, impact, preds)

    return {
        "day": day,
        "features": features,
        "scores": {**scores, "concentration_trend": concentration_trend(db, user_id, day)},
        "distractions": {
            "interruptions": events,
            "frequent_clusters": clusters,
            "high_switch_hours": high,
            "focus_loss": focus_loss_events(activity, focus),
            "notification_impact": impact,
            "attention_leaks": leaks,
        },
        "predictions": preds,
        "insights": insights,
        "summary": daily_summary(day, scores, features, leaks, insights),
    }