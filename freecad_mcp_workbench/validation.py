"""Small validation helpers for JSON-compatible MCP inputs."""

from __future__ import annotations

import math
import os
import re
from typing import Any

from .errors import ToolFailure, VALIDATION_ERROR

IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,63}$")


def optional_document_name(value: Any, *, field: str = "document") -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise ToolFailure(VALIDATION_ERROR, f"{field} must be a non-empty string")
    return value


def document_safe_name(value: Any, *, field: str = "name") -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not IDENTIFIER_RE.match(value):
        raise ToolFailure(VALIDATION_ERROR, f"{field} must be a simple identifier")
    return value


def non_empty_string(value: Any, *, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ToolFailure(VALIDATION_ERROR, f"{field} must be a non-empty string")
    return value


def finite_number(value: Any, *, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ToolFailure(VALIDATION_ERROR, f"{field} must be a finite number")
    return float(value)


def positive_number(value: Any, *, field: str) -> float:
    number = finite_number(value, field=field)
    if number <= 0:
        raise ToolFailure(VALIDATION_ERROR, f"{field} must be positive")
    return number


def optional_bool(value: Any, *, field: str, default: bool = False) -> bool:
    if value is None:
        return default
    if not isinstance(value, bool):
        raise ToolFailure(VALIDATION_ERROR, f"{field} must be a boolean")
    return value


def point2(value: Any, *, field: str) -> tuple[float, float]:
    if not isinstance(value, list | tuple) or len(value) != 2:
        raise ToolFailure(VALIDATION_ERROR, f"{field} must be a 2 item coordinate")
    return finite_number(value[0], field=f"{field}[0]"), finite_number(value[1], field=f"{field}[1]")


def point3(value: Any, *, field: str) -> tuple[float, float, float]:
    if not isinstance(value, list | tuple) or len(value) != 3:
        raise ToolFailure(VALIDATION_ERROR, f"{field} must be a 3 item coordinate")
    return (
        finite_number(value[0], field=f"{field}[0]"),
        finite_number(value[1], field=f"{field}[1]"),
        finite_number(value[2], field=f"{field}[2]"),
    )


def absolute_path(value: Any, *, field: str, suffixes: tuple[str, ...]) -> str:
    path = non_empty_string(value, field=field)
    if not os.path.isabs(path):
        raise ToolFailure(VALIDATION_ERROR, f"{field} must be an absolute path")
    if not path.lower().endswith(suffixes):
        allowed = ", ".join(suffixes)
        raise ToolFailure(VALIDATION_ERROR, f"{field} must end with {allowed}")
    return path


def ensure_mapping(value: Any, *, field: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ToolFailure(VALIDATION_ERROR, f"{field} must be an object")
    return value


def ensure_list(value: Any, *, field: str) -> list[Any]:
    if not isinstance(value, list):
        raise ToolFailure(VALIDATION_ERROR, f"{field} must be a list")
    return value

