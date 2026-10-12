from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core import rate_limit
from app.core.database import get_db
from app.models.user import User
from app.repositories import activity_repository
from app.schemas.activity import ActivityBatchIn, ActivityBatchOut, ActivitySessionOut
from app.services import ingestion_service

router = APIRouter(prefix="/activity", tags=["activity"])


@router.post("/batch", response_model=ActivityBatchOut)
def upload_batch(
    body: ActivityBatchIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Desktop agent sends up to 500 sessions. Safe to retry (idempotent)."""
    rate_limit.check(f"batch:{user.id}", 30, 60)  # 30 uploads/min per user
    return ingestion_service.ingest(db, user, body)


@router.get("/recent", response_model=list[ActivitySessionOut])
def recent_activity(
    limit: int = Query(20, ge=1, le=200),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return activity_repository.recent(db, user.id, limit)
