"""
AcaDesk Structured Logger
==========================
Provides a rotating file logger for all logic modules.
Never logs passwords, secrets, or raw credentials.

Usage:
    from logic.logger import get_logger
    log = get_logger(__name__)
    log.info("Something happened")
    log.warning("Non-critical issue")
    log.error("Something failed")
"""

import logging
import os
import sys
import pathlib
from logging.handlers import RotatingFileHandler

_LOGGERS: dict[str, logging.Logger] = {}

def _get_log_path() -> str:
    """Resolve log file path relative to the project root."""
    if getattr(sys, 'frozen', False):
        base = pathlib.Path(sys.executable).parent
    else:
        base = pathlib.Path(__file__).parent.parent
    return str(base / "acadesk.log")


def get_logger(name: str) -> logging.Logger:
    """
    Return a named logger with rotating file handler.
    Reuses existing loggers to avoid duplicate handlers.
    Log level is INFO by default; set ACADESK_LOG_LEVEL=DEBUG for verbose output.
    """
    if name in _LOGGERS:
        return _LOGGERS[name]

    logger = logging.getLogger(name)
    if logger.handlers:
        _LOGGERS[name] = logger
        return logger

    level_name = os.environ.get("ACADESK_LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)
    logger.setLevel(level)

    # Rotating file: max 5 MB per file, keep 3 backups
    try:
        fh = RotatingFileHandler(
            _get_log_path(),
            maxBytes=5 * 1024 * 1024,
            backupCount=3,
            encoding="utf-8",
        )
        fh.setFormatter(logging.Formatter(
            "%(asctime)s [%(levelname)-8s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        ))
        logger.addHandler(fh)
    except OSError:
        # If log file is not writable (e.g., read-only packaged path), use NullHandler
        logger.addHandler(logging.NullHandler())

    # Also stream WARNING+ to console during development
    if level <= logging.DEBUG:
        ch = logging.StreamHandler(sys.stderr)
        ch.setLevel(logging.WARNING)
        ch.setFormatter(logging.Formatter("[%(levelname)s] %(name)s: %(message)s"))
        logger.addHandler(ch)

    logger.propagate = False
    _LOGGERS[name] = logger
    return logger
