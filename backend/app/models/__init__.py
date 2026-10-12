"""Import every model here so Alembic autogenerate can see them."""
from app.models.activity_log import ActivitySession
from app.models.device import Device
from app.models.focus_session import FocusSession
from app.models.goal import Goal
from app.models.notification_event import NotificationEvent
from app.models.refresh_token import RefreshToken
from app.models.score import DailyScore
from app.models.user import User, UserSettings

__all__ = [
    "ActivitySession", "Device", "FocusSession", "Goal",
    "NotificationEvent", "RefreshToken", "DailyScore", "User", "UserSettings",
]
