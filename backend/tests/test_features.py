from datetime import datetime, timezone

from app.ml.features import best_hour, build_daily_features, moving_average

UTC = timezone.utc


def _row(app, h1, m1, h2, m2, idle=False, fs=None):
    return {"app_name": app, "is_idle": idle, "focus_session_id": fs,
            "started_at": datetime(2026, 1, 5, h1, m1, tzinfo=UTC),
            "ended_at": datetime(2026, 1, 5, h2, m2, tzinfo=UTC)}


def test_features_basic():
    act = [_row("code", 4, 30, 5, 30, fs="x"),   # crosses hour (IST 10:00-11:00)
           _row("chrome", 5, 30, 5, 40),
           _row("x", 5, 40, 5, 50, idle=True),
           _row("code", 5, 50, 6, 0)]
    fs = [{"started_at": act[0]["started_at"], "ended_at": act[0]["ended_at"],
           "status": "completed"}]
    f = build_daily_features(act, fs, tz="Asia/Kolkata")
    assert f["active_min"] == 80 and f["idle_min"] == 10
    assert f["switch_count"] == 2 and f["session_count"] == 1
    assert f["focus_min"] == 60 and best_hour(f["hourly_focus_min"]) == 10


def test_moving_average():
    assert moving_average([10, 20, 30], 2) == [10, 15, 25]