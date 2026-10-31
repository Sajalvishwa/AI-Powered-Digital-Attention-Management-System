"""Nightly job: compute yesterday's metrics, scores and insights for every active user.

Run:  python -m app.jobs.nightly            (yesterday, IST)
      python -m app.jobs.nightly 2026-01-05 (specific day)
"""
import logging
import sys
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import select

from app.core.database import SessionLocal
from app.ml.features import DEFAULT_TZ
from app.models.user import User
from app.services.insight_service import build_day_report

log = logging.getLogger("nightly")


def run_for_day(day: date) -> tuple[int, int]:
    ok = failed = 0
    with SessionLocal() as db:
        ids = list(db.scalars(select(User.id).where(User.is_active.is_(True))))
    for uid in ids:
        with SessionLocal() as db:  # fresh session per user, so one failure cannot poison the rest
            try:
                build_day_report(db, uid, day)
                ok += 1
            except Exception:
                db.rollback()
                failed += 1
                log.exception("nightly failed for user %s", uid)
    return ok, failed


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    day = (date.fromisoformat(sys.argv[1]) if len(sys.argv) > 1
           else datetime.now(ZoneInfo(DEFAULT_TZ)).date() - timedelta(days=1))
    ok, failed = run_for_day(day)
    log.info("nightly %s done: %d ok, %d failed", day, ok, failed)
    sys.exit(1 if failed else 0)