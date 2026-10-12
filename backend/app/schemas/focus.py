import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class FocusStart(BaseModel):
    planned_min: int = Field(ge=1, le=480)
    label: str | None = Field(default=None, max_length=120)


class FocusUpdate(BaseModel):
    action: Literal["pause", "resume", "stop", "cancel"]
    switch_count: int | None = Field(default=None, ge=0)  # agent may send it on "stop"


class FocusOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    label: str | None
    planned_min: int
    started_at: datetime
    ended_at: datetime | None
    status: str
    switch_count: int
