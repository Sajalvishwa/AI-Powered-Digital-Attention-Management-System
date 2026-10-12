"""User A must never see or change User B's data (and vice versa)."""
from datetime import date, timedelta

API = "/api/v1"


def wide_range() -> dict:
    today = date.today()
    return {
        "from": (today - timedelta(days=1)).isoformat(),
        "to": (today + timedelta(days=1)).isoformat(),
    }


def test_cannot_touch_other_users_focus_session(client, user_a, user_b):
    r = client.post(f"{API}/focus-sessions", json={"planned_min": 25}, headers=user_a)
    assert r.status_code == 201
    focus_id = r.json()["id"]

    # B cannot stop A's session; the answer is 404 so B can't even learn it exists
    r = client.patch(f"{API}/focus-sessions/{focus_id}", json={"action": "stop"}, headers=user_b)
    assert r.status_code == 404

    assert client.get(f"{API}/focus-sessions", headers=user_b).json() == []
    assert client.get(f"{API}/focus-sessions/active", headers=user_b).json() is None
    assert client.get(f"{API}/focus-sessions/active", headers=user_a).json()["status"] == "running"

    # B can run their own session while A's is active
    r = client.post(f"{API}/focus-sessions", json={"planned_min": 10}, headers=user_b)
    assert r.status_code == 201


def test_cannot_touch_other_users_goals(client, user_a, user_b):
    r = client.post(
        f"{API}/goals", json={"type": "daily_focus_min", "target_value": 180}, headers=user_a
    )
    assert r.status_code == 201
    goal_id = r.json()["id"]

    assert client.patch(
        f"{API}/goals/{goal_id}", json={"target_value": 999}, headers=user_b
    ).status_code == 404
    assert client.delete(f"{API}/goals/{goal_id}", headers=user_b).status_code == 404
    assert client.get(f"{API}/goals", headers=user_b).json() == []

    mine = client.get(f"{API}/goals", headers=user_a).json()
    assert len(mine) == 1 and mine[0]["target_value"] == 180

    # the "one active goal per type" rule is per user, not global
    r = client.post(
        f"{API}/goals", json={"type": "daily_focus_min", "target_value": 120}, headers=user_b
    )
    assert r.status_code == 201


def test_activity_and_stats_are_private(client, user_a, user_b, make_session):
    r = client.post(f"{API}/activity/batch", json={"sessions": [make_session()]}, headers=user_a)
    assert r.status_code == 200 and r.json()["inserted"] == 1

    assert len(client.get(f"{API}/activity/recent", headers=user_a).json()) == 1
    assert client.get(f"{API}/activity/recent", headers=user_b).json() == []

    a = client.get(f"{API}/stats/range", params=wide_range(), headers=user_a).json()
    b = client.get(f"{API}/stats/range", params=wide_range(), headers=user_b).json()
    assert a["screen_time_sec"] == 60
    assert b["screen_time_sec"] == 0 and b["top_apps"] == []
    assert client.get(f"{API}/stats/today", headers=user_b).json()["screen_time_sec"] == 0


def test_same_client_id_allowed_for_different_users(client, user_a, user_b, make_session):
    session = make_session()
    ra = client.post(f"{API}/activity/batch", json={"sessions": [session]}, headers=user_a)
    rb = client.post(f"{API}/activity/batch", json={"sessions": [session]}, headers=user_b)
    assert ra.json()["inserted"] == 1
    assert rb.json()["inserted"] == 1  # uniqueness is per (user, client_id)


def test_cannot_link_activity_to_other_users_focus_session(client, user_a, user_b, make_session):
    focus_id = client.post(
        f"{API}/focus-sessions", json={"planned_min": 25}, headers=user_a
    ).json()["id"]

    # B tries to attach their activity to A's focus session -> link is dropped
    r = client.post(
        f"{API}/activity/batch",
        json={"sessions": [make_session(focus_session_id=focus_id)]},
        headers=user_b,
    )
    assert r.json()["inserted"] == 1
    assert client.get(f"{API}/activity/recent", headers=user_b).json()[0]["focus_session_id"] is None

    # A linking to their own focus session works
    client.post(
        f"{API}/activity/batch",
        json={"sessions": [make_session(focus_session_id=focus_id)]},
        headers=user_a,
    )
    assert client.get(f"{API}/activity/recent", headers=user_a).json()[0]["focus_session_id"] == focus_id


def test_settings_are_per_user(client, user_a, user_b):
    r = client.put(f"{API}/users/me/settings", json={"daily_focus_goal_min": 300}, headers=user_a)
    assert r.status_code == 200
    assert client.get(f"{API}/users/me/settings", headers=user_b).json()["daily_focus_goal_min"] == 180


def test_delete_my_data_only_deletes_my_data(client, user_a, user_b, make_session):
    for headers in (user_a, user_b):
        client.post(f"{API}/goals", json={"type": "max_task_switches", "target_value": 100}, headers=headers)
        client.post(f"{API}/activity/batch", json={"sessions": [make_session()]}, headers=headers)
    client.post(f"{API}/focus-sessions", json={"planned_min": 25}, headers=user_a)

    # safety switch: must confirm
    assert client.delete(f"{API}/users/me/data", headers=user_a).status_code == 400

    r = client.delete(f"{API}/users/me/data", params={"confirm": "true"}, headers=user_a)
    assert r.status_code == 200
    deleted = r.json()["deleted"]
    assert deleted["activity_sessions"] == 1
    assert deleted["goals"] == 1
    assert deleted["focus_sessions"] == 1

    # A is empty but the account still works
    assert client.get(f"{API}/activity/recent", headers=user_a).json() == []
    assert client.get(f"{API}/goals", headers=user_a).json() == []
    assert client.get(f"{API}/users/me", headers=user_a).status_code == 200

    # B is untouched
    assert len(client.get(f"{API}/activity/recent", headers=user_b).json()) == 1
    assert len(client.get(f"{API}/goals", headers=user_b).json()) == 1
