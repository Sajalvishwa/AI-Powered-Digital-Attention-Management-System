"""Main loop for desktop activity collection and backend synchronization."""

import logging
import threading
import time
import uuid
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

FOCUS_CHECK_INTERVAL_SEC = 10
SETTINGS_REFRESH_SEC = 300  # how often web-app settings are fetched
SETTINGS_RETRY_SEC = 60  # retry delay after a failed fetch


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

        # The desktop app (Electron) asks for a clean shutdown by creating
        # this file. Force-killing a Windows process would skip the final
        # flush and sync, so a file is used instead of a signal.
        self._stop_file = settings.data_dir / "stop.flag"

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
        self._api_client = api_client
        self.sync_worker = (
            SyncWorker(
                buffer=self.collector.buffer,
                api_client=api_client,
            )
            if api_client is not None
            else None
        )

        self._last_sync_at = time.monotonic()
        self._last_focus_check = float("-inf")
        self._current_focus_id: uuid.UUID | None = None

        # Settings saved in the web app. Local config.toml values are the
        # starting point until the first successful fetch. Window titles are OFF
        # unless the user switches them on (config.toml or the web app).
        self._local_ignored = set(self._ignored_apps)
        self._idle_threshold_sec = settings.idle_threshold_sec
        self._store_titles = settings.store_window_titles
        self._last_settings_check = float("-inf")
        self._idle_warning_logged = False

    def stop(self) -> None:
        """Ask the loop to finish safely."""
        self._stop.set()

    def _stop_requested(self) -> bool:
        """True when the desktop app asked for a clean shutdown."""
        try:
            if self._stop_file.exists():
                self._stop_file.unlink()
                return True
        except OSError:
            pass
        return False

    def run(self, max_ticks: int | None = None) -> int:
        """Run the activity collection loop until stopped."""
        log.info(
            "Agent started (api=%s, poll=%ss, sync=%ss)",
            self.settings.api_base_url,
            self.settings.poll_interval_sec,
            self.settings.sync_interval_sec,
        )

        # Ignore a stale stop request left over from an earlier run.
        try:
            self._stop_file.unlink()
        except OSError:
            pass

        try:
            while not self._stop.is_set():
                if self._stop_requested():
                    log.info("Stop requested by the desktop app")
                    break

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

    def _refresh_focus_link(self) -> None:
        """Tag new activity with the running focus session (checked every 10s).

        Without this, activity sessions are uploaded with focus_session_id = null
        and the dashboard's focus time stays at zero.
        """
        if self._api_client is None:
            return

        now = time.monotonic()
        if now - self._last_focus_check < FOCUS_CHECK_INTERVAL_SEC:
            return
        self._last_focus_check = now

        try:
            if not self._api_client.is_logged_in():
                return

            active = self._api_client.get_active_focus()
            focus_id = (
                uuid.UUID(active["id"])
                if active.get("id") and active.get("status") == "running"
                else None
            )

            if focus_id == self._current_focus_id:
                return

            builder = getattr(self.collector, "builder", None) or getattr(
                self.collector, "_builder", None
            )
            if builder is None:
                return

            builder.set_focus_session_id(focus_id)
            self._current_focus_id = focus_id
            log.info(
                "Focus session link changed: %s",
                focus_id if focus_id else "none",
            )
        except Exception:
            # Focus linking is optional; never break activity tracking.
            log.debug("Focus link refresh failed", exc_info=True)

    def _refresh_remote_settings(self) -> None:
        """Apply the settings saved in the web app (checked every 5 minutes).

        * ignored apps: config.toml list + the list saved in the web app
        * window titles: the web-app switch decides (default OFF). The tracker is
          told too, so titles are not even read from Windows while it is OFF
        * idle threshold: taken from the web app
        """
        if self._api_client is None:
            return

        now = time.monotonic()
        if now - self._last_settings_check < SETTINGS_REFRESH_SEC:
            return

        # Failures (offline, not logged in yet) retry after a short delay.
        self._last_settings_check = now - (SETTINGS_REFRESH_SEC - SETTINGS_RETRY_SEC)

        try:
            if not self._api_client.is_logged_in():
                return
            remote = self._api_client.get_settings()
        except Exception:
            log.debug("Could not fetch settings from the server", exc_info=True)
            return

        self._last_settings_check = now  # success: wait the full interval

        idle = remote.get("idle_threshold_sec")
        if isinstance(idle, int) and not isinstance(idle, bool) and 30 <= idle <= 900:
            self._idle_threshold_sec = idle

        titles = remote.get("store_window_titles")
        if isinstance(titles, bool):
            self._store_titles = titles
            # WindowTracker reads this flag on every call, so no restart is needed.
            if hasattr(self.tracker, "include_title"):
                self.tracker.include_title = titles

        apps = remote.get("ignored_apps")
        if isinstance(apps, list):
            self._ignored_apps = self._local_ignored | {
                app.casefold().strip()
                for app in apps
                if isinstance(app, str) and app.strip()
            }

        log.info(
            "Applied web-app settings: idle=%ss, titles=%s, ignored apps=%d",
            self._idle_threshold_sec,
            self._store_titles,
            len(self._ignored_apps),
        )

    def _tick(self) -> None:
        """Collect one foreground-app and idle-state observation."""
        self._refresh_focus_link()
        self._refresh_remote_settings()

        window = self.tracker.current()
        self.last_window = window

        try:
            idle_seconds = self.idle_provider()

            is_idle = is_idle_for_threshold(
                idle_seconds,
                self._idle_threshold_sec,
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
                if self._store_titles
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