"""Structured tool result and error helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


VALIDATION_ERROR = "validation_error"
NO_ACTIVE_DOCUMENT = "no_active_document"
DOCUMENT_NOT_FOUND = "document_not_found"
OBJECT_NOT_FOUND = "object_not_found"
SELECTION_ERROR = "selection_error"
UNSUPPORTED_OPERATION = "unsupported_operation"
FREECAD_ERROR = "freecad_error"
RECOMPUTE_FAILED = "recompute_failed"
EXPORT_FAILED = "export_failed"
DEPENDENCY_MISSING = "dependency_missing"


@dataclass
class ToolFailure(Exception):
    code: str
    message: str
    details: dict[str, Any] | None = None

    def to_result(self) -> dict[str, Any]:
        return error(self.code, self.message, self.details or {})


def ok(data: dict[str, Any] | None = None) -> dict[str, Any]:
    return {"ok": True, "data": data or {}}


def error(code: str, message: str, details: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "ok": False,
        "error": {
            "code": code,
            "message": message,
            "details": details or {},
        },
    }


def result_from_exception(exc: Exception) -> dict[str, Any]:
    if isinstance(exc, ToolFailure):
        return exc.to_result()
    return error(FREECAD_ERROR, str(exc), {"type": exc.__class__.__name__})

