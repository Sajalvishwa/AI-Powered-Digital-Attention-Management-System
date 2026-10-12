import uuid
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class UserCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)

    @field_validator("password")
    @classmethod
    def strong_password(cls, v: str) -> str:
        if not (
            any(c.islower() for c in v)
            and any(c.isupper() for c in v)
            and any(c.isdigit() for c in v)
        ):
            raise ValueError("Password needs upper, lower and a digit")
        return v


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    name: str
    email: EmailStr


class UserUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=100)


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class SettingsOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    daily_focus_goal_min: int
    idle_threshold_sec: int
    store_window_titles: bool
    ignored_apps: list[str]
    timezone: str
    theme: str


class SettingsUpdate(BaseModel):
    """All fields optional: send only what you want to change."""

    daily_focus_goal_min: int | None = Field(default=None, ge=15, le=720)
    idle_threshold_sec: int | None = Field(default=None, ge=30, le=900)
    store_window_titles: bool | None = None
    ignored_apps: list[str] | None = Field(default=None, max_length=100)
    timezone: str | None = Field(default=None, max_length=64)
    theme: Literal["dark", "light"] | None = None
    