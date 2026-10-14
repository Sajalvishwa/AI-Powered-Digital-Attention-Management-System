
"""Main loop for desktop activity collection and backend synchronization."""

import logging
import threading
import time
from datetime import datetime, timezone
from typing import Callable

from app.activity_collector import ActivityCollector
from app.api_client import ApiClient
from app.idle import get_windows_idle_seconds, is_idle_for_threshold
from app.logging_setup import LOGGER_NAME
from app.offline_buffer import SQLiteBuffer
from app.session_builder import ActivityObservation, SessionBuilder
from app.settings import AgentSettings
from app.sync_worker import SyncWorker
from app.tracker import ForegroundWindow, Tracker

log = logging.getLogger(LOGGER_NAME)


class Agent:
    """Collect desktop activity and periodically sync it with the backend."""

    def __init__(
        self,
        settings: AgentSettings,
        tracker: Tracker,
        idle_provider: Callable[[], float] | None = None,
        clock: Callable[[], datetime] | None = None,
        collector: ActivityCollector | None = None,
        api_client: ApiClient | None = None,
    ) -> None:
        self.settings = settings
        self.tracker = tracker

        # Normalize ignored application names for case-insensitive matching.
        self._ignored_apps = {
            app.casefold().strip()
            for app in settings.ignored_apps
        }

        self.ticks = 0
        self.last_window: ForegroundWindow | None = None
        self._stop = threading.Event()

        # Injectable dependencies keep automated tests independent
        # of the real Windows API and wall-clock timing.
        self.idle_provider = idle_provider or get_windows_idle_seconds
        self.clock = clock or (lambda: datetime.now(timezone.utc))

        # Initialize local activity collection and offline storage.
        if collector is None:
            collector = ActivityCollector(
                builder=SessionBuilder(),
                buffer=SQLiteBuffer(settings.buffer_db),
            )

        self.collector = collector

        # SyncWorker is optional so existing tracking-only tests and
        # offline usage can work without an API client.
        self.sync_worker = (
            SyncWorker(
                buffer=self.collector.buffer,
                api_client=api_client,
            )
            if api_client is not None
            else None
        )

        self._last_sync_at = time.monotonic()
        self._idle_warning_logged = False

    def stop(self) -> None:
        """Ask the loop to finish safely."""
        self._stop.set()

    def run(self, max_ticks: int | None = None) -> int:
        """Run the activity collection loop until stopped."""
        log.info(
            "Agent started (api=%s, poll=%ss, sync=%ss)",
            self.settings.api_base_url,
            self.settings.poll_interval_sec,
            self.settings.sync_interval_sec,
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
            # Save the currently open activity session first.
            try:
                completed = self.collector.flush(ended_at=self.clock())

                if completed:
                    log.info(
                        "Saved %d final activity session(s)",
                        len(completed),
                    )

            except Exception:
                log.exception("Could not flush the final activity session")

            # Try to upload buffered activity before exiting.
            # If the backend is unavailable, local data remains buffered.
            try:
                self._maybe_sync(force=True)
            except Exception:
                log.exception("Final activity synchronization failed")

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

        observed_at = self.clock()

        # Never collect or buffer activity from an ignored application.
        # Flush the previous allowed session when entering an ignored app.
        if not is_idle and app_name.casefold() in self._ignored_apps:
            completed = self.collector.flush(ended_at=observed_at)

            if completed:
                log.debug(
                    "Closed %d session(s) before entering an ignored app",
                    len(completed),
                )

            self._maybe_sync()
            return

        # Window titles are included only when explicitly enabled.
        observation = ActivityObservation(
            app_name=app_name,
            is_idle=is_idle,
            observed_at=observed_at,
            window_title=(
                window.title
                if self.settings.store_window_titles
                and window is not None
                else None
            ),
        )

        completed = self.collector.observe(observation)

        log.debug(
            "tick %d: foreground app = %s; idle = %s; completed = %d",
            self.ticks + 1,
            app_name,
            is_idle,
            len(completed),
        )

        # Periodically upload buffered activity to the backend.
        self._maybe_sync()

    def _maybe_sync(self, force: bool = False) -> None:
        """Sync buffered activity when the interval expires or on shutdown."""
        if self.sync_worker is None:
            return

        now = time.monotonic()

        if not force:
            elapsed = now - self._last_sync_at

            if elapsed < self.settings.sync_interval_sec:
                return

        # Record the attempt time before calling the backend so failures
        # do not cause an upload attempt on every polling tick.
        self._last_sync_at = now

        try:
            result = self.sync_worker.sync_once()

            if not result.success:
                log.warning(
                    "Activity sync unsuccessful; %d session(s) remain pending",
                    result.pending,
                )

        except Exception:
            # A sync failure must never stop local activity collection.
            log.exception("Activity synchronization failed")
