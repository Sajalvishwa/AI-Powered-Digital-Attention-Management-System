"""Receives batches from the desktop agent and stores them safely."""
import uuid

from sqlalchemy.orm import Session

from app.models.user import User
from app.repositories import activity_repository, focus_repository
from app.schemas.activity import ActivityBatchIn, ActivityBatchOut


def ingest(db: Session, user: User, batch: ActivityBatchIn) -> ActivityBatchOut:
    cfg = user.settings
    store_titles = bool(cfg and cfg.store_window_titles)
    ignored = {a.lower() for a in (cfg.ignored_apps if cfg else [])}

    # only accept focus_session ids that belong to this user
    wanted = {s.focus_session_id for s in batch.sessions if s.focus_session_id}
    valid_focus = focus_repository.existing_ids(db, user.id, wanted)

    rows: list[dict] = []
    skipped = 0
    for s in batch.sessions:
        if not s.is_idle and s.app_name.lower() in ignored:
            skipped += 1
            continue
        rows.append(
            {
                "id": uuid.uuid4(),
                "client_id": s.client_id,
                "user_id": user.id,  # always from the token, never from the body
                "app_name": s.app_name,
                # privacy: titles are saved only if the user opted in
                "window_title": s.window_title if store_titles else None,
                "is_idle": s.is_idle,
                "started_at": s.started_at,
                "ended_at": s.ended_at,
                "focus_session_id": s.focus_session_id if s.focus_session_id in valid_focus else None,
            }
        )

    inserted = activity_repository.insert_ignore_duplicates(db, rows)
    db.commit()
    return ActivityBatchOut(
        received=len(batch.sessions),
        inserted=inserted,
        duplicates=len(rows) - inserted,
        skipped=skipped,
    )
