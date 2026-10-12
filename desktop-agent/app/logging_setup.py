"""File + console logging. Secrets are masked as a safety net.

Rule (docs/security.md): never log passwords, tokens or window titles.
The masking below is only a backup - do not pass such values to the logger at all.
"""
import logging
import re
from logging.handlers import RotatingFileHandler

from app.settings import AgentSettings

LOGGER_NAME = "attention_agent"

_PATTERNS = [
    (re.compile(r"(?i)(bearer\s+)[A-Za-z0-9._~+/=-]+"), r"\1***"),
    (
        re.compile(
            r"(?i)((?:password|passwd|secret|token|refresh_token|access_token)[\"']?\s*[:=]\s*[\"']?)"
            r"[^\s\"',}&]+"
        ),
        r"\1***",
    ),
]


def redact(text: str) -> str:
    for pattern, replacement in _PATTERNS:
        text = pattern.sub(replacement, text)
    return text


class RedactFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = redact(record.getMessage())
        record.args = ()
        return True


def close_logging() -> None:
    """Close handlers (releases agent.log - important on Windows)."""
    logger = logging.getLogger(LOGGER_NAME)
    for handler in list(logger.handlers):
        handler.close()
        logger.removeHandler(handler)


def setup_logging(settings: AgentSettings, console: bool = True) -> logging.Logger:
    close_logging()  # safe to call more than once
    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(getattr(logging, settings.log_level))
    logger.propagate = False

    fmt = logging.Formatter("%(asctime)s %(levelname)-7s %(message)s")
    file_handler = RotatingFileHandler(
        settings.log_file, maxBytes=1_000_000, backupCount=3, encoding="utf-8"
    )
    handlers: list[logging.Handler] = [file_handler]
    if console:
        handlers.append(logging.StreamHandler())
    for handler in handlers:
        handler.setFormatter(fmt)
        handler.addFilter(RedactFilter())
        logger.addHandler(handler)
    return logger
