from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from app.offline_buffer import SQLiteBuffer


START = datetime(2026, 10, 12, 10, 0, tzinfo=timezone.utc)


def make_session(**overrides):
    session = {
        "client_id": str(uuid4()),
        "app_name": "Code.exe",
        "window_title": None,
        "is_idle": False,
        "started_at": START.isoformat(),
        "ended_at": (START + timedelta(seconds=30)).isoformat(),
        "focus_session_id": None,
    }
    session.update(overrides)
    return session


@pytest.fixture
def buffer(tmp_path):
    return SQLiteBuffer(tmp_path / "buffer.db")


def test_database_file_is_created(tmp_path):
    db_path = tmp_path / "nested" / "buffer.db"

    SQLiteBuffer(db_path)

    assert db_path.is_file()


def test_save_and_read_pending_session(buffer):
    session = make_session()

    assert buffer.save_session(session) is True

    pending = buffer.get_pending_sessions()

    assert len(pending) == 1
    assert pending[0]["client_id"] == session["client_id"]
    assert pending[0]["app_name"] == "Code.exe"
    assert pending[0]["is_idle"] is False


def test_duplicate_client_id_is_not_inserted(buffer):
    session = make_session()

    assert buffer.save_session(session) is True
    assert buffer.save_session(session) is False

    assert buffer.count_pending() == 1


def test_pending_limit_is_respected(buffer):
    for _ in range(3):
        buffer.save_session(make_session())

    assert len(buffer.get_pending_sessions(limit=2)) == 2


def test_invalid_limit_is_rejected(buffer):
    with pytest.raises(ValueError):
        buffer.get_pending_sessions(limit=0)


def test_mark_synced_removes_session_from_pending_results(buffer):
    session = make_session()
    buffer.save_session(session)

    updated = buffer.mark_synced([session["client_id"]])

    assert updated == 1
    assert buffer.get_pending_sessions() == []
    assert buffer.count_pending() == 0


def test_mark_synced_is_idempotent(buffer):
    session = make_session()
    buffer.save_session(session)

    assert buffer.mark_synced([session["client_id"]]) == 1
    assert buffer.mark_synced([session["client_id"]]) == 0


def test_unknown_client_id_does_not_change_database(buffer):
    assert buffer.mark_synced([str(uuid4())]) == 0


def test_empty_sync_list_returns_zero(buffer):
    assert buffer.mark_synced([]) == 0


def test_invalid_client_id_is_rejected(buffer):
    with pytest.raises(ValueError, match="valid UUID"):
        buffer.save_session(make_session(client_id="not-a-uuid"))


def test_naive_timestamps_are_rejected(buffer):
    session = make_session(
        started_at="2026-10-12T10:00:00",
    )

    with pytest.raises(ValueError, match="timezone-aware"):
        buffer.save_session(session)


def test_end_before_start_is_rejected(buffer):
    session = make_session(
        ended_at=(START - timedelta(seconds=1)).isoformat(),
    )

    with pytest.raises(ValueError, match="cannot precede"):
        buffer.save_session(session)


def test_invalid_idle_type_is_rejected(buffer):
    with pytest.raises(ValueError, match="boolean"):
        buffer.save_session(make_session(is_idle=1))


def test_sessions_survive_buffer_recreation(tmp_path):
    db_path = tmp_path / "buffer.db"
    session = make_session()

    SQLiteBuffer(db_path).save_session(session)

    reopened = SQLiteBuffer(db_path)

    assert len(reopened.get_pending_sessions()) == 1
    assert reopened.get_pending_sessions()[0]["client_id"] == session["client_id"]


def test_synced_records_are_retained_but_not_pending(buffer):
    session = make_session()
    buffer.save_session(session)

    buffer.mark_synced([session["client_id"]])

    # A repeated insert must not recreate the pending session.
    assert buffer.save_session(session) is False
    assert buffer.get_pending_sessions() == []