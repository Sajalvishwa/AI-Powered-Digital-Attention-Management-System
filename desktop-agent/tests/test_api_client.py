import uuid
from datetime import datetime, timezone

import pytest

from app.api_client import ApiClient, ApiError, AuthRequired, NetworkError, RateLimited, ServerError
from app.token_store import Tokens, TokenStore
from tests.fake_backend import MemoryKeyring, payload, running_backend


def make_client(url, store=None, timeout=3.0):
    store = store or TokenStore(MemoryKeyring())
    return ApiClient(url, store, timeout=timeout), store


def logged_in_client(backend):
    client, store = make_client(backend.url)
    client.login("me@example.com", "Strong123")
    return client, store


def test_login_stores_tokens():
    with running_backend() as backend:
        client, store = make_client(backend.url)
        assert not client.is_logged_in()
        client.login("me@example.com", "Strong123")
        assert client.is_logged_in() and client.email() == "me@example.com"
        assert store.load().access == "acc-0"


def test_wrong_password():
    with running_backend() as backend:
        client, store = make_client(backend.url)
        with pytest.raises(ApiError) as exc:
            client.login("me@example.com", "nope")
        assert exc.value.status == 401 and store.load() is None


def test_upload_batch_sends_the_sessions():
    with running_backend() as backend:
        client, _ = logged_in_client(backend)
        result = client.upload_batch([payload(1), payload(2, title="Docs")])
        assert result["inserted"] == 2
        first, second = backend.all_sessions
        assert first["client_id"].endswith("000000000001") and "window_title" not in first
        assert second["window_title"] == "Docs"


def test_objects_with_to_payload_and_uuid_datetime_values_are_accepted():
    class Session:
        def to_payload(self):
            return {
                "client_id": uuid.UUID("11111111-1111-4111-8111-111111111111"),
                "app_name": "Code.exe",
                "window_title": None,
                "is_idle": False,
                "started_at": datetime(2026, 10, 12, 9, 0, tzinfo=timezone.utc),
                "ended_at": datetime(2026, 10, 12, 9, 1, tzinfo=timezone.utc),
                "focus_session_id": None,
            }

    with running_backend() as backend:
        client, _ = logged_in_client(backend)
        client.upload_batch([Session()])
        sent = backend.all_sessions[0]
        assert sent["client_id"] == "11111111-1111-4111-8111-111111111111"
        assert sent["started_at"] == "2026-10-12T09:00:00+00:00"


def test_bad_input_is_rejected_before_any_request():
    with running_backend() as backend:
        client, _ = logged_in_client(backend)
        with pytest.raises(ValueError):
            client.upload_batch([])
        with pytest.raises(ValueError):
            client.upload_batch([payload(i) for i in range(501)])
        with pytest.raises(TypeError):
            client.upload_batch(["not a session"])
        assert backend.batches == []


def test_expired_access_token_is_refreshed_automatically():
    with running_backend() as backend:
        client, store = logged_in_client(backend)
        old_refresh = store.load().refresh
        backend.expire_access()  # the server no longer accepts our access token
        client.upload_batch([payload(1)])
        assert len(backend.all_sessions) == 1
        assert store.load().refresh != old_refresh  # the new token pair was saved


def test_refresh_rejected_means_login_required_and_tokens_cleared():
    with running_backend() as backend:
        client, store = logged_in_client(backend)
        backend.expire_access()
        backend.refresh = "something-else"  # our refresh token is no longer valid
        with pytest.raises(AuthRequired):
            client.upload_batch([payload(1)])
        assert store.load() is None and not client.is_logged_in()


def test_not_logged_in():
    with running_backend() as backend:
        client, _ = make_client(backend.url)
        with pytest.raises(AuthRequired):
            client.upload_batch([payload(1)])


def test_validation_error_message_does_not_leak_request_data():
    with running_backend() as backend:
        client, _ = logged_in_client(backend)
        backend.reject_app = "Bank.exe"
        with pytest.raises(ApiError) as exc:
            client.upload_batch([payload(1, app="Bank.exe", title="Account 1234 secret")])
        assert exc.value.status == 422
        assert "secret" not in str(exc.value) and "Bank" not in str(exc.value)


def test_server_error_and_rate_limit_are_distinguished():
    with running_backend() as backend:
        client, _ = logged_in_client(backend)
        backend.force_status = 500
        with pytest.raises(ServerError):
            client.upload_batch([payload(1)])
        backend.force_status = 429
        with pytest.raises(RateLimited) as exc:
            client.upload_batch([payload(1)])
        assert exc.value.retry_after == 7


def test_unreachable_server_raises_network_error():
    client, _ = make_client("http://127.0.0.1:9/api/v1", timeout=1.0)  # nothing listens on port 9
    with pytest.raises(NetworkError):
        client.login("me@example.com", "Strong123")
    assert client.health() is False


def test_get_settings_and_health():
    with running_backend() as backend:
        client, _ = logged_in_client(backend)
        backend.settings = {"store_window_titles": True, "ignored_apps": ["a"], "idle_threshold_sec": 60}
        assert client.get_settings()["idle_threshold_sec"] == 60
        assert client.health() is True


def test_logout_clears_tokens_and_tells_the_server():
    with running_backend() as backend:
        client, store = logged_in_client(backend)
        client.logout()
        assert store.load() is None and not client.is_logged_in()
        assert backend.logout_calls == 1


def test_tokens_already_in_the_keyring_are_used():
    with running_backend() as backend:
        store = TokenStore(MemoryKeyring())
        store.save(Tokens("acc-0", "ref-0", "me@example.com"))
        client = ApiClient(backend.url, store, timeout=3.0)
        assert client.is_logged_in()
        client.upload_batch([payload(1)])
