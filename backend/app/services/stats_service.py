"""Builds stats for 'today' and for a date range, in the user's own timezone."""
from datetime import date, datetime, time, timedelta, timezone, tzinfo
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy.orm import Session

from app.models.user import User
from app.repositories import stats_repository as repo
from app.schemas.stats import RangeStatsOut, TodayStatsOut


def _user_tz(user: User) -> tuple[str, tzinfo]:
    name = user.settings.timezone if user.settings else "Asia/Kolkata"
    try:
        return name, ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError, OSError):
        return "UTC", timezone.utc


def _bounds(first: date, last: date, tz: tzinfo) -> tuple[datetime, datetime]:
    start = datetime.combine(first, time.min, tzinfo=tz)
    end = datetime.combine(last + timedelta(days=1), time.min, tzinfo=tz)
    return start, end


def _common(db: Session, user: User, start: datetime, end: datetime) -> dict:
    data = repo.totals(db, user.id, start, end)
    data["top_apps"] = repo.top_apps(db, user.id, start, end)
    return data


def today(db: Session, user: User) -> TodayStatsOut:
    tz_name, tz = _user_tz(user)
    day = datetime.now(tz).date()
    start, end = _bounds(day, day, tz)
    return TodayStatsOut(
        day=day,
        timezone=tz_name,
        timeline=repo.hourly(db, user.id, start, end, tz_name),
        **_common(db, user, start, end),
    )


def date_range(db: Session, user: User, first: date, last: date) -> RangeStatsOut:
    tz_name, tz = _user_tz(user)
    start, end = _bounds(first, last, tz)
    return RangeStatsOut(
        from_day=first,
        to_day=last,
        timezone=tz_name,
        daily=repo.daily(db, user.id, start, end, tz_name),
        **_common(db, user, start, end),
    )
