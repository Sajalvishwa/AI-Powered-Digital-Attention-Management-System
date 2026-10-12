"""Profile and settings logic."""
from sqlalchemy.orm import Session

from app.models.user import User, UserSettings


def update_profile(db: Session, user: User, name: str) -> User:
    user.name = name.strip()
    db.commit()
    return user


def _get_or_create_settings(db: Session, user: User) -> UserSettings:
    if user.settings is None:
        user.settings = UserSettings()
        db.flush()
    return user.settings


def get_settings(db: Session, user: User) -> UserSettings:
    s = _get_or_create_settings(db, user)
    db.commit()
    return s


def update_settings(db: Session, user: User, changes: dict) -> UserSettings:
    s = _get_or_create_settings(db, user)
    for field, value in changes.items():
        setattr(s, field, value)
    db.commit()
    return s
