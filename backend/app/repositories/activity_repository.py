"""DB queries for activity sessions."""
import uuid

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.models.activity_log import ActivitySession


def insert_ignore_duplicates(db: Session, rows: list[dict]) -> int:
    """Bulk insert. Rows whose (user_id, client_id) already exist are skipped.
    Returns how many rows were really inserted."""
    if not rows:
        return 0
    stmt = (
        pg_insert(ActivitySession)
        .values(rows)
        .on_conflict_do_nothing(index_elements=["user_id", "client_id"])
        .returning(ActivitySession.id)
    )
    return len(db.execute(stmt).all())


def recent(db: Session, user_id: uuid.UUID, limit: int) -> list[ActivitySession]:
    stmt = (
        select(ActivitySession)
        .where(ActivitySession.user_id == user_id)
        .order_by(ActivitySession.started_at.desc())
        .limit(limit)
    )
    return list(db.scalars(stmt).all())
