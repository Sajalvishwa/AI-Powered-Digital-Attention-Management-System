
"""Seed demo data for the analytics engine.

Run (from backend/):
    python -m app.jobs.seed_demo
    python -m app.jobs.seed_demo --reset
    python -m app.jobs.seed_demo --user <uuid> --days 14 --no-report
"""

import argparse
import random
import uuid
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import delete, func, select

from app.core.database import SessionLocal
from app.ml.features import DEFAULT_TZ
from app.models.activity_log import ActivitySession
from app.models.focus_session import FocusSession
from app.models.notification_event import NotificationEvent
from app.models.user import User


TAG = "seed-demo"
NOTIF_SUFFIX = " [demo]"

FOCUS_APPS = ["Code.exe", "WindowsTerminal.exe", "Notion.exe"]
DISTRACT_APPS = ["YouTube", "Instagram", "WhatsApp"]
NOTIF_APPS = ["WhatsApp", "Instagram", "Slack"]

ZONE = ZoneInfo(DEFAULT_TZ)

# Monday to Sunday: higher value means more distraction.
WEEKDAY = [0.10, 0.0, -0.05, -0.05, 0.05, 0.30, 0.35]


def _drift(day, mood):
    """Calculate daily distraction level using weekday and mood."""
    return min(
        1.0,
        max(0.0, 0.45 + WEEKDAY[day.weekday()] + 0.25 * mood),
    )


def _at(day, h, m):
    return datetime.combine(day, time(h, m), tzinfo=ZONE)


def _act(uid, app, s, e, fs_id=None, idle=False):
    return ActivitySession(
        client_id=uuid.uuid4(),
        user_id=uid,
        app_name=app,
        window_title=TAG,
        is_idle=idle,
        started_at=s,
        ended_at=e,
        focus_session_id=fs_id,
    )


def _focus_block(rng, uid, day, h, m, minutes, switch_p, fatigue):
    start = _at(day, h, m)
    end = start + timedelta(minutes=minutes)

    fs = FocusSession(
        id=uuid.uuid4(),
        user_id=uid,
        label=TAG,
        planned_min=minutes,
        started_at=start,
        ended_at=end,
        status="completed",
        switch_count=0,
    )

    rows = []
    t = start
    app = rng.choice(FOCUS_APPS)
    switches = 0

    while t < end:
        late = (
            fatigue
            and (t - start).total_seconds() >= 90 * 60
        )
        seg = rng.randint(2, 3) if late else rng.randint(2, 6)
        seg_end = min(t + timedelta(minutes=seg), end)

        rows.append(_act(uid, app, t, seg_end, fs.id))
        t = seg_end

        if t >= end:
            break

        if rng.random() < 0.05:
            ie = min(t + timedelta(minutes=3), end)
            rows.append(_act(uid, "Idle", t, ie, fs.id, idle=True))
            t = ie

        if rng.random() < (0.8 if late else switch_p):
            new = (
                rng.choice(DISTRACT_APPS)
                if rng.random() < 0.5
                else rng.choice(FOCUS_APPS)
            )
            if new != app:
                switches += 1
            app = new

    fs.switch_count = switches
    return fs, rows


def _free_block(rng, uid, day, h, m, minutes):
    t = _at(day, h, m)
    end = t + timedelta(minutes=minutes)
    rows = []

    pool = DISTRACT_APPS + ["chrome.exe"] * 2 + FOCUS_APPS[:1]

    while t < end:
        seg_end = min(
            t + timedelta(minutes=rng.randint(1, 4)),
            end,
        )
        rows.append(_act(uid, rng.choice(pool), t, seg_end))
        t = seg_end

    return rows


