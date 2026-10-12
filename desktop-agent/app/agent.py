"""The agent's main loop. Later tasks plug more work into _tick()."""
import logging
import threading

from app.logging_setup import LOGGER_NAME
from app.settings import AgentSettings
from app.tracker import ForegroundWindow, Tracker

log = logging.getLogger(LOGGER_NAME)


class Agent:
    def __init__(self, settings: AgentSettings, tracker: Tracker) -> None:
        self.settings = settings
        self.tracker = tracker
        self.ticks = 0
        self.last_window: ForegroundWindow | None = None
        self._stop = threading.Event()

    def stop(self) -> None:
        """Ask the loop to finish (safe to call from a signal handler or another thread)."""
        self._stop.set()

    def run(self, max_ticks: int | None = None) -> int:
        log.info(
            "Agent started (api=%s, poll=%ss)",
            self.settings.api_base_url,
            self.settings.poll_interval_sec,
        )
        try:
            while not self._stop.is_set():
                try:
                    self._tick()
                except Exception:  # one bad tick must never kill the agent
                    log.exception("Tick failed; continuing")
                self.ticks += 1
                if max_ticks is not None and self.ticks >= max_ticks:
                    break
                self._stop.wait(self.settings.poll_interval_sec)
        finally:
            log.info("Agent stopped after %d ticks", self.ticks)
        return 0

    def _tick(self) -> None:
        """T3.2: look at the active window. T3.3 adds idle time, T3.4 builds sessions."""
        window = self.tracker.current()
        self.last_window = window
        # app name only - never log the window title
        log.debug("tick %d: foreground app = %s", self.ticks + 1, window.app_name if window else "none")
