from datetime import date

from pydantic import BaseModel


class AppUsage(BaseModel):
    app_name: str
    total_sec: int
    sessions: int


class HourBucket(BaseModel):
    hour: int  # 0-23 in the user's timezone
    active_sec: int
    idle_sec: int


class DayBucket(BaseModel):
    day: date
    active_sec: int
    idle_sec: int


class StatsCommon(BaseModel):
    screen_time_sec: int  # non-idle time
    idle_sec: int
    focus_sec: int  # non-idle time that happened inside focus sessions
    task_switches: int  # non-idle sessions minus 1
    top_apps: list[AppUsage]


class TodayStatsOut(StatsCommon):
    day: date
    timezone: str
    timeline: list[HourBucket]


class RangeStatsOut(StatsCommon):
    from_day: date
    to_day: date
    timezone: str
    daily: list[DayBucket]
