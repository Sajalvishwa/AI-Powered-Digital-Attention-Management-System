"""DB queries for goals."""
import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.goal import Goal


def list_for_user(db: Session, user_id: uuid.UUID, active_only: bool) -> list[Goal]:
    stmt = select(Goal).where(Goal.user_id == user_id)
    if active_only:
        stmt = stmt.where(Goal.is_active.is_(True))
    return list(db.scalars(stmt.order_by(Goal.created_at.desc())).all())


def get_owned(db: Session, goal_id: uuid.UUID, user_id: uuid.UUID) -> Goal | None:
    return db.scalar(select(Goal).where(Goal.id == goal_id, Goal.user_id == user_id))


def count_for_user(db: Session, user_id: uuid.UUID) -> int:
    return db.scalar(select(func.count()).select_from(Goal).where(Goal.user_id == user_id)) or 0


def find_active_same(
    db: Session, user_id: uuid.UUID, goal_type: str, app_name: str | None
) -> Goal | None:
    """An active goal of the same type (and same app, for app goals)."""
    stmt = select(Goal).where(
        Goal.user_id == user_id, Goal.type == goal_type, Goal.is_active.is_(True)
    )
    if app_name is None:
        stmt = stmt.where(Goal.app_name.is_(None))
    else:
        stmt = stmt.where(func.lower(Goal.app_name) == app_name.lower())
    return db.scalars(stmt).first()


def create(
    db: Session, user_id: uuid.UUID, goal_type: str, target_value: int, app_name: str | None
) -> Goal:
    goal = Goal(user_id=user_id, type=goal_type, target_value=target_value, app_name=app_name)
    db.add(goal)
    db.flush()
    return goal


def delete(db: Session, goal: Goal) -> None:
    db.delete(goal)
