"""Foreground window tracker (T3.2).

Reads ONLY: the app name of the active window (e.g. "Code.exe"), its process id and,
if enabled, the window title. Nothing else: no keystrokes, clipboard or screenshots.

Titles can contain private data (bank pages, mail subjects). They are not even read
unless include_title=True, and they must never be written to logs.

Known limitation: Windows "store" apps (Settings, Calculator, ...) are hosted by
ApplicationFrameHost.exe, so they show up under that name.
"""
import argparse
import time
from dataclasses import dataclass
from typing import Protocol

MAX_APP_NAME = 255  # same limits as the backend
MAX_TITLE = 500


class TrackerUnavailable(RuntimeError):
    """The tracker cannot run here (not Windows, or pywin32/psutil missing)."""


@dataclass(frozen=True)
class ForegroundWindow:
    app_name: str
    title: str | None
    pid: int


class Tracker(Protocol):
    def current(self) -> ForegroundWindow | None: ...


class Win32Api(Protocol):
    """The few OS calls we need. Faked in tests so they run on any computer."""

    def foreground_hwnd(self) -> int: ...
    def window_pid(self, hwnd: int) -> int: ...
    def window_title(self, hwnd: int) -> str: ...
    def process_name(self, pid: int) -> str | None: ...  # None = process is gone


class RealWin32:
    def __init__(self) -> None:
        try:
            import psutil
            import pywintypes
            import win32gui
            import win32process
        except ImportError as exc:
            raise TrackerUnavailable(
                "Window tracking needs Windows with pywin32 and psutil "
                "(run: pip install -r requirements.txt)"
            ) from exc
        self._psutil = psutil
        self._win_error = pywintypes.error
        self._gui = win32gui
        self._proc = win32process

    def foreground_hwnd(self) -> int:
        return int(self._gui.GetForegroundWindow() or 0)

    def window_pid(self, hwnd: int) -> int:
        try:
            _thread_id, pid = self._proc.GetWindowThreadProcessId(hwnd)
        except self._win_error:
            return 0
        return int(pid)

    def window_title(self, hwnd: int) -> str:
        try:
            return self._gui.GetWindowText(hwnd) or ""
        except self._win_error:
            return ""

    def process_name(self, pid: int) -> str | None:
        try:
            return self._psutil.Process(pid).name()
        except self._psutil.AccessDenied:
            return ""  # e.g. an elevated/system process: app exists, name hidden
        except self._psutil.NoSuchProcess:
            return None


class WindowTracker:
    def __init__(self, include_title: bool = False, api: Win32Api | None = None) -> None:
        self.include_title = include_title
        self._api: Win32Api = api if api is not None else RealWin32()

    def current(self) -> ForegroundWindow | None:
        """The active window, or None (no window, e.g. lock screen, or it just closed)."""
        hwnd = self._api.foreground_hwnd()
        if not hwnd:
            return None
        pid = self._api.window_pid(hwnd)
        if not pid:
            return None
        name = self._api.process_name(pid)
        if name is None:
            return None
        title = None
        if self.include_title:
            title = self._api.window_title(hwnd).strip()[:MAX_TITLE]
        return ForegroundWindow(
            app_name=(name.strip() or "Unknown")[:MAX_APP_NAME], title=title, pid=pid
        )


def _demo(seconds: float, titles: bool) -> None:
    """Manual check: python -m app.tracker --seconds 20   (switch between windows)"""
    tracker = WindowTracker(include_title=titles)
    print(f"Watching the active window for {seconds:g}s. Switch between a few apps now...")
    end = time.monotonic() + seconds
    last: object = object()
    while time.monotonic() < end:
        window = tracker.current()
        if window != last:
            if window is None:
                print("(no foreground window)")
            elif window.title:
                print(f"{window.app_name}  pid={window.pid}  title={window.title}")
            else:
                print(f"{window.app_name}  pid={window.pid}")
            last = window
        time.sleep(0.3)
    print("Done.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Print the active window for a few seconds")
    parser.add_argument("--seconds", type=float, default=15)
    parser.add_argument("--titles", action="store_true", help="also show window titles (console only)")
    args = parser.parse_args()
    try:
        _demo(args.seconds, args.titles)
    except TrackerUnavailable as exc:
        raise SystemExit(f"Error: {exc}")
