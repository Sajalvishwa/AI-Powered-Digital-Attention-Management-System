from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from app.ml.features import DEFAULT_TZ
from app.ml.forecast import merge_row, predict_next
from app.ml.predictor import attention_fatigue, focus_degradation, productivity_risk
from app.repositories import analytics_repository as repo
from app.ml.focus_score import trailing_run

def get_predictions(db, user_id, day, tz=DEFAULT_TZ):
    first = day - timedelta(days=6)
    rows = repo.fetch_scores_range(db, user_id, first, day)
    focus = trailing_run([(r.day, r.focus_score) for r in rows if r.focus_score is not None])
    prod = trailing_run([(r.day, r.productivity_score) for r in rows if r.productivity_score is not None])

    by_day = {r.day: r for r in rows}
    metrics = repo.fetch_metrics_range(db, user_id, first, day)
    history = [merge_row(m, by_day[m.day]) for m in metrics if m.day in by_day]

    zone = ZoneInfo(tz)
    start = datetime.combine(first, time.min, tzinfo=zone)
    end = datetime.combine(day, time.min, tzinfo=zone) + timedelta(days=1)
    fatigue = attention_fatigue(repo.fetch_activity(db, user_id, start, end))
    

    return {
        "focus_degradation": focus_degradation(focus),
        "productivity_risk": productivity_risk(prod),
        "attention_fatigue": {
            "sessions_checked": len(fatigue),
            "fatigued_sessions": sum(1 for f in fatigue if f["fatigued"]),
            "details": fatigue,
        },
        "ml_forecast": predict_next(history),
    }