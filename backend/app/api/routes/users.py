from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.user import SettingsOut, SettingsUpdate, UserOut, UserUpdate
from app.services import user_service

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserOut)
def read_me(user: User = Depends(get_current_user)):
    return user


@router.put("/me", response_model=UserOut)
def update_me(
    body: UserUpdate, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    return user_service.update_profile(db, user, body.name)


@router.get("/me/settings", response_model=SettingsOut)
def read_settings(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return user_service.get_settings(db, user)


@router.put("/me/settings", response_model=SettingsOut)
def update_settings(
    body: SettingsUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return user_service.update_settings(db, user, body.model_dump(exclude_unset=True))
