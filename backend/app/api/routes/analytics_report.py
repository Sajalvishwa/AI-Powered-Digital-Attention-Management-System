from datetime import date, datetime
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.ml.features import DEFAULT_TZ
from app.models.user import User
from app.services.insight_service import build_day_report
from datetime import date, datetime, timedelta
from app.repositories import analytics_repository as repo

router = APIRouter(prefix="/analytics", tags=["analytics"])


def _report(db: Session, user: User, day: date | None):
    today = datetime.now(ZoneInfo(DEFAULT_TZ)).date()
    day = day or today
    if day > today:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "date cannot be in the future")
    return build_day_report(db, user.id, day)


@router.get("/daily")
def daily(day: date | None = Query(None, alias="date"),
          db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    r = _report(db, user, day)
    return {"day": r["day"], "features": r["features"]}


@router.get("/focus-score")
def focus_score(day: date | None = Query(None, alias="date"),
                db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    r = _report(db, user, day)
    return {"day": r["day"], **r["scores"]}


@router.get("/distractions")
def distractions(day: date | None = Query(None, alias="date"),
                 db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    r = _report(db, user, day)
    return {"day": r["day"], **r["distractions"]}


@router.get("/predictions")
def predictions(day: date | None = Query(None, alias="date"),
                db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    r = _report(db, user, day)
    return {"day": r["day"], **r["predictions"]}


@router.get("/insights")
def insights(day: date | None = Query(None, alias="date"),
             db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    r = _report(db, user, day)
    return {"day": r["day"], "insights": r["insights"]}


@router.get("/summary")
def summary(day: date | None = Query(None, alias="date"),
            db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return _report(db, user, day)["summary"]

@router.get("/trend")
def trend(days: int = Query(7, ge=2, le=30),
          db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Stored daily scores only (no recompute). Days without data have null scores."""
    today = datetime.now(ZoneInfo(DEFAULT_TZ)).date()
    first = today - timedelta(days=days - 1)
    by_day = {r.day: r for r in repo.fetch_scores_range(db, user.id, first, today)}
    out = []
    for i in range(days):
        d = first + timedelta(days=i)
        r = by_day.get(d)
        out.append({
            "day": d.isoformat(),
            "focus_score": r.focus_score if r else None,
            "productivity_score": r.productivity_score if r else None,
        })
    return {"days": out}