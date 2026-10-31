from datetime import date, datetime, time, timedelta, timezone

import pytest

API = "/api/v1/analytics"
ENDPOINTS = ["daily", "focus-score", "distractions", "predictions", "insights", "summary"]


def _seed(client, headers, make_session, day=None):
    """6 activity rows on `day` (05:00-06:20 UTC = 10:30-11:50 IST, same calendar day)."""
    day = day or (date.today() - timedelta(days=3))
    focus = client.post("/api/v1/focus-sessions", json={"planned_min": 25}, headers=headers)
    assert focus.status_code == 201, focus.text
    fid = focus.json()["id"]
    base = datetime.combine(day, time(5, 0), tzinfo=timezone.utc)

    def row(start_min, minutes, app, *, idle=False, in_focus=False):
        start = base + timedelta(minutes=start_min)
        end = start + timedelta(minutes=minutes)
        return make_session(
            app_name=app, started_at=start.isoformat(), ended_at=end.isoformat(),
            is_idle=idle, focus_session_id=fid if in_focus else None,
        )

    sessions = [
        row(0, 30, "Code.exe", in_focus=True),
        row(30, 5, "Slack.exe", in_focus=True),    # interruption 1
        row(35, 15, "Code.exe", in_focus=True),    # interruption 2
        row(50, 4, "Idle", idle=True, in_focus=True),  # interruption 3 + long idle
        row(54, 16, "Code.exe", in_focus=True),
        row(70, 10, "Chrome.exe"),                 # interruption 4
    ]
    r = client.post("/api/v1/activity/batch", json={"sessions": sessions}, headers=headers)
    assert r.status_code == 200, r.text
    assert r.json()["inserted"] == 6
    return day


def _get(client, headers, name, day):
    r = client.get(f"{API}/{name}", params={"date": day.isoformat()}, headers=headers)
    assert r.status_code == 200, r.text
    return r.json()


@pytest.mark.parametrize("name", ENDPOINTS)
def test_empty_day_never_returns_500(client, user_a, name):
    _get(client, user_a, name, date.today() - timedelta(days=10))


def test_empty_day_content(client, user_a):
    day = date.today() - timedelta(days=10)
    assert _get(client, user_a, "insights", day)["insights"] == []
    s = _get(client, user_a, "summary", day)
    assert s["focus_score"] is None and s["best_hour"] is None
    assert "focus session" in s["suggestion"]


def test_daily_features_from_real_rows(client, user_a, make_session):
    day = _seed(client, user_a, make_session)
    f = _get(client, user_a, "daily", day)["features"]
    assert f["active_min"] == 76 and f["idle_min"] == 4
    assert f["focus_min"] == 66 and f["switch_count"] == 3
    assert len(f["hourly_active_min"]) == 24
    assert f["top_apps"]["Code.exe"] == 61


def test_distractions_detected(client, user_a, make_session):
    day = _seed(client, user_a, make_session)
    d = _get(client, user_a, "distractions", day)
    assert len(d["interruptions"]) == 4
    assert len(d["frequent_clusters"]) >= 1
    assert "long_idle" in {e["type"] for e in d["focus_loss"]}
    assert {x["app"] for x in d["attention_leaks"]} == {"Slack.exe", "Chrome.exe"}  # Code.exe is productive
    assert d["notification_impact"]["total"] == 0


def test_scores(client, user_a, make_session):
    day = _seed(client, user_a, make_session)
    s = _get(client, user_a, "focus-score", day)
    assert 0 < s["focus_score"] <= 100
    assert s["productivity_score"] == 100.0       # only Code.exe is classified
    assert s["stability_score"] is None            # no completed focus session on that day


def test_insights_and_summary(client, user_a, make_session):
    day = _seed(client, user_a, make_session)
    types = {i["type"] for i in _get(client, user_a, "insights", day)["insights"]}
    assert {"pattern", "leak", "interruptions"} <= types
    s = _get(client, user_a, "summary", day)
    assert s["top_distraction"] in {"Slack.exe", "Chrome.exe"}
    assert s["best_hour"] is not None and s["focus_score"] is not None


def test_predictions_shape(client, user_a, make_session):
    day = _seed(client, user_a, make_session)
    p = _get(client, user_a, "predictions", day)
    assert {"focus_degradation", "productivity_risk", "attention_fatigue", "ml_forecast"} <= set(p)
    assert p["ml_forecast"]["available"] is False   # only 1 day of history
    assert "reason" in p["ml_forecast"]


def test_other_user_cannot_see_my_data(client, user_a, user_b, make_session):
    day = _seed(client, user_a, make_session)
    f = _get(client, user_b, "daily", day)["features"]
    assert f["active_min"] == 0 and f["top_apps"] == {}
    assert _get(client, user_b, "insights", day)["insights"] == []


def test_future_date_rejected(client, user_a):
    r = client.get(f"{API}/summary", params={"date": (date.today() + timedelta(days=2)).isoformat()},
                   headers=user_a)
    assert r.status_code == 422


def test_report_is_idempotent(client, user_a, make_session):
    day = _seed(client, user_a, make_session)
    assert _get(client, user_a, "focus-score", day) == _get(client, user_a, "focus-score", day)


def test_trend_reads_stored_scores(client, user_a, make_session):
    day = _seed(client, user_a, make_session)
    _get(client, user_a, "focus-score", day)       # computes + stores that day's score
    r = client.get(f"{API}/trend", params={"days": 7}, headers=user_a)
    assert r.status_code == 200, r.text
    days = r.json()["days"]
    assert len(days) == 7
    stored = {d["day"]: d["focus_score"] for d in days}
    assert stored[day.isoformat()] is not None
    assert sum(v is not None for v in stored.values()) == 1


def test_trend_validates_days(client, user_a):
    for bad in (1, 100):
        assert client.get(f"{API}/trend", params={"days": bad}, headers=user_a).status_code == 422