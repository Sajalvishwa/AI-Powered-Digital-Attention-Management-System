"""Rules of /activity/batch: idempotency, privacy defaults, ignore-list, validation."""
API = "/api/v1"


def test_same_batch_twice_is_safe(client, user_a, make_session):
    batch = {"sessions": [make_session(), make_session(minutes_ago=20)]}
    first = client.post(f"{API}/activity/batch", json=batch, headers=user_a).json()
    second = client.post(f"{API}/activity/batch", json=batch, headers=user_a).json()
    assert first == {"received": 2, "inserted": 2, "duplicates": 0, "skipped": 0}
    assert second == {"received": 2, "inserted": 0, "duplicates": 2, "skipped": 0}
    assert len(client.get(f"{API}/activity/recent", headers=user_a).json()) == 2


def test_window_titles_dropped_unless_user_opts_in(client, user_a, make_session):
    secret = make_session(window_title="My Bank - Account 1234")
    client.post(f"{API}/activity/batch", json={"sessions": [secret]}, headers=user_a)
    assert client.get(f"{API}/activity/recent", headers=user_a).json()[0]["window_title"] is None

    client.put(f"{API}/users/me/settings", json={"store_window_titles": True}, headers=user_a)
    allowed = make_session(minutes_ago=5, window_title="Notes")
    client.post(f"{API}/activity/batch", json={"sessions": [allowed]}, headers=user_a)

    rows = {r["client_id"]: r for r in client.get(f"{API}/activity/recent", headers=user_a).json()}
    assert rows[allowed["client_id"]]["window_title"] == "Notes"
    assert rows[secret["client_id"]]["window_title"] is None  # old data stays private


def test_ignored_apps_are_skipped_case_insensitive(client, user_a, make_session):
    client.put(f"{API}/users/me/settings", json={"ignored_apps": ["chrome.exe"]}, headers=user_a)
    batch = {"sessions": [make_session(app_name="Chrome.EXE"), make_session(app_name="Code.exe")]}
    result = client.post(f"{API}/activity/batch", json=batch, headers=user_a).json()
    assert result == {"received": 2, "inserted": 1, "duplicates": 0, "skipped": 1}


def test_invalid_batches_are_rejected(client, user_a, make_session):
    bad_order = make_session()
    bad_order["started_at"], bad_order["ended_at"] = bad_order["ended_at"], bad_order["started_at"]
    assert client.post(f"{API}/activity/batch", json={"sessions": [bad_order]}, headers=user_a).status_code == 422
    assert client.post(f"{API}/activity/batch", json={"sessions": []}, headers=user_a).status_code == 422
