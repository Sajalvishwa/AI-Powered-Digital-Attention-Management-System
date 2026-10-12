
from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session

from app.core import rate_limit
from app.core.database import get_db
from app.schemas.user import RefreshRequest, TokenPair, UserCreate, UserLogin, UserOut
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(
    body: UserCreate,
    request: Request,
    db: Session = Depends(get_db),
):
    ip = request.client.host if request.client else "unknown"
    rate_limit.check(f"register:{ip}", 3, 60)

    return auth_service.register(db, body)


@router.post("/login", response_model=TokenPair)
def login(
    body: UserLogin,
    request: Request,
    db: Session = Depends(get_db),
):
    ip = request.client.host if request.client else "unknown"
    email = body.email.strip().lower()

    # Maximum 20 login attempts per minute per IP.
    rate_limit.check(f"login:ip:{ip}", 20, 60)

    # Maximum 5 login attempts per minute per email.
    rate_limit.check(f"login:email:{email}", 5, 60)

    return auth_service.login(db, body.email, body.password)


@router.post("/refresh", response_model=TokenPair)
def refresh(
    body: RefreshRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    ip = request.client.host if request.client else "unknown"
    rate_limit.check(f"refresh:{ip}", 30, 60)

    return auth_service.refresh(db, body.refresh_token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    body: RefreshRequest,
    db: Session = Depends(get_db),
) -> None:
    auth_service.logout(db, body.refresh_token)
