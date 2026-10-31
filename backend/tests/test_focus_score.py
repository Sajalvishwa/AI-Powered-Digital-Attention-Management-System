from datetime import datetime, timedelta, timezone

from app.ml.focus_score import (
    completed_lengths_min, focus_score, productivity_score,
    stability_score, trend_slope,
)

F = {"active_min": 120, "focus_min": 60, "avg_session_min": 25, "switch_count": 10}


def test_focus_score_formula():
    # ratio 50, session 100, switch penalty 25, notif penalty 20
    assert focus_score(F, 0.2) == 73.0


def test_focus_score_no_activity():
    assert focus_score({**F, "active_min": 0}) is None


def test_focus_score_clamped():
    f = {"active_min": 60, "focus_min": 999, "avg_session_min": 999, "switch_count": 0}
    assert focus_score(f) == 100.0


def test_productivity():
    apps = {"Code.exe": 60, "Instagram": 20, "chrome.exe": 30}  # chrome ignored
    assert productivity_score(apps) == 75.0
    assert productivity_score({"chrome.exe": 30}) is None


def test_stability():
    assert stability_score([20, 20, 20]) == 100.0
    assert stability_score([10, 30]) == 50.0
    assert stability_score([20]) is None


def test_completed_lengths():
    t = datetime(2026, 1, 5, 9, 0, tzinfo=timezone.utc)
    fs = [
        {"started_at": t, "ended_at": t + timedelta(minutes=25), "status": "completed"},
        {"started_at": t, "ended_at": t + timedelta(minutes=5), "status": "cancelled"},
    ]
    assert completed_lengths_min(fs) == [25.0]


def test_trend_slope():
    assert trend_slope([50, 60, 70]) == 10.0
    assert trend_slope([70, 60, 50]) == -10.0
    assert trend_slope([50, 60]) is None

def test_trailing_run_ignores_gaps():
    from datetime import date
    from app.ml.focus_score import trailing_run
    d = lambda n: date(2026, 10, n)
    assert trailing_run([(d(25), 50), (d(26), 52), (d(30), 31), (d(31), 30)]) == [31, 30]
    assert trailing_run([(d(30), 31)]) == [31]
    assert trailing_run([]) == []