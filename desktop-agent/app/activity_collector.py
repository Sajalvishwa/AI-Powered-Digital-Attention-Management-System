
"""Connect session building to the local SQLite buffer."""

from datetime import datetime

from app.offline_buffer import SQLiteBuffer
from app.session_builder import ActivityObservation, ActivitySession, SessionBuilder


class ActivityCollector:
    """Build activity sessions and persist completed sessions locally."""

    def __init__(
        self,
        builder: SessionBuilder,
        buffer: SQLiteBuffer,
    ) -> None:
        self.builder = builder
        self.buffer = buffer

    def observe(
        self,
        observation: ActivityObservation,
    ) -> list[ActivitySession]:
        """Process an observation and save any completed sessions."""
        completed = self.builder.observe(observation)

        for session in completed:
            self.buffer.save_session(session)

        return completed

    def flush(
        self,
        ended_at: datetime | None = None,
    ) -> list[ActivitySession]:
        """Close and persist the current session during shutdown."""
        completed = self.builder.flush(ended_at=ended_at)

        for session in completed:
            self.buffer.save_session(session)

        return completed
