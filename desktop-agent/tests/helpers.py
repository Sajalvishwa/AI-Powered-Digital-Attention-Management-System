"""Fakes so tests run on any computer without real windows."""
from app.tracker import ForegroundWindow


class FakeWin32:
    def __init__(self, hwnd=1, pid=100, process="App.exe", title=""):
        self.hwnd, self.pid, self.process, self.title = hwnd, pid, process, title
        self.title_reads = 0

    def foreground_hwnd(self):
        return self.hwnd

    def window_pid(self, hwnd):
        return self.pid

    def window_title(self, hwnd):
        self.title_reads += 1
        return self.title

    def process_name(self, pid):
        return self.process


class FakeTracker:
    """Returns the given windows one by one, then keeps repeating the last one."""

    def __init__(self, windows=None):
        self.windows = windows if windows is not None else [ForegroundWindow("Code.exe", None, 1)]
        self.calls = 0

    def current(self):
        index = min(self.calls, len(self.windows) - 1)
        self.calls += 1
        return self.windows[index]


class RaisingTracker:
    """Fails on the given call numbers (1-based), works otherwise."""

    def __init__(self, fail_on=(2,)):
        self.fail_on = set(fail_on)
        self.calls = 0

    def current(self):
        self.calls += 1
        if self.calls in self.fail_on:
            raise RuntimeError("boom")
        return ForegroundWindow("Code.exe", None, 1)
