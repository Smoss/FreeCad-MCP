"""Workbench logging setup."""

from __future__ import annotations

import logging
from pathlib import Path

LOGGER_NAME = "freecad_mcp_workbench"


def log_dir() -> Path:
    return Path.home() / ".freecad_mcp_workbench" / "logs"


def log_path() -> Path:
    return log_dir() / "workbench.log"


def get_logger() -> logging.Logger:
    logger = logging.getLogger(LOGGER_NAME)
    if logger.handlers:
        return logger
    log_dir().mkdir(parents=True, exist_ok=True)
    handler = logging.FileHandler(log_path(), encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    return logger
