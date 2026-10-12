import uuid

import pytest
from pydantic import ValidationError

from app.schemas.activity import ActivityBatchIn, ActivitySessionIn
from app.schemas.focus import FocusUpdate


def make(**over):
    base = dict(
        client_id=str(uuid.uuid4()),
        app_name="Code.exe",
        started_at="2026-10-11T10:00:00Z",
        ended_at="2026-10-11T10:30:00Z",
    )
    base.update(over)
    return ActivitySessionIn(**base)


def test_valid_session():
    assert make().is_idle is False


def test_end_before_start_rejected():
    with pytest.raises(ValidationError):
        make(started_at="2026-10-11T11:00:00Z", ended_at="2026-10-11T10:00:00Z")


def test_naive_timestamp_rejected():
    with pytest.raises(ValidationError):
        make(started_at="2026-10-11T10:00:00", ended_at="2026-10-11T10:30:00")


def test_far_future_rejected():
    with pytest.raises(ValidationError):
        make(started_at="2099-01-01T10:00:00Z", ended_at="2099-01-01T11:00:00Z")


def test_batch_limits():
    with pytest.raises(ValidationError):
        ActivityBatchIn(sessions=[])
    with pytest.raises(ValidationError):
        ActivityBatchIn(sessions=[make() for _ in range(501)])


def test_focus_action_validated():
    assert FocusUpdate(action="stop", switch_count=3).switch_count == 3
    with pytest.raises(ValidationError):
        FocusUpdate(action="explode")
