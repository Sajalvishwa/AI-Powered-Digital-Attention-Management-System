from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.account import DeleteDataOut
from app.services import account_service

router = APIRouter(prefix="/users", tags=["users"])


@router.delete("/me/data", response_model=DeleteDataOut)
def delete_my_data(
    confirm: bool = Query(False, description="Must be true. This cannot be undone."),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Deletes activity, focus sessions, goals and scores. Account and settings stay."""
    if not confirm:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "Add ?confirm=true to delete all your data"
        )
    return DeleteDataOut(deleted=account_service.delete_my_data(db, user))
