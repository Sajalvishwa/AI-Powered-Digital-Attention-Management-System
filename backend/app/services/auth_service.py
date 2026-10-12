"""Auth business logic: register, login, refresh (rotation), logout."""
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core import security
from app.core.config import settings
from app.models.user import User
from app.repositories import refresh_token_repository as rt_repo
from app.repositories import user_repository as user_repo
from app.schemas.user import TokenPair, UserCreate

# used to keep login timing similar when the email does not exist
_DUMMY_HASH = security.hash_password("dummy-password-for-timing")


def _unauthorized(msg: str) -> HTTPException:
    return HTTPException(status.HTTP_401_UNAUTHORIZED, msg)


def _issue_tokens(db: Session, user: User) -> TokenPair:
    """Creates access + refresh token. Caller must commit."""
    access = security.create_access_token(user.id, user.role)
    raw_refresh = security.generate_refresh_token()
    expires = datetime.now(timezone.utc) + timedelta(days=settings.refresh_expire_days)
    rt_repo.create(db, user.id, security.hash_refresh_token(raw_refresh), expires)
    return TokenPair(access_token=access, refresh_token=raw_refresh)


def register(db: Session, data: UserCreate) -> User:
    conflict = HTTPException(status.HTTP_409_CONFLICT, "Email already registered")
    if user_repo.get_by_email(db, data.email):
        raise conflict
    try:
        user = user_repo.create_user(
            db, data.name.strip(), data.email, security.hash_password(data.password)
        )
        db.commit()
    except IntegrityError:  # two requests with same email at the same time
        db.rollback()
        raise conflict
    return user


def login(db: Session, email: str, password: str) -> TokenPair:
    user = user_repo.get_by_email(db, email)
    if user is None:
        security.verify_password(password, _DUMMY_HASH)
        raise _unauthorized("Invalid email or password")
    if not security.verify_password(password, user.password_hash) or not user.is_active:
        raise _unauthorized("Invalid email or password")
    pair = _issue_tokens(db, user)
    db.commit()
    return pair


def refresh(db: Session, raw_token: str) -> TokenPair:
    now = datetime.now(timezone.utc)
    token = rt_repo.get_by_hash(db, security.hash_refresh_token(raw_token))
    if token is None:
        raise _unauthorized("Invalid refresh token")
    if token.revoked_at is not None:
        # an old token was used again -> possible theft -> log out everywhere
        rt_repo.revoke_all_for_user(db, token.user_id, now)
        db.commit()
        raise _unauthorized("Invalid refresh token")
    if token.expires_at <= now:
        raise _unauthorized("Refresh token expired")
    user = user_repo.get_by_id(db, token.user_id)
    if user is None or not user.is_active:
        raise _unauthorized("Invalid refresh token")
    token.revoked_at = now  # rotation: old token can be used only once
    pair = _issue_tokens(db, user)
    db.commit()
    return pair


def logout(db: Session, raw_token: str) -> None:
    token = rt_repo.get_by_hash(db, security.hash_refresh_token(raw_token))
    if token is not None and token.revoked_at is None:
        token.revoked_at = datetime.now(timezone.utc)
        db.commit()
