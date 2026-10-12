import threading

from app.agent import Agent
from app.settings import AgentSettings
from app.tracker import ForegroundWindow
from tests.helpers import FakeTracker, RaisingTracker


def make_agent(tmp_path, tracker=None, poll=0.1) -> Agent:
    return Agent(AgentSettings(data_dir=tmp_path, poll_interval_sec=poll), tracker or FakeTracker())


def test_runs_requested_number_of_ticks(tmp_path):
    agent = make_agent(tmp_path)
    assert agent.run(max_ticks=3) == 0
    assert agent.ticks == 3


def test_looks_at_the_active_window_every_tick(tmp_path):
    chrome = ForegroundWindow("Chrome.exe", None, 2)
    tracker = FakeTracker([ForegroundWindow("Code.exe", None, 1), chrome])
    agent = make_agent(tmp_path, tracker)
    agent.run(max_ticks=2)
    assert tracker.calls == 2
    assert agent.last_window == chrome


def test_stop_ends_the_loop_quickly(tmp_path):
    agent = make_agent(tmp_path, poll=30)  # would sleep 30s without stop()
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
