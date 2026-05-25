"""JSON-compatible input schema registry for the v1 tool surface."""

from __future__ import annotations

from typing import Any

from .models import TOOL_INPUT_MODELS

TOOL_SCHEMAS: dict[str, dict[str, Any]] = {
    name: model.model_json_schema(mode="validation") for name, model in TOOL_INPUT_MODELS.items()
}


def schema_for_tool(name: str) -> dict[str, Any]:
    return TOOL_SCHEMAS[name]
