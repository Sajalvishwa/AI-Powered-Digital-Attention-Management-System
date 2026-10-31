from sqlalchemy import text
from app.core.database import SessionLocal

with SessionLocal() as db:
    for tbl, cond in [("focus_sessions", "label is distinct from 'seed-demo'"),
                      ("activity_sessions", "window_title is distinct from 'seed-demo'")]:
        rows = db.execute(text(
            f"select user_id, date(started_at) d, count(*) from {tbl} "
            f"where {cond} group by 1, 2 order by 2")).all()
        print(tbl, rows)