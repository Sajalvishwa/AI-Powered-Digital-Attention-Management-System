
"""Privacy: user can erase all collected data but keep the account."""

from sqlalchemy.orm import Session

from app.models.user import User
from app.repositories import account_repository


def delete_my_data(db: Session, user: User) -> dict[str, int]:
    """Delete the current user's collected data in one transaction."""
    try:
        counts = account_repository.delete_all_user_data(db, user.id)
        db.commit()
        return counts
    except Exception:
        db.rollback()
        raise
