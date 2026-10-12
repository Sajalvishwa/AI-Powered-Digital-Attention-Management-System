"""SQLite-backed offline storage for activity sessions."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping
from uuid import UUID


class SQLiteBuffer:
    """Persist activity sessions until they are synchronized."""

    def __init__(self, db_path: Path | str) -> None:
        self.db_path = Path(db_path)

        # Create the parent directory if it does not exist.
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        """Create a connection with safe transaction defaults."""
        connection = sqlite3.connect(
            str(self.db_path),
            timeout=10.0,
        )
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA busy_timeout = 10000")
        return connection

    def _initialize(self) -> None:
        """Create the offline buffer table if necessary."""
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS pending_sessions (
                    client_id TEXT PRIMARY KEY,
                    app_name TEXT NOT NULL,
                    window_title TEXT,
                    is_idle INTEGER NOT NULL CHECK (is_idle IN (0, 1)),
                    started_at TEXT NOT NULL,
                    ended_at TEXT NOT NULL,
                    focus_session_id TEXT,
                    created_at TEXT NOT NULL,
                    synced_at TEXT,
                    CHECK (ended_at >= started_at)
                )
                """
            )

            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS
                idx_pending_sessions_unsynced
                ON pending_sessions (created_at)
                WHERE synced_at IS NULL
                """
            )

    @staticmethod
    def _normalize_session(
        session: Any,
    ) -> dict[str, Any]:
        """Convert a session object or payload dictionary into storage data."""
        if hasattr(session, "to_payload"):
            payload = session.to_payload()
        elif isinstance(session, Mapping):
            payload = dict(session)
        else:
            raise TypeError(
                "session must be a payload dictionary or expose to_payload()."
            )

        required = {
            "client_id",
            "app_name",
            "window_title",
            "is_idle",
            "started_at",
            "ended_at",
            "focus_session_id",
        }

        missing = required.difference(payload)
        if missing:
            raise ValueError(
                f"Missing session fields: {', '.join(sorted(missing))}"
            )

        try:
            client_id = str(UUID(str(payload["client_id"])))
        except (ValueError, TypeError, AttributeError) as exc:
            raise ValueError("client_id must be a valid UUID.") from exc

        app_name = payload["app_name"]

        if not isinstance(app_name, str) or not app_name.strip():
            raise ValueError("app_name must not be empty.")

        if len(app_name) > 255:
            raise ValueError("app_name cannot exceed 255 characters.")

        title = payload["window_title"]
        if title is not None and not isinstance(title, str):
            raise ValueError("window_title must be a string or None.")

        if title is not None and len(title) > 1000:
            raise ValueError("window_title cannot exceed 1000 characters.")

        if not isinstance(payload["is_idle"], bool):
            raise ValueError("is_idle must be a boolean.")

        def normalize_timestamp(value: Any, field: str) -> datetime:
            if isinstance(value, str):
                try:
                    value = datetime.fromisoformat(value)
                except ValueError as exc:
                    raise ValueError(
                        f"{field} must be a valid ISO timestamp."
                    ) from exc

            if not isinstance(value, datetime):
                raise ValueError(f"{field} must be a datetime or ISO string.")

            if value.tzinfo is None or value.utcoffset() is None:
                raise ValueError(f"{field} must be timezone-aware.")

            return value.astimezone(timezone.utc)

        started_at = normalize_timestamp(
            payload["started_at"], "started_at"
        )
        ended_at = normalize_timestamp(
            payload["ended_at"], "ended_at"
        )

        if ended_at < started_at:
            raise ValueError("ended_at cannot precede started_at.")

        focus_id = payload["focus_session_id"]

        if focus_id is not None:
            try:
                focus_id = str(UUID(str(focus_id)))
            except (ValueError, TypeError, AttributeError) as exc:
                raise ValueError(
                    "focus_session_id must be a valid UUID or None."
                ) from exc

        return {
            "client_id": client_id,
            "app_name": app_name.strip(),
            "window_title": title,
            "is_idle": payload["is_idle"],
            "started_at": started_at.isoformat(),
            "ended_at": ended_at.isoformat(),
            "focus_session_id": focus_id,
        }

    def save_session(self, session: Any) -> bool:
        """
        Save a completed session.

        Returns True when inserted.
        Returns False when the client_id already exists.
        """
        data = self._normalize_session(session)

        with self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO pending_sessions (
                    client_id,
                    app_name,
                    window_title,
                    is_idle,
                    started_at,
                    ended_at,
                    focus_session_id,
                    created_at,
                    synced_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, NULL)
                ON CONFLICT(client_id) DO NOTHING
                """,
                (
                    data["client_id"],
                    data["app_name"],
                    data["window_title"],
                    int(data["is_idle"]),
                    data["started_at"],
                    data["ended_at"],
                    data["focus_session_id"],
                    datetime.now(timezone.utc).isoformat(),
                ),
            )

            return cursor.rowcount == 1

    def get_pending_sessions(
        self,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Return unsynchronized sessions in insertion order."""
        if isinstance(limit, bool) or not isinstance(limit, int) or limit < 1:
            raise ValueError("limit must be a positive integer.")

        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT
                    client_id,
                    app_name,
                    window_title,
                    is_idle,
                    started_at,
                    ended_at,
                    focus_session_id
                FROM pending_sessions
                WHERE synced_at IS NULL
                ORDER BY created_at ASC, rowid ASC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()

        return [
            {
                "client_id": row["client_id"],
                "app_name": row["app_name"],
                "window_title": row["window_title"],
                "is_idle": bool(row["is_idle"]),
                "started_at": row["started_at"],
                "ended_at": row["ended_at"],
                "focus_session_id": row["focus_session_id"],
            }
            for row in rows
        ]

    def mark_synced(self, client_ids: list[str | UUID]) -> int:
        """
        Mark sessions as synchronized.

        Returns the number of records newly marked as synced.
        Synced rows are retained to prevent duplicate local inserts.
        """
        if not client_ids:
            return 0

        normalized_ids = []

        for client_id in client_ids:
            try:
                normalized_ids.append(str(UUID(str(client_id))))
            except (ValueError, TypeError, AttributeError) as exc:
                raise ValueError("Every client_id must be a valid UUID.") from exc

        now = datetime.now(timezone.utc).isoformat()
        updated = 0

        with self._connect() as connection:
            for start in range(0, len(normalized_ids), 500):
                batch = normalized_ids[start : start + 500]
                placeholders = ",".join("?" for _ in batch)

                cursor = connection.execute(
                    f"""
                    UPDATE pending_sessions
                    SET synced_at = ?
                    WHERE synced_at IS NULL
                      AND client_id IN ({placeholders})
                    """,
                    (now, *batch),
                )

                updated += cursor.rowcount

        return updated

    def count_pending(self) -> int:
        """Return the number of sessions awaiting synchronization."""
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT COUNT(*) AS total
                FROM pending_sessions
                WHERE synced_at IS NULL
                """
            ).fetchone()

        return int(row["total"])