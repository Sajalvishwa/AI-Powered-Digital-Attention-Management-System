
from datetime import datetime, timedelta, timezone
import uuid

import pytest

from app.session_builder import (
    ActivityObservation,
    SessionBuilder,
)


START = datetime(2026, 10, 12, 10, 0, 0, tzinfo=timezone.utc)


def observation(
    app_name="Code.exe",
    seconds=0,
    is_idle=False,
    title=None,
):
    return ActivityObservation(
        app_name=app_name,
        is_idle=is_idle,
        observed_at=START + timedelta(seconds=seconds),
        window_title=title,
    )


def test_first_observation_starts_session():
    builder = SessionBuilder()

    result = builder.observe(observation())

    assert result == []
    assert builder.has_active_session


def test_app_change_completes_previous_session():
    builder = SessionBuilder()

    builder.observe(observation("Code.exe", 0))
    result = builder.observe(observation("chrome.exe", 30))

    assert len(result) == 1
    assert result[0].app_name == "Code.exe"
    assert result[0].started_at == START
    assert result[0].ended_at == START + timedelta(seconds=30)
    assert result[0].duration_seconds == 30
    assert builder.current_observation.app_name == "chrome.exe"


def test_same_app_does_not_create_extra_sessions():
    builder = SessionBuilder()

    builder.observe(observation("Code.exe", 0))
    assert builder.observe(observation("Code.exe", 5)) == []
    assert builder.observe(observation("Code.exe", 10)) == []

    result = builder.observe(observation("chrome.exe", 15))

    assert len(result) == 1
    assert result[0].duration_seconds == 15


def test_idle_transition_closes_active_app_session():
    builder = SessionBuilder()

    builder.observe(observation("Code.exe", 0))
    result = builder.observe(
        observation("IDLE", 60, is_idle=True)
    )

    assert len(result) == 1
    assert result[0].app_name == "Code.exe"
    assert result[0].is_idle is False
    assert result[0].duration_seconds == 60


def test_idle_observation_normalizes_app_name():
    item = observation("Code.exe", 60, is_idle=True)

    assert item.app_name == "IDLE"
    assert item.is_idle is True


def test_active_transition_closes_idle_session():
    builder = SessionBuilder()

    builder.observe(observation("Code.exe", 0))
    builder.observe(observation("IDLE", 60, is_idle=True))

    result = builder.observe(observation("chrome.exe", 90))

    assert len(result) == 1
    assert result[0].app_name == "IDLE"
    assert result[0].is_idle is True
    assert result[0].duration_seconds == 30


def test_title_change_splits_session():
    builder = SessionBuilder()

    builder.observe(observation("Code.exe", 0, title="file_a.py"))
    result = builder.observe(
        observation("Code.exe", 10, title="file_b.py")
    )

    assert len(result) == 1
    assert result[0].window_title == "file_a.py"
    assert result[0].duration_seconds == 10


def test_flush_closes_current_session():
    builder = SessionBuilder()

    builder.observe(observation("Code.exe", 0))
    result = builder.flush(START + timedelta(seconds=20))

    assert len(result) == 1
    assert result[0].app_name == "Code.exe"
    assert result[0].duration_seconds == 20
    assert not builder.has_active_session


def test_flush_without_active_session_returns_empty_list():
    assert SessionBuilder().flush() == []


def test_zero_length_session_is_discarded():
    builder = SessionBuilder()

    builder.observe(observation("Code.exe", 0))
    result = builder.flush(START)

    assert result == []
    assert not builder.has_active_session


def test_observations_must_be_chronological():
    builder = SessionBuilder()

    builder.observe(observation("Code.exe", 10))

    with pytest.raises(ValueError, match="chronological"):
        builder.observe(observation("chrome.exe", 5))


def test_observation_requires_timezone():
    with pytest.raises(ValueError, match="timezone-aware"):
        ActivityObservation(
            app_name="Code.exe",
            is_idle=False,
            observed_at=datetime(2026, 10, 12, 10, 0, 0),
        )


def test_flush_rejects_naive_end_time():
    builder = SessionBuilder()
    builder.observe(observation())

    with pytest.raises(ValueError, match="timezone-aware"):
        builder.flush(datetime(2026, 10, 12, 10, 1, 0))


def test_client_ids_are_unique():
    builder = SessionBuilder()

    builder.observe(observation("Code.exe", 0))
    first = builder.observe(observation("chrome.exe", 10))[0]

    builder.observe(observation("chrome.exe", 10))
    second = builder.observe(observation("Code.exe", 20))[0]

    assert first.client_id != second.client_id
    assert isinstance(first.client_id, uuid.UUID)


def test_payload_matches_backend_fields():
    builder = SessionBuilder()

    builder.observe(observation("Code.exe", 0))
    session = builder.observe(observation("chrome.exe", 10))[0]

    payload = session.to_payload()

    assert set(payload) == {
        "client_id",
        "app_name",
        "window_title",
        "is_idle",
        "started_at",
        "ended_at",
        "focus_session_id",
    }
    assert payload["app_name"] == "Code.exe"
    assert payload["is_idle"] is False
    assert payload["focus_session_id"] is None
    assert payload["client_id"] == str(session.client_id)


def test_focus_session_id_is_attached_to_completed_session():
    builder = SessionBuilder()
    focus_id = uuid.uuid4()

    builder.set_focus_session_id(focus_id)
    builder.observe(observation("Code.exe", 0))

    result = builder.observe(observation("chrome.exe", 10))

    assert result[0].focus_session_id == focus_id
