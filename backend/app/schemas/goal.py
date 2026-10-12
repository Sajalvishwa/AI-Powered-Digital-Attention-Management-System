import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

GoalType = Literal["daily_focus_min", "max_task_switches", "max_app_min"]
MINUTE_GOALS = ("daily_focus_min", "max_app_min")  # a day has only 1440 minutes
MAX_MINUTES = 1440


class GoalCreate(BaseModel):
    type: GoalType
    target_value: int = Field(ge=1, le=100000)
    app_name: str | None = Field(default=None, min_length=1, max_length=255)

    @model_validator(mode="after")
    def check_rules(self) -> "GoalCreate":
        if self.type == "max_app_min" and not self.app_name:
            raise ValueError("app_name is required for max_app_min goals")
        if self.type != "max_app_min" and self.app_name is not None:
            raise ValueError("app_name is only allowed for max_app_min goals")
        if self.type in MINUTE_GOALS and self.target_value > MAX_MINUTES:
            raise ValueError("target_value can be at most 1440 minutes per day")
        return self


class GoalUpdate(BaseModel):
    """Send only what you want to change. Type and app cannot be changed."""

    target_value: int | None = Field(default=None, ge=1, le=100000)
    is_active: bool | None = None


class GoalOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    type: str
    target_value: int
    app_name: str | None
    is_active: bool
    created_at: datetime
