import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.focus import FocusOut, FocusStart, FocusUpdate
from app.services import focus_service

router = APIRouter(prefix="/focus-sessions", tags=["focus"])


@router.post("", response_model=FocusOut, status_code=status.HTTP_201_CREATED)
def start_focus(
    body: FocusStart, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    return focus_service.start(db, user, body)


@router.get("/active", response_model=FocusOut | None)
def active_focus(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return focus_service.active(db, user)


@router.patch("/{focus_id}", response_model=FocusOut)
def update_focus(
    focus_id: uuid.UUID,
    body: FocusUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return focus_service.update(db, user, focus_id, body)


@router.get("", response_model=list[FocusOut])
def focus_history(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return focus_service.history(db, user, limit, offset)
