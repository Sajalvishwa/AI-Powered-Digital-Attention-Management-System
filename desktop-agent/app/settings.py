
"""Agent settings loaded from config.toml.

Passwords and tokens are stored separately in the OS keyring.
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

# HTTP is allowed only for localhost; remote addresses must use HTTPS.
api_base_url = "http://127.0.0.1:8000/api/v1"

# How often the agent checks the foreground window (seconds, 0.1 - 60).
poll_interval_sec = 1.0

# No keyboard/mouse input for this long = idle (seconds, 30 - 900).
idle_threshold_sec = 120

# How often buffered data is uploaded (seconds, 5 - 300).
sync_interval_sec = 30

# Privacy: titles are not collected unless explicitly enabled.
store_window_titles = false

# Apps listed here are not recorded or uploaded. Matching ignores case.
# Example: ignored_apps = ["chrome.exe", "Discord.exe"]
ignored_apps = []

# DEBUG, INFO, WARNING or ERROR.
log_level = "INFO"
"""


class SettingsError(ValueError):
    """config.toml contains a typo or an unsafe/invalid value."""


@dataclass(frozen=True)
class AgentSettings:
    data_dir: Path
    api_base_url: str = "http://127.0.0.1:8000/api/v1"
    poll_interval_sec: float = 1.0
    idle_threshold_sec: int = 120
    sync_interval_sec: int = 30
    log_level: str = "INFO"
    store_window_titles: bool = False
    ignored_apps: tuple[str, ...] = ()

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
    if not low <= value <= high:
        raise SettingsError(f"{key} must be between {low} and {high}")
    return int(value) if integer else float(value)


def _check_url(url) -> str:
    if not isinstance(url, str):
        raise SettingsError("api_base_url must be text")
    parsed = urlparse(url.strip())
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        raise SettingsError("api_base_url must look like https://host/api/v1")
    if parsed.scheme == "http" and parsed.hostname not in LOCAL_HOSTS:
        raise SettingsError(
            "api_base_url must use https:// (http is allowed only for localhost)"
        )
    return url.strip().rstrip("/")


def _check_privacy_settings(raw: dict) -> tuple[bool, tuple[str, ...]]:
    store_titles = raw.get("store_window_titles", False)
    if not isinstance(store_titles, bool):
        raise SettingsError("store_window_titles must be true or false")

    ignored = raw.get("ignored_apps", [])
    if not isinstance(ignored, list):
        raise SettingsError("ignored_apps must be a list of application names")

    cleaned = []
    seen = set()
    for app in ignored:
        if not isinstance(app, str) or not app.strip():
            raise SettingsError("ignored_apps must contain non-empty text values")
        name = app.strip()
        if "\x00" in name:
            raise SettingsError("ignored_apps cannot contain null characters")
        if name.casefold() not in seen:
            cleaned.append(name)
            seen.add(name.casefold())

    return store_titles, tuple(cleaned)


def load_settings(data_dir: Path | None = None) -> AgentSettings:
    """Read config.toml, creating it with safe defaults on first run."""
    data_dir = Path(data_dir) if data_dir else default_data_dir()
    data_dir.mkdir(parents=True, exist_ok=True)
    config_file = data_dir / "config.toml"

    if not config_file.exists():
        config_file.write_text(DEFAULT_CONFIG, encoding="utf-8")

    try:
        raw = tomllib.loads(config_file.read_text(encoding="utf-8-sig"))
    except tomllib.TOMLDecodeError as exc:
        raise SettingsError(f"config.toml is not valid TOML: {exc}") from exc

    known = {
        "api_base_url",
        "poll_interval_sec",
        "idle_threshold_sec",
        "sync_interval_sec",
        "log_level",
        "store_window_titles",
        "ignored_apps",
    }
    unknown = sorted(set(raw) - known)
    if unknown:
        raise SettingsError(
            f"Unknown setting(s) in config.toml: {', '.join(unknown)}"
        )

    level = raw.get("log_level", "INFO")
    if not isinstance(level, str):
        raise SettingsError(f"log_level must be one of {', '.join(LOG_LEVELS)}")
    level = level.upper()
    if level not in LOG_LEVELS:
        raise SettingsError(f"log_level must be one of {', '.join(LOG_LEVELS)}")

    store_titles, ignored_apps = _check_privacy_settings(raw)

    return AgentSettings(
        data_dir=data_dir,
        api_base_url=_check_url(
            raw.get("api_base_url", "http://127.0.0.1:8000/api/v1")
        ),
        poll_interval_sec=_number(raw, "poll_interval_sec", 1.0, 0.1, 60),
        idle_threshold_sec=_number(
            raw, "idle_threshold_sec", 120, 30, 900, integer=True
        ),
        sync_interval_sec=_number(
            raw, "sync_interval_sec", 30, 5, 300, integer=True
        ),
        log_level=level,
        store_window_titles=store_titles,
        ignored_apps=ignored_apps,
    )
