"""Goal rules: limits, no duplicates, owner-only access."""
import uuid

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.goal import Goal
from app.models.user import User
from app.repositories import goal_repository as repo
from app.schemas.goal import MAX_MINUTES, MINUTE_GOALS, GoalCreate, GoalUpdate

MAX_GOALS_PER_USER = 50


def _not_found() -> HTTPException:
    return HTTPException(status.HTTP_404_NOT_FOUND, "Goal not found")


def _duplicate() -> HTTPException:
    return HTTPException(
        status.HTTP_409_CONFLICT, "An active goal of this type already exists. Update it instead."
    )


def create(db: Session, user: User, data: GoalCreate) -> Goal:
    if repo.count_for_user(db, user.id) >= MAX_GOALS_PER_USER:
        raise HTTPException(status.HTTP_409_CONFLICT, f"Max {MAX_GOALS_PER_USER} goals allowed")
    if repo.find_active_same(db, user.id, data.type, data.app_name):
        raise _duplicate()
    goal = repo.create(db, user.id, data.type, data.target_value, data.app_name)
    db.commit()
    return goal


def list_goals(db: Session, user: User, active_only: bool) -> list[Goal]:
    return repo.list_for_user(db, user.id, active_only)


def update(db: Session, user: User, goal_id: uuid.UUID, data: GoalUpdate) -> Goal:
    goal = repo.get_owned(db, goal_id, user.id)
    if goal is None:  # also when it belongs to someone else
        raise _not_found()

    if data.target_value is not None:
        if goal.type in MINUTE_GOALS and data.target_value > MAX_MINUTES:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY, "target_value can be at most 1440 minutes"
            )
        goal.target_value = data.target_value

    if data.is_active is not None:
        if data.is_active and not goal.is_active:
            same = repo.find_active_same(db, user.id, goal.type, goal.app_name)
            if same is not None and same.id != goal.id:
                raise _duplicate()
        goal.is_active = data.is_active

    db.commit()
    return goal


def delete(db: Session, user: User, goal_id: uuid.UUID) -> None:
    goal = repo.get_owned(db, goal_id, user.id)
    if goal is None:
        raise _not_found()
    repo.delete(db, goal)
    db.commit()
