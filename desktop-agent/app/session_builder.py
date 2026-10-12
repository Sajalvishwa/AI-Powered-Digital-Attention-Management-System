
"""
Build continuous activity sessions from foreground app and idle-state events.

Responsibilities:
- Start a session when an observation arrives.
- Close the current session when the app or idle state changes.
- Return completed sessions for local buffering.
- Generate a unique client_id for each session.
- Keep timestamps timezone-aware and in UTC.

This module performs no database or network operations.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True)
class ActivityObservation:
    """A snapshot of the foreground app and the user's idle state."""

    app_name: str
    is_idle: bool
    observed_at: datetime
    window_title: str | None = None

    def __post_init__(self) -> None:
        if not self.app_name or not self.app_name.strip():
            raise ValueError("app_name must not be empty.")

        if self.observed_at.tzinfo is None:
            raise ValueError("observed_at must be timezone-aware.")

        if self.observed_at.utcoffset() is None:
            raise ValueError("observed_at must include a UTC offset.")

        if self.is_idle and self.app_name != "IDLE":
            # Idle intervals should have a consistent app label.
            object.__setattr__(self, "app_name", "IDLE")

        if not self.is_idle and self.app_name == "IDLE":
            raise ValueError(
                "The app name 'IDLE' is reserved for idle observations."
            )


@dataclass(frozen=True)
class ActivitySession:
    """A completed interval that can be sent to the backend."""

    client_id: uuid.UUID
    app_name: str
    window_title: str | None
    is_idle: bool
    started_at: datetime
    ended_at: datetime
    focus_session_id: uuid.UUID | None = None

    @property
    def duration_seconds(self) -> float:
        """Return the interval duration in seconds."""
        return (self.ended_at - self.started_at).total_seconds()

    def to_payload(self) -> dict:
        """Convert the session into a backend-compatible dictionary."""
        return {
            "client_id": str(self.client_id),
            "app_name": self.app_name,
            "window_title": self.window_title,
            "is_idle": self.is_idle,
            "started_at": self.started_at.isoformat(),
            "ended_at": self.ended_at.isoformat(),
            "focus_session_id": (
                str(self.focus_session_id)
                if self.focus_session_id is not None
                else None
            ),
        }


class SessionBuilder:
    """
    Convert observations into completed activity sessions.

    The first observation starts a session. A later observation closes
    the current session only when the app, title, or idle state changes.

    Call flush() during an orderly shutdown to close the current session.
    """

    def __init__(self) -> None:
        self._current: ActivityObservation | None = None
        self._focus_session_id: uuid.UUID | None = None

    @property
    def has_active_session(self) -> bool:
        """Whether an observation is currently being tracked."""
        return self._current is not None

    @property
    def current_observation(self) -> ActivityObservation | None:
        """Expose the current observation without modifying builder state."""
        return self._current

    def set_focus_session_id(
        self,
        focus_session_id: uuid.UUID | None,
    ) -> None:
        """Set the optional focus-session association for future intervals."""
        self._focus_session_id = focus_session_id

    def observe(
        self,
        observation: ActivityObservation,
    ) -> list[ActivitySession]:
        """
        Process a new observation.

        Returns:
            A list containing zero or one completed session.
        """
        if self._current is None:
            self._current = observation
            return []

        previous = self._current

        previous_time = previous.observed_at.astimezone(timezone.utc)
        current_time = observation.observed_at.astimezone(timezone.utc)

        if current_time < previous_time:
            raise ValueError("Observation timestamps must be chronological.")

        same_interval = (
            previous.app_name == observation.app_name
            and previous.is_idle == observation.is_idle
            and previous.window_title == observation.window_title
        )

        if same_interval:
            # Keep the original start time; only the latest observation
            # determines when this interval will eventually end.
            self._current = observation.__class__(
                app_name=previous.app_name,
                is_idle=previous.is_idle,
                observed_at=previous.observed_at,
                window_title=previous.window_title,
            )
            return []

        completed = self._build_session(
            start=previous,
            end_time=current_time,
        )

        # The new interval begins at the transition timestamp.
        self._current = ActivityObservation(
            app_name=observation.app_name,
            is_idle=observation.is_idle,
            observed_at=current_time,
            window_title=observation.window_title,
        )

        return [completed] if completed is not None else []

    def flush(
        self,
        ended_at: datetime | None = None,
    ) -> list[ActivitySession]:
        """
        Close the current session, typically when the agent shuts down.

        If ended_at is omitted, the current UTC time is used.
        Zero-length sessions are discarded.
        """
        if self._current is None:
            return []

        end_time = ended_at or datetime.now(timezone.utc)

        if end_time.tzinfo is None or end_time.utcoffset() is None:
            raise ValueError("ended_at must be timezone-aware.")

        end_time = end_time.astimezone(timezone.utc)
        start_time = self._current.observed_at.astimezone(timezone.utc)

        if end_time < start_time:
            raise ValueError("ended_at cannot precede the session start.")

        completed = self._build_session(
            start=self._current,
            end_time=end_time,
        )

        self._current = None

        return [completed] if completed is not None else []

    def _build_session(
        self,
        start: ActivityObservation,
        end_time: datetime,
    ) -> ActivitySession | None:
        """Build a session from a start observation and an end timestamp."""
        started_at = start.observed_at.astimezone(timezone.utc)

        if end_time <= started_at:
            return None

        return ActivitySession(
            client_id=uuid.uuid4(),
            app_name=start.app_name,
            window_title=start.window_title,
            is_idle=start.is_idle,
            started_at=started_at,
            ended_at=end_time,
            focus_session_id=self._focus_session_id,
        )
