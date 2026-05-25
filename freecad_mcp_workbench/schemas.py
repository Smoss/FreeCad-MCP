"""JSON-compatible input schema registry for the v1 tool surface."""

from __future__ import annotations

from typing import Any

OBJECT = {"type": "object", "additionalProperties": False}
STRING = {"type": "string", "minLength": 1}
NUMBER = {"type": "number"}
POSITIVE = {"type": "number", "exclusiveMinimum": 0}
PLACEMENT = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "position_mm": {"type": "array", "items": NUMBER, "minItems": 3, "maxItems": 3},
        "rotation_degrees": {"type": "array", "items": NUMBER, "minItems": 3, "maxItems": 3},
    },
}


TOOL_SCHEMAS: dict[str, dict[str, Any]] = {
    "get_active_document": {**OBJECT, "properties": {}},
    "get_selection": {**OBJECT, "properties": {}},
    "create_document": {**OBJECT, "properties": {"name": STRING}},
    "recompute": {**OBJECT, "properties": {"document": STRING}},
    "save_document": {**OBJECT, "required": ["path"], "properties": {"document": STRING, "path": STRING}},
    "create_body": {**OBJECT, "properties": {"document": STRING, "label": STRING}},
    "add_box": {
        **OBJECT,
        "required": ["length_mm", "width_mm", "height_mm"],
        "properties": {"document": STRING, "label": STRING, "length_mm": POSITIVE, "width_mm": POSITIVE, "height_mm": POSITIVE, "placement": PLACEMENT},
    },
    "add_cylinder": {
        **OBJECT,
        "required": ["radius_mm", "height_mm"],
        "properties": {"document": STRING, "label": STRING, "radius_mm": POSITIVE, "height_mm": POSITIVE, "placement": PLACEMENT},
    },
    "create_sketch": {
        **OBJECT,
        "properties": {
            "document": STRING,
            "label": STRING,
            "support": {
                "type": "object",
                "properties": {"mode": {"type": "string", "enum": ["plane", "selection"]}, "plane": {"type": "string", "enum": ["XY", "XZ", "YZ"]}},
            },
        },
    },
    "add_sketch_geometry": {
        **OBJECT,
        "required": ["sketch", "geometry"],
        "properties": {"document": STRING, "sketch": STRING, "geometry": {"type": "array", "items": {"type": "object"}}},
    },
    "add_sketch_constraint": {
        **OBJECT,
        "required": ["sketch", "constraints"],
        "properties": {"document": STRING, "sketch": STRING, "constraints": {"type": "array", "items": {"type": "object"}}},
    },
    "solve_sketch": {**OBJECT, "required": ["sketch"], "properties": {"document": STRING, "sketch": STRING}},
    "pad_sketch": {**OBJECT, "required": ["sketch", "length_mm"], "properties": {"document": STRING, "sketch": STRING, "length_mm": POSITIVE, "symmetric": {"type": "boolean"}}},
    "fillet_edges": {
        **OBJECT,
        "required": ["object", "radius_mm"],
        "properties": {"document": STRING, "object": STRING, "edges": {"type": "array", "items": STRING}, "radius_mm": POSITIVE},
    },
    "boolean_operation": {
        **OBJECT,
        "required": ["operation"],
        "properties": {
            "document": STRING,
            "operation": {"type": "string", "enum": ["union", "intersection", "difference"]},
            "objects": {"type": "array", "items": STRING, "minItems": 2},
            "label": STRING,
        },
    },
    "set_property": {
        **OBJECT,
        "required": ["object", "property", "value"],
        "properties": {"document": STRING, "object": STRING, "property": STRING, "value": {}},
    },
    "export_step": {
        **OBJECT,
        "required": ["path"],
        "properties": {"document": STRING, "objects": {"type": "array", "items": STRING}, "path": STRING},
    },
    "export_stl": {
        **OBJECT,
        "required": ["path"],
        "properties": {
            "document": STRING,
            "objects": {"type": "array", "items": STRING},
            "path": STRING,
            "linear_deflection": POSITIVE,
            "angular_deflection": POSITIVE,
        },
    },
}


def schema_for_tool(name: str) -> dict[str, Any]:
    return TOOL_SCHEMAS[name]
