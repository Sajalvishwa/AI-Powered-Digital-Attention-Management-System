from datetime import date, datetime, time, timedelta, timezone
import uuid

API = "/api/v1"


def test_reversed_date_range_is_rejected(client, user_a):
    today = date.today()
    response = client.get(
        f"{API}/stats/range",
        params={"from": today.isoformat(), "to": (today - timedelta(days=1)).isoformat()},
        headers=user_a,
    )
    assert response.status_code == 422


def test_range_limit_is_enforced(client, user_a):
    today = date.today()

    # 92 days between endpoints means 93 calendar dates: reject.
    too_wide = client.get(
        f"{API}/stats/range",
        params={
            "from": (today - timedelta(days=92)).isoformat(),
            "to": today.isoformat(),
        },
        headers=user_a,
    )
    assert too_wide.status_code == 422

    # 91 days between endpoints means 92 calendar dates: allow.
    allowed = client.get(
        f"{API}/stats/range",
        params={
            "from": (today - timedelta(days=91)).isoformat(),
            "to": today.isoformat(),
        },
        headers=user_a,
    )
    assert allowed.status_code == 200
    assert len(allowed.json()["daily"]) == 92


def test_empty_range_returns_zero_totals_and_daily_buckets(client, user_a):
    day = date.today() - timedelta(days=5)
    response = client.get(
        f"{API}/stats/range",
        params={"from": day.isoformat(), "to": (day + timedelta(days=2)).isoformat()},
        headers=user_a,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["screen_time_sec"] == 0
    assert data["idle_sec"] == 0
    assert data["focus_sec"] == 0
    assert data["task_switches"] == 0
    assert data["top_apps"] == []
    assert [item["day"] for item in data["daily"]] == [
        day.isoformat(),
        (day + timedelta(days=1)).isoformat(),
        (day + timedelta(days=2)).isoformat(),
    ]
    assert all(item["active_sec"] == 0 and item["idle_sec"] == 0 for item in data["daily"])


def test_range_calculates_active_idle_focus_and_app_switches(
    client, user_a, make_session
):
    focus_response = client.post(
        f"{API}/focus-sessions",
        json={"planned_min": 25},
        headers=user_a,
    )
    assert focus_response.status_code == 201, focus_response.text
    focus_id = focus_response.json()["id"]

    # Use a past UTC date so the activity is safely within the accepted timestamp window.
    day = date.today() - timedelta(days=3)
    base = datetime.combine(day, time(10, 0), tzinfo=timezone.utc)

    def session_at(offset_min, seconds, app, *, idle=False, focus=False):
        start = base + timedelta(minutes=offset_min)
        end = start + timedelta(seconds=seconds)
        return make_session(
            app_name=app,
            started_at=start.isoformat(),
            ended_at=end.isoformat(),
            is_idle=idle,
            focus_session_id=focus_id if focus else None,
        )

    sessions = [
        session_at(0, 60, "Code.exe", focus=True),
        session_at(2, 300, "Idle", idle=True),
        session_at(4, 120, "Chrome.exe"),
        session_at(6, 30, "Slack.exe", focus=True),
    ]
    upload = client.post(
        f"{API}/activity/batch",
        json={"sessions": sessions},
        headers=user_a,
    )
    assert upload.status_code == 200, upload.text
    assert upload.json()["inserted"] == 4

    response = client.get(
        f"{API}/stats/range",
        params={"from": day.isoformat(), "to": day.isoformat()},
        headers=user_a,
    )
    assert response.status_code == 200, response.text
    data = response.json()

    assert data["screen_time_sec"] == 210
    assert data["idle_sec"] == 300
    assert data["focus_sec"] == 90
    assert data["task_switches"] == 2
    assert {app["app_name"]: app["total_sec"] for app in data["top_apps"]} == {
        "Code.exe": 60,
        "Chrome.exe": 120,
        "Slack.exe": 30,
    }
    assert data["daily"][0]["active_sec"] == 210
    assert data["daily"][0]["idle_sec"] == 300
