"""Agent settings: read from config.toml in the agent's data folder.

Windows: %APPDATA%\\AttentionAgent\\config.toml
Other:   ~/.attention-agent/config.toml

Passwords and tokens are NOT stored here (tokens go to the OS keyring, task T3.6).
"""
import os
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

APP_NAME = "AttentionAgent"
LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1"}
LOG_LEVELS = ("DEBUG", "INFO", "WARNING", "ERROR")

DEFAULT_CONFIG = """\
# Attention Agent configuration. Restart the agent after changing this file.

# Backend address. http:// is allowed only for localhost; anything else must be https://
api_base_url = "http://127.0.0.1:8000/api/v1"

# How often the agent looks at the active window (seconds, 0.1 - 60)
poll_interval_sec = 1.0

# No keyboard/mouse for this long = idle (seconds, 30 - 900)
idle_threshold_sec = 120

# How often buffered data is uploaded (seconds, 5 - 300)
sync_interval_sec = 30

# DEBUG, INFO, WARNING or ERROR
log_level = "INFO"
"""


class SettingsError(ValueError):
    """config.toml is missing something, has a typo or an unsafe value."""


@dataclass(frozen=True)
class AgentSettings:
    data_dir: Path
    api_base_url: str = "http://127.0.0.1:8000/api/v1"
    poll_interval_sec: float = 1.0
    idle_threshold_sec: int = 120
    sync_interval_sec: int = 30
    log_level: str = "INFO"

    @property
    def config_file(self) -> Path:
        return self.data_dir / "config.toml"

    @property
    def log_file(self) -> Path:
        return self.data_dir / "agent.log"

    @property
    def buffer_db(self) -> Path:
        return self.data_dir / "buffer.db"


def default_data_dir() -> Path:
    if sys.platform == "win32":
        appdata = os.environ.get("APPDATA")
        if appdata:
            return Path(appdata) / APP_NAME
    return Path.home() / ".attention-agent"


def _number(raw: dict, key: str, default, low, high, integer: bool = False):
    value = raw.get(key, default)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise SettingsError(f"{key} must be a number")
    if integer and int(value) != value:
        raise SettingsError(f"{key} must be a whole number")
    if not (low <= value <= high):
        raise SettingsError(f"{key} must be between {low} and {high}")
    return int(value) if integer else float(value)


def _check_url(url) -> str:
    if not isinstance(url, str):
        raise SettingsError("api_base_url must be text")
    parsed = urlparse(url.strip())
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        raise SettingsError("api_base_url must look like https://host/api/v1")
    if parsed.scheme == "http" and parsed.hostname not in LOCAL_HOSTS:
        raise SettingsError("api_base_url must use https:// (http is allowed only for localhost)")
    return url.strip().rstrip("/")


def load_settings(data_dir: Path | None = None) -> AgentSettings:
    """Reads config.toml (creates it with defaults on the first run)."""
    data_dir = Path(data_dir) if data_dir else default_data_dir()
    data_dir.mkdir(parents=True, exist_ok=True)
    config_file = data_dir / "config.toml"
    if not config_file.exists():
        config_file.write_text(DEFAULT_CONFIG, encoding="utf-8")

    try:
        # utf-8-sig: Windows Notepad may add an invisible BOM at the start
        raw = tomllib.loads(config_file.read_text(encoding="utf-8-sig"))
    except tomllib.TOMLDecodeError as exc:
        raise SettingsError(f"config.toml is not valid TOML: {exc}") from exc

    known = {"api_base_url", "poll_interval_sec", "idle_threshold_sec", "sync_interval_sec", "log_level"}
    unknown = sorted(set(raw) - known)
    if unknown:
        raise SettingsError(f"Unknown setting(s) in config.toml: {', '.join(unknown)}")

    level = str(raw.get("log_level", "INFO")).upper()
    if level not in LOG_LEVELS:
        raise SettingsError(f"log_level must be one of {', '.join(LOG_LEVELS)}")

    return AgentSettings(
        data_dir=data_dir,
        api_base_url=_check_url(raw.get("api_base_url", "http://127.0.0.1:8000/api/v1")),
        poll_interval_sec=_number(raw, "poll_interval_sec", 1.0, 0.1, 60),
        idle_threshold_sec=_number(raw, "idle_threshold_sec", 120, 30, 900, integer=True),
        sync_interval_sec=_number(raw, "sync_interval_sec", 30, 5, 300, integer=True),
        log_level=level,
    )
