"""DB queries for users. No business logic here."""
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.user import User, UserSettings


def get_by_email(db: Session, email: str) -> User | None:
    return db.scalar(select(User).where(User.email == email))


def get_by_id(db: Session, user_id: uuid.UUID) -> User | None:
    return db.get(User, user_id)


def create_user(db: Session, name: str, email: str, password_hash: str) -> User:
    """Creates user + default settings row (not committed)."""
    user = User(name=name, email=email, password_hash=password_hash)
    user.settings = UserSettings()
    db.add(user)
    db.flush()
    return user
