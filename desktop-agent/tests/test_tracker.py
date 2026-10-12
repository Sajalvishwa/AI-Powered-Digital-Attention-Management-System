from app.tracker import ForegroundWindow, WindowTracker
from tests.helpers import FakeWin32


def test_reads_app_name_and_pid():
    api = FakeWin32(hwnd=10, pid=4242, process="Code.exe", title="main.py - secret")
    window = WindowTracker(include_title=False, api=api).current()
    assert window == ForegroundWindow(app_name="Code.exe", title=None, pid=4242)


def test_title_is_not_even_read_when_disabled():
    api = FakeWin32(title="Bank - Account 1234")
    WindowTracker(include_title=False, api=api).current()
    assert api.title_reads == 0


def test_title_is_returned_when_enabled():
    api = FakeWin32(title="  Notes  ")
    window = WindowTracker(include_title=True, api=api).current()
    assert window.title == "Notes"


def test_long_values_are_truncated_to_backend_limits():
    api = FakeWin32(process="a" * 300, title="t" * 2000)
    window = WindowTracker(include_title=True, api=api).current()
    assert len(window.app_name) == 255
    assert len(window.title) == 500


def test_no_foreground_window_gives_none():
    assert WindowTracker(api=FakeWin32(hwnd=0)).current() is None


def test_pid_zero_gives_none():
    assert WindowTracker(api=FakeWin32(pid=0)).current() is None


def test_process_that_just_closed_gives_none():
    assert WindowTracker(api=FakeWin32(process=None)).current() is None


def test_hidden_process_name_becomes_unknown():
    window = WindowTracker(api=FakeWin32(process="")).current()
    assert window.app_name == "Unknown"


def test_same_window_compares_equal():
    api = FakeWin32(pid=7, process="Chrome.exe")
    tracker = WindowTracker(api=api)
    assert tracker.current() == tracker.current()