def _build_day(rng, uid, day, drift, fatigue_day):
    """Build a day's focus sessions, activity and notification events."""
    switch_p = 0.1 + 0.7 * drift
    scale = 1 - 0.6 * drift

    # Fixed planned lengths reduce random variation between days.
    plan = [
        (10, 0, 70),
        (14, 30, 50),
        (19, 0, 40),
    ]

    sessions, acts = [], []

    for i, (h, m, mins) in enumerate(plan):
        long_one = fatigue_day and i == 0
        mins = 120 if long_one else max(15, int(mins * scale))

        fs, rows = _focus_block(
            rng, uid, day, h, m, mins, switch_p, long_one
        )

        sessions.append(fs)
        acts += rows

    # Add activity outside planned focus sessions.
    for h, m in [(8, 30), (12, 30), (21, 0)]:
        acts += _free_block(rng, uid, day, h, m, 60)

    notifs = [
        NotificationEvent(
            client_id=uuid.uuid4(),
            user_id=uid,
            app_name=rng.choice(NOTIF_APPS) + NOTIF_SUFFIX,
            received_at=_at(
                day,
                rng.randint(9, 21),
                rng.randint(0, 59),
            ),
        )
        for _ in range(rng.randint(6, 12))
    ]

    return sessions, acts, notifs


def _wipe(db, uid):
    """Remove only demo rows belonging to the selected user."""
    db.execute(
        delete(ActivitySession).where(
            ActivitySession.user_id == uid,
            ActivitySession.window_title == TAG,
        )
    )

    db.execute(
        delete(NotificationEvent).where(
            NotificationEvent.user_id == uid,
            NotificationEvent.app_name.like("%" + NOTIF_SUFFIX),
        )
    )

    db.execute(
        delete(FocusSession).where(
            FocusSession.user_id == uid,
            FocusSession.label == TAG,
        )
    )

    db.commit()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--user")
    ap.add_argument("--days", type=int, default=14)
    ap.add_argument("--reset", action="store_true")
    ap.add_argument("--no-report", action="store_true")
    args = ap.parse_args()

    if args.days < 1:
        ap.error("--days must be at least 1")

    with SessionLocal() as db:
        uid = (
            uuid.UUID(args.user)
            if args.user
            else db.scalar(
                select(User.id)
                .where(User.is_active.is_(True))
                .limit(1)
            )
        )

        if uid is None:
            raise SystemExit("No active user found. Register one first.")

        user_exists = db.scalar(
            select(User.id).where(User.id == uid)
        )
        if user_exists is None:
            raise SystemExit(f"User not found: {uid}")

        print("user:", uid)

        if args.reset:
            _wipe(db, uid)
        elif db.scalar(
            select(func.count())
            .select_from(ActivitySession)
            .where(
                ActivitySession.user_id == uid,
                ActivitySession.window_title == TAG,
            )
        ):
            raise SystemExit(
                "Demo data already exists. Use --reset to recreate."
            )

        rng = random.Random(42)
        today = datetime.now(ZONE).date()
        days = [
            today - timedelta(days=args.days - i)
            for i in range(args.days)
        ]  # Ends yesterday.

        # Mood carries over from day to day.
        mood, moods = 0.0, []
        for _ in days:
            mood = 0.75 * mood + rng.gauss(0, 0.25)
            moods.append(mood)

        n_act = 0

        for i, d in enumerate(days):
            sessions, acts, notifs = _build_day(
                rng,
                uid,
                d,
                _drift(d, moods[i]),
                i in (10, len(days) - 3),
            )

            db.add_all(sessions)
            db.flush()  # Focus sessions must exist before activity FK rows.

            db.add_all(acts + notifs)
            n_act += len(acts)

        db.commit()

        print(
            f"seeded {n_act} activity rows over {args.days} days "
            f"({days[0]} -> {days[-1]})"
        )

        if args.no_report:
            return

        from app.services.insight_service import build_day_report

        for d in days:
            r = build_day_report(db, uid, d)
            s = r["scores"]

            print(
                d,
                "focus", s["focus_score"],
                "| prod", s["productivity_score"],
                "| stab", s["stability_score"],
                "| trend", s["concentration_trend"],
            )

        print("\nLast day summary:", r["summary"])
        print("Insight types:", [i["type"] for i in r["insights"]])


if __name__ == "__main__":
    main()
