
from datetime import datetime, timedelta, timezone

from app.activity_collector import ActivityCollector
from app.offline_buffer import SQLiteBuffer
from app.session_builder import ActivityObservation, SessionBuilder


START = datetime(2026, 10, 12, 10, 0, tzinfo=timezone.utc)


def make_observation(app_name, seconds):
    return ActivityObservation(
        app_name=app_name,
        is_idle=False,
        observed_at=START + timedelta(seconds=seconds),
    )


def test_completed_session_is_saved_to_sqlite(tmp_path):
    buffer = SQLiteBuffer(tmp_path / "buffer.db")
    collector = ActivityCollector(SessionBuilder(), buffer)

    collector.observe(make_observation("Code.exe", 0))
    completed = collector.observe(make_observation("chrome.exe", 10))

    assert len(completed) == 1
    assert completed[0].app_name == "Code.exe"

    pending = buffer.get_pending_sessions()
    assert len(pending) == 1
    assert pending[0]["app_name"] == "Code.exe"
    assert pending[0]["started_at"] == START.isoformat()
    assert pending[0]["ended_at"] == (
        START + timedelta(seconds=10)
    ).isoformat()


def test_flush_saves_final_session(tmp_path):
    buffer = SQLiteBuffer(tmp_path / "buffer.db")
    collector = ActivityCollector(SessionBuilder(), buffer)

    collector.observe(make_observation("Code.exe", 0))
    completed = collector.flush(START + timedelta(seconds=20))

    assert len(completed) == 1
    assert buffer.count_pending() == 1
    assert buffer.get_pending_sessions()[0]["app_name"] == "Code.exe"


def test_same_app_is_not_saved_until_session_closes(tmp_path):
    buffer = SQLiteBuffer(tmp_path / "buffer.db")
    collector = ActivityCollector(SessionBuilder(), buffer)

    collector.observe(make_observation("Code.exe", 0))
    collector.observe(make_observation("Code.exe", 5))

    assert buffer.count_pending() == 0

    collector.observe(make_observation("chrome.exe", 10))

    assert buffer.count_pending() == 1


def test_flush_without_active_session_saves_nothing(tmp_path):
    buffer = SQLiteBuffer(tmp_path / "buffer.db")
    collector = ActivityCollector(SessionBuilder(), buffer)

    assert collector.flush() == []
    assert buffer.count_pending() == 0
