
"""Database queries for activity statistics."""

from datetime import date, timedelta
import uuid

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.models.activity_log import ActivitySession


def totals(
    db: Session,
    user_id: uuid.UUID,
    start,
    end,
) -> dict:
    """Return activity totals and app-switch count for a user."""

    active_duration = func.coalesce(
        func.sum(
            case(
                (ActivitySession.is_idle.is_(False), ActivitySession.duration_sec),
                else_=0,
            )
        ),
        0,
    )

    idle_duration = func.coalesce(
        func.sum(
            case(
                (ActivitySession.is_idle.is_(True), ActivitySession.duration_sec),
                else_=0,
            )
        ),
        0,
    )

    focus_duration = func.coalesce(
        func.sum(
            case(
                (
                    (
                        ActivitySession.is_idle.is_(False)
                        & ActivitySession.focus_session_id.is_not(None)
                    ),
                    ActivitySession.duration_sec,
                ),
                else_=0,
            )
        ),
        0,
    )

    stmt = (
        select(
            active_duration.label("screen_time_sec"),
            idle_duration.label("idle_sec"),
            focus_duration.label("focus_sec"),
        )
        .where(
            ActivitySession.user_id == user_id,
            ActivitySession.started_at >= start,
            ActivitySession.started_at < end,
        )
    )

    row = db.execute(stmt).one()

    # Find the previous active app for each active session.
    # Idle and zero-duration sessions are excluded.
    previous_sessions = (
        select(
            ActivitySession.app_name.label("app_name"),
            func.lag(ActivitySession.app_name)
            .over(
                order_by=(
                    ActivitySession.started_at,
                    ActivitySession.id,
                )
            )
            .label("previous_app"),
        )
        .where(
            ActivitySession.user_id == user_id,
            ActivitySession.started_at >= start,
            ActivitySession.started_at < end,
            ActivitySession.is_idle.is_(False),
            ActivitySession.duration_sec > 0,
        )
        .subquery()
    )

    # Count only transitions between different active apps.
    switches_stmt = (
        select(func.count())
        .select_from(previous_sessions)
        .where(
            previous_sessions.c.previous_app.is_not(None),
            previous_sessions.c.app_name
            != previous_sessions.c.previous_app,
        )
    )

    task_switches = int(
        db.execute(switches_stmt).scalar_one()
    )

    return {
        "screen_time_sec": int(row.screen_time_sec),
        "idle_sec": int(row.idle_sec),
        "focus_sec": int(row.focus_sec),
        "task_switches": task_switches,
    }


def top_apps(
    db: Session,
    user_id: uuid.UUID,
    start,
    end,
) -> list[dict]:
    """Return the ten apps with the most active usage."""

    stmt = (
        select(
            ActivitySession.app_name.label("app_name"),
            func.coalesce(
                func.sum(ActivitySession.duration_sec), 0
            ).label("total_sec"),
            func.count(ActivitySession.id).label("sessions"),
        )
        .where(
            ActivitySession.user_id == user_id,
            ActivitySession.started_at >= start,
            ActivitySession.started_at < end,
            ActivitySession.is_idle.is_(False),
        )
        .group_by(ActivitySession.app_name)
        .order_by(func.sum(ActivitySession.duration_sec).desc())
        .limit(10)
    )

    return [
        {
            "app_name": row.app_name,
            "total_sec": int(row.total_sec),
            "sessions": int(row.sessions),
        }
        for row in db.execute(stmt)
    ]


def hourly(
    db: Session,
    user_id: uuid.UUID,
    start,
    end,
    timezone_name: str,
) -> list[dict]:
    """Return hourly activity buckets in the user's timezone."""

    local_time = ActivitySession.started_at.op("AT TIME ZONE")(
        timezone_name
    )
    hour_expr = func.extract("hour", local_time).label("hour")

    active_duration = func.coalesce(
        func.sum(
            case(
                (ActivitySession.is_idle.is_(False), ActivitySession.duration_sec),
                else_=0,
            )
        ),
        0,
    )

    idle_duration = func.coalesce(
        func.sum(
            case(
                (ActivitySession.is_idle.is_(True), ActivitySession.duration_sec),
                else_=0,
            )
        ),
        0,
    )

    stmt = (
        select(
            hour_expr,
            active_duration.label("active_sec"),
            idle_duration.label("idle_sec"),
        )
        .where(
            ActivitySession.user_id == user_id,
            ActivitySession.started_at >= start,
            ActivitySession.started_at < end,
        )
        .group_by(hour_expr)
    )

    buckets = {
        int(row.hour): {
            "active_sec": int(row.active_sec),
            "idle_sec": int(row.idle_sec),
        }
        for row in db.execute(stmt)
    }

    return [
        {
            "hour": hour,
            "active_sec": buckets.get(hour, {}).get("active_sec", 0),
            "idle_sec": buckets.get(hour, {}).get("idle_sec", 0),
        }
        for hour in range(24)
    ]


def daily(
    db: Session,
    user_id: uuid.UUID,
    start,
    end,
    timezone_name: str,
) -> list[dict]:
    """Return daily activity buckets in the user's timezone."""

    local_time = ActivitySession.started_at.op("AT TIME ZONE")(
        timezone_name
    )
    day_expr = func.date(local_time).label("day")

    active_duration = func.coalesce(
        func.sum(
            case(
                (ActivitySession.is_idle.is_(False), ActivitySession.duration_sec),
                else_=0,
            )
        ),
        0,
    )

    idle_duration = func.coalesce(
        func.sum(
            case(
                (ActivitySession.is_idle.is_(True), ActivitySession.duration_sec),
                else_=0,
            )
        ),
        0,
    )

    stmt = (
        select(
            day_expr,
            active_duration.label("active_sec"),
            idle_duration.label("idle_sec"),
        )
        .where(
            ActivitySession.user_id == user_id,
            ActivitySession.started_at >= start,
            ActivitySession.started_at < end,
        )
        .group_by(day_expr)
        .order_by(day_expr)
    )

    buckets = {
        row.day: {
            "active_sec": int(row.active_sec),
            "idle_sec": int(row.idle_sec),
        }
        for row in db.execute(stmt)
    }

    first_day = start.date()
    last_day = (end - timedelta(microseconds=1)).date()
    result = []

    current_day: date = first_day
    while current_day <= last_day:
        values = buckets.get(
            current_day,
            {"active_sec": 0, "idle_sec": 0},
        )
        result.append(
            {
                "day": current_day,
                "active_sec": values["active_sec"],
                "idle_sec": values["idle_sec"],
            }
        )
        current_day += timedelta(days=1)

    return result
