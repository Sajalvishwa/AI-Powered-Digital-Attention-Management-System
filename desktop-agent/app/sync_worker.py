"""Upload buffered activity sessions to the backend safely."""

import logging
from dataclasses import dataclass
from typing import Any

from app.api_client import ApiClient
from app.logging_setup import LOGGER_NAME
from app.offline_buffer import SQLiteBuffer

log = logging.getLogger(LOGGER_NAME)

MAX_BATCH_SIZE = 500


@dataclass(frozen=True)
class SyncResult:
    """Summary of a single synchronization attempt."""

    attempted: int = 0
    synced: int = 0
    pending: int = 0
    success: bool = True
    reason: str = ""


class SyncWorker:
    """Synchronize SQLite-buffered sessions with the backend."""

    def __init__(
        self,
        buffer: SQLiteBuffer,
        api_client: ApiClient,
        batch_size: int = MAX_BATCH_SIZE,
    ) -> None:
        if isinstance(batch_size, bool) or not isinstance(batch_size, int):
            raise ValueError("batch_size must be an integer.")

        if not 1 <= batch_size <= MAX_BATCH_SIZE:
            raise ValueError(
                f"batch_size must be between 1 and {MAX_BATCH_SIZE}."
            )

        self.buffer = buffer
        self.api_client = api_client
        self.batch_size = batch_size

    def sync_once(self) -> SyncResult:
        """Attempt to upload one batch without losing offline data."""
        try:
            if not self.api_client.is_logged_in():
                return self._failure("login_required")

            sessions = self.buffer.get_pending_sessions(
                limit=self.batch_size
            )

            if not sessions:
                return SyncResult(
                    pending=self.buffer.count_pending()
                )

            client_ids = [
                session["client_id"]
                for session in sessions
            ]

            response = self.api_client.upload_batch(sessions)

            if not self._valid_response(response, len(sessions)):
                log.warning(
                    "Sync response did not confirm the complete batch."
                )
                return self._failure("invalid_response")

            # Mark records only after the server confirms processing.
            marked = self.buffer.mark_synced(client_ids)

            log.info(
                "Sync successful: attempted=%d, marked=%d, "
                "inserted=%d, duplicates=%d, skipped=%d",
                len(sessions),
                marked,
                response["inserted"],
                response["duplicates"],
                response["skipped"],
            )

            return SyncResult(
                attempted=len(sessions),
                synced=marked,
                pending=self.buffer.count_pending(),
            )

        except Exception as exc:
            # Keep local records pending so a later attempt can retry.
            log.warning(
                "Sync attempt failed (%s); local sessions retained.",
                type(exc).__name__,
            )
            return self._failure(type(exc).__name__)

    @staticmethod
    def _valid_response(
        response: Any,
        expected_count: int,
    ) -> bool:
        """Validate the backend's batch acknowledgement."""
        if not isinstance(response, dict):
            return False

        fields = ("received", "inserted", "duplicates", "skipped")

        for field in fields:
            value = response.get(field)

            if (
                isinstance(value, bool)
                or not isinstance(value, int)
                or value < 0
            ):
                return False

        return (
            response["received"] == expected_count
            and (
                response["inserted"]
                + response["duplicates"]
                + response["skipped"]
            ) == expected_count
        )

    def _failure(self, reason: str) -> SyncResult:
        """Return a failure result without modifying pending records."""
        try:
            pending = self.buffer.count_pending()
        except Exception:
            pending = -1

        return SyncResult(
            pending=pending,
            success=False,
            reason=reason,
        )