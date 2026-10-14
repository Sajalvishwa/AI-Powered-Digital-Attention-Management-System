
import threading
from datetime import datetime, timedelta, timezone

from app.agent import Agent
from app.settings import AgentSettings
from app.tracker import ForegroundWindow
from tests.helpers import FakeTracker, RaisingTracker


class FakeSyncResult:
    """Minimal sync result for Agent integration tests."""

    def __init__(self, success=True, pending=0):
        self.success = success
        self.pending = pending


class FakeSyncWorker:
    """Record sync attempts without contacting a real backend."""

    def __init__(self, results=None):
        self.calls = 0
        self.results = list(results or [])

    def sync_once(self):
        self.calls += 1

        if self.results:
            return self.results.pop(0)

        return FakeSyncResult()


def make_agent(tmp_path, tracker=None, poll=0.1) -> Agent:
    return Agent(
        AgentSettings(
            data_dir=tmp_path,
            poll_interval_sec=poll,
        ),
        tracker or FakeTracker(),
    )


def test_runs_requested_number_of_ticks(tmp_path):
    agent = make_agent(tmp_path)

    assert agent.run(max_ticks=3) == 0
    assert agent.ticks == 3


def test_looks_at_the_active_window_every_tick(tmp_path):
    chrome = ForegroundWindow("Chrome.exe", None, 2)

    tracker = FakeTracker(
        [
            ForegroundWindow("Code.exe", None, 1),
            chrome,
        ]
    )

    agent = make_agent(tmp_path, tracker)

    agent.run(max_ticks=2)

    assert tracker.calls == 2
    assert agent.last_window == chrome


def test_stop_ends_the_loop_quickly(tmp_path):
    agent = make_agent(tmp_path, poll=30)

    thread = threading.Thread(target=agent.run)
    thread.start()

    agent.stop()
    thread.join(timeout=3)

    assert not thread.is_alive()


def test_a_failing_tracker_call_does_not_kill_the_agent(tmp_path):
    tracker = RaisingTracker(fail_on=(2,))
    agent = make_agent(tmp_path, tracker)

    assert agent.run(max_ticks=4) == 0
    assert agent.ticks == 4
    assert tracker.calls == 4


def test_periodic_sync_runs_when_interval_expires(tmp_path, monkeypatch):
    agent = make_agent(tmp_path)

    worker = FakeSyncWorker()
    agent.sync_worker = worker

    # Simulate that the configured sync interval has elapsed.
    monkeypatch.setattr(
        "app.agent.time.monotonic",
        lambda: (
            agent._last_sync_at
            + agent.settings.sync_interval_sec
            + 1
        ),
    )

    agent._maybe_sync()

    assert worker.calls == 1


def test_shutdown_attempts_final_sync(tmp_path):
    agent = make_agent(tmp_path)

    worker = FakeSyncWorker()
    agent.sync_worker = worker

    assert agent.run(max_ticks=1) == 0

    # Shutdown forces one final synchronization attempt.
    assert worker.calls == 1


def test_sync_failure_does_not_stop_activity_collection(tmp_path):
    agent = make_agent(tmp_path)

    worker = FakeSyncWorker(
        results=[
            FakeSyncResult(success=False, pending=2),
        ]
    )
    agent.sync_worker = worker

    # The failure must not terminate the collection loop.
    agent._maybe_sync(force=True)

    assert worker.calls == 1
    assert agent.ticks == 0


# T3.8: Ignore-list and window-title privacy tests


def test_ignored_app_is_never_saved_and_allowed_sessions_are_split(
    tmp_path,
):
    start = datetime(2026, 10, 12, 10, 0, tzinfo=timezone.utc)

    timestamps = iter(
        start + timedelta(seconds=seconds)
        for seconds in (0, 10, 20, 30)
    )

    tracker = FakeTracker(
        [
            ForegroundWindow("Code.exe", None, 1),
            ForegroundWindow("Chrome.EXE", None, 2),
            ForegroundWindow("Code.exe", None, 1),
        ]
    )

    settings = AgentSettings(
        data_dir=tmp_path,
        poll_interval_sec=0.1,
        ignored_apps=("chrome.exe",),
    )

    agent = Agent(
        settings,
        tracker,
        idle_provider=lambda: 0,
        clock=lambda: next(timestamps),
    )

    agent.run(max_ticks=3)

    pending = agent.collector.buffer.get_pending_sessions()

    assert len(pending) == 2
    assert all(row["app_name"] == "Code.exe" for row in pending)
    assert all(row["window_title"] is None for row in pending)

    durations = [
        (
            datetime.fromisoformat(row["ended_at"])
            - datetime.fromisoformat(row["started_at"])
        ).total_seconds()
        for row in pending
    ]

    assert durations == [10, 10]


def test_window_title_is_not_stored_when_setting_is_disabled(
    tmp_path,
):
    start = datetime(2026, 10, 12, 10, 0, tzinfo=timezone.utc)

    tracker = FakeTracker(
        [
            ForegroundWindow(
                "Code.exe",
                "private document title",
                1,
            )
        ]
    )

    agent = Agent(
        AgentSettings(data_dir=tmp_path),
        tracker,
        idle_provider=lambda: 0,
        clock=lambda: start,
    )

    agent._tick()
    agent.collector.flush(ended_at=start + timedelta(seconds=5))

    pending = agent.collector.buffer.get_pending_sessions()

    assert len(pending) == 1
    assert pending[0]["window_title"] is None
