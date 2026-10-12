from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.stats import RangeStatsOut, TodayStatsOut
from app.services import stats_service

router = APIRouter(prefix="/stats", tags=["stats"])

MAX_RANGE_DAYS = 92


@router.get("/today", response_model=TodayStatsOut)
def stats_today(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return stats_service.today(db, user)


@router.get("/range", response_model=RangeStatsOut)
def stats_range(
    from_date: date = Query(alias="from"),
    to_date: date = Query(alias="to"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if to_date < from_date:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "'to' must be >= 'from'")
    if (to_date - from_date).days >= MAX_RANGE_DAYS:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY, f"Range can be at most {MAX_RANGE_DAYS} days"
        )
    return stats_service.date_range(db, user, from_date, to_date)
