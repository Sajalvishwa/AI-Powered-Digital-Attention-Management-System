
"""Main loop for desktop activity collection."""

import logging
import threading
from datetime import datetime, timezone
from typing import Callable

from app.activity_collector import ActivityCollector
from app.idle import get_windows_idle_seconds, is_idle_for_threshold
from app.logging_setup import LOGGER_NAME
from app.offline_buffer import SQLiteBuffer
from app.session_builder import ActivityObservation, SessionBuilder
from app.settings import AgentSettings
from app.tracker import ForegroundWindow, Tracker

log = logging.getLogger(LOGGER_NAME)


class Agent:
    def __init__(
        self,
        settings: AgentSettings,
        tracker: Tracker,
        idle_provider: Callable[[], float] | None = None,
        clock: Callable[[], datetime] | None = None,
        collector: ActivityCollector | None = None,
    ) -> None:
        self.settings = settings
        self.tracker = tracker
        self.ticks = 0
        self.last_window: ForegroundWindow | None = None
        self._stop = threading.Event()

        # Injectable dependencies keep automated tests independent
        # of the real Windows API and wall-clock timing.
        self.idle_provider = idle_provider or (lambda: 0.0)
        self.clock = clock or (lambda: datetime.now(timezone.utc))

        if collector is None:
            collector = ActivityCollector(
                builder=SessionBuilder(),
                buffer=SQLiteBuffer(settings.buffer_db),
            )
        self.collector = collector

        self._idle_warning_logged = False

    def stop(self) -> None:
        """Ask the loop to finish safely."""
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
                except Exception:
                    # A single failed tick must not terminate the agent.
                    log.exception("Tick failed; continuing")

                self.ticks += 1

                if max_ticks is not None and self.ticks >= max_ticks:
                    break

                self._stop.wait(self.settings.poll_interval_sec)
        finally:
            try:
                completed = self.collector.flush(ended_at=self.clock())
                if completed:
                    log.info(
                        "Saved %d final activity session(s)",
                        len(completed),
                    )
            except Exception:
                log.exception("Could not flush the final activity session")

            log.info("Agent stopped after %d ticks", self.ticks)

        return 0

    def _tick(self) -> None:
        """Collect one foreground-app and idle-state observation."""
        window = self.tracker.current()
        self.last_window = window

        try:
            idle_seconds = self.idle_provider()
            is_idle = is_idle_for_threshold(
                idle_seconds,
                self.settings.idle_threshold_sec,
            )
            self._idle_warning_logged = False
        except Exception:
            # Do not let a Windows idle API failure stop app tracking.
            is_idle = False
            if not self._idle_warning_logged:
                log.warning(
                    "Idle detection failed; treating this observation as active",
                    exc_info=True,
                )
                self._idle_warning_logged = True

        if is_idle:
            app_name = "IDLE"
        elif window is None:
            # The tracker may not find a foreground window.
            app_name = "Unknown"
        else:
            app_name = window.app_name

        observation = ActivityObservation(
            app_name=app_name,
            is_idle=is_idle,
            observed_at=self.clock(),
            # Privacy default: window titles are not collected.
            window_title=None,
        )

        completed = self.collector.observe(observation)

        log.debug(
            "tick %d: foreground app = %s; idle = %s; completed = %d",
            self.ticks + 1,
            app_name,
            is_idle,
            len(completed),
        )
