import uuid

from datetime import datetime, timedelta, timezone

from app.api_client import ApiClient
from app.offline_buffer import SQLiteBuffer
from app.sync_worker import SyncWorker
from app.token_store import TokenStore
from tests.fake_backend import (
    MemoryKeyring,
    running_backend,
)


def make_session(number: int) -> dict:
    started = datetime.now(timezone.utc)
    ended = started + timedelta(minutes=1)

    return {
        "client_id": str(
            uuid.UUID(
                f"00000000-0000-4000-8000-{number:012d}"
            )
        ),
        "app_name": "Code.exe",
        "window_title": None,
        "is_idle": False,
        "started_at": started,
        "ended_at": ended,
        "focus_session_id": None,
    }


def make_buffer(tmp_path) -> SQLiteBuffer:
    return SQLiteBuffer(tmp_path / "buffer.db")


def test_sync_success_marks_sessions_synced(tmp_path):
    buffer = make_buffer(tmp_path)
    buffer.save_session(make_session(1))
    buffer.save_session(make_session(2))

    with running_backend() as backend:
        client = ApiClient(
            backend.url,
            TokenStore(MemoryKeyring()),
        )
        client.login("me@example.com", "Strong123")

        worker = SyncWorker(buffer, client)
        result = worker.sync_once()

        assert result.success is True
        assert result.attempted == 2
        assert result.synced == 2
        assert result.pending == 0
        assert len(backend.all_sessions) == 2
        assert buffer.count_pending() == 0


def test_not_logged_in_keeps_sessions_pending(tmp_path):
    buffer = make_buffer(tmp_path)
    buffer.save_session(make_session(1))

    with running_backend() as backend:
        client = ApiClient(
            backend.url,
            TokenStore(MemoryKeyring()),
        )

        worker = SyncWorker(buffer, client)
        result = worker.sync_once()

        assert result.success is False
        assert result.reason == "login_required"
        assert buffer.count_pending() == 1
        assert backend.all_sessions == []


def test_server_error_keeps_sessions_pending(tmp_path):
    buffer = make_buffer(tmp_path)
    buffer.save_session(make_session(1))

    with running_backend() as backend:
        client = ApiClient(
            backend.url,
            TokenStore(MemoryKeyring()),
        )
        client.login("me@example.com", "Strong123")

        backend.force_status = 500

        worker = SyncWorker(buffer, client)
        result = worker.sync_once()

        assert result.success is False
        assert buffer.count_pending() == 1


def test_empty_buffer_does_not_send_batch(tmp_path):
    buffer = make_buffer(tmp_path)

    with running_backend() as backend:
        client = ApiClient(
            backend.url,
            TokenStore(MemoryKeyring()),
        )
        client.login("me@example.com", "Strong123")

        worker = SyncWorker(buffer, client)
        result = worker.sync_once()

        assert result.success is True
        assert result.attempted == 0
        assert result.pending == 0
        assert backend.batches == []


def test_batch_size_cannot_exceed_backend_limit(tmp_path):
    buffer = make_buffer(tmp_path)

    with running_backend() as backend:
        client = ApiClient(
            backend.url,
            TokenStore(MemoryKeyring()),
        )

        try:
            SyncWorker(buffer, client, batch_size=501)
        except ValueError:
            pass
        else:
            raise AssertionError(
                "Expected invalid batch size to be rejected."
            )