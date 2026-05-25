"""Pydantic input models for the v1 MCP tool surface."""

from __future__ import annotations

import math
import os
import re
from typing import Annotated, Any, Literal, TypeVar

from pydantic import (
    AfterValidator,
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    StrictBool,
    ValidationError,
    field_validator,
)

from .errors import VALIDATION_ERROR, ToolFailure

IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,63}$")
GEOMETRY_IDENTIFIER_RE = re.compile(r"^g[0-9]+$")


def _non_empty_string(value: str) -> str:
    if not value.strip():
        raise ValueError("must be a non-empty string")
    return value


def _safe_identifier(value: str) -> str:
    if not IDENTIFIER_RE.match(value):
        raise ValueError("must be a simple identifier")
    return value


def _geometry_identifier(value: str) -> str:
    if not GEOMETRY_IDENTIFIER_RE.match(value):
        raise ValueError("must look like g0")
    return value


def _finite_number(value: Any) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float) or not math.isfinite(value):
        raise ValueError("must be a finite number")
    return float(value)


NonEmptyString = Annotated[str, AfterValidator(_non_empty_string)]
SafeIdentifier = Annotated[NonEmptyString, AfterValidator(_safe_identifier)]
GeometryIdentifier = Annotated[NonEmptyString, AfterValidator(_geometry_identifier)]
FiniteNumber = Annotated[float, BeforeValidator(_finite_number)]
PositiveNumber = Annotated[FiniteNumber, Field(gt=0)]
Point2 = tuple[FiniteNumber, FiniteNumber]
Point3 = tuple[FiniteNumber, FiniteNumber, FiniteNumber]


class ToolInput(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class GetActiveDocumentInput(ToolInput):
    pass


class GetSelectionInput(ToolInput):
    pass


class CreateDocumentInput(ToolInput):
    name: SafeIdentifier | None = None


class DocumentInput(ToolInput):
    document: NonEmptyString | None = None


class SaveDocumentInput(DocumentInput):
    path: NonEmptyString

    @field_validator("path")
    @classmethod
    def validate_path(cls, value: str) -> str:
        return _absolute_path(value, field="path", suffixes=(".fcstd",))


class CreateBodyInput(DocumentInput):
    label: NonEmptyString = "Body"


class PlacementInput(ToolInput):
    position_mm: Point3 = (0.0, 0.0, 0.0)
    rotation_degrees: Point3 = (0.0, 0.0, 0.0)


class AddBoxInput(DocumentInput):
    label: NonEmptyString = "Box"
    length_mm: PositiveNumber
    width_mm: PositiveNumber
    height_mm: PositiveNumber
    placement: PlacementInput | None = None


class AddCylinderInput(DocumentInput):
    label: NonEmptyString = "Cylinder"
    radius_mm: PositiveNumber
    height_mm: PositiveNumber
    placement: PlacementInput | None = None


class SketchSupportInput(ToolInput):
    mode: Literal["plane", "selection"] = "plane"
    plane: Literal["XY", "XZ", "YZ"] = "XY"


class CreateSketchInput(DocumentInput):
    label: NonEmptyString = "Sketch"
    support: SketchSupportInput = Field(default_factory=SketchSupportInput)


class LineGeometryInput(ToolInput):
    type: Literal["line"]
    start_mm: Point2
    end_mm: Point2
    construction: StrictBool = False


class RectangleGeometryInput(ToolInput):
    type: Literal["rectangle"]
    origin_mm: Point2
    width_mm: PositiveNumber
    height_mm: PositiveNumber
    construction: StrictBool = False


class CircleGeometryInput(ToolInput):
    type: Literal["circle"]
    center_mm: Point2
    radius_mm: PositiveNumber
    construction: StrictBool = False


class ArcGeometryInput(ToolInput):
    type: Literal["arc"]
    center_mm: Point2
    radius_mm: PositiveNumber
    start_degrees: FiniteNumber
    end_degrees: FiniteNumber
    construction: StrictBool = False


SketchGeometryInput = Annotated[
    LineGeometryInput | RectangleGeometryInput | CircleGeometryInput | ArcGeometryInput,
    Field(discriminator="type"),
]


class AddSketchGeometryInput(DocumentInput):
    sketch: NonEmptyString
    geometry: list[SketchGeometryInput]


class SimpleConstraintInput(ToolInput):
    type: Literal["horizontal", "vertical"]
    geometry: GeometryIdentifier


class ValueConstraintInput(ToolInput):
    type: Literal["distance", "distance_x", "distance_y", "radius", "diameter"]
    geometry: GeometryIdentifier
    value_mm: PositiveNumber


class EqualConstraintInput(ToolInput):
    type: Literal["equal"]
    geometry: GeometryIdentifier
    other_geometry: GeometryIdentifier


class CoincidentConstraintInput(ToolInput):
    type: Literal["coincident"]
    geometry: GeometryIdentifier
    other_geometry: GeometryIdentifier
    point: int = 1
    other_point: int = 1


class SymmetricConstraintInput(ToolInput):
    type: Literal["symmetric"]
    geometry: GeometryIdentifier
    other_geometry: GeometryIdentifier
    axis_geometry: GeometryIdentifier


SketchConstraintInput = Annotated[
    SimpleConstraintInput
    | ValueConstraintInput
    | EqualConstraintInput
    | CoincidentConstraintInput
    | SymmetricConstraintInput,
    Field(discriminator="type"),
]


class AddSketchConstraintInput(DocumentInput):
    sketch: NonEmptyString
    constraints: list[SketchConstraintInput]


class SolveSketchInput(DocumentInput):
    sketch: NonEmptyString


class PadSketchInput(SolveSketchInput):
    length_mm: PositiveNumber
    symmetric: StrictBool = False


class FilletEdgesInput(DocumentInput):
    object: NonEmptyString
    edges: list[NonEmptyString] | None = None
    radius_mm: PositiveNumber


class BooleanOperationInput(DocumentInput):
    operation: Literal["union", "intersection", "difference"]
    objects: list[NonEmptyString] | None = None
    label: NonEmptyString = "Boolean"


class SetPropertyInput(DocumentInput):
    object: NonEmptyString
    property: NonEmptyString
    value: Any = None


class StringValueInput(ToolInput):
    value: NonEmptyString


class PositiveValueInput(ToolInput):
    value: PositiveNumber


class PlacementValueInput(ToolInput):
    value: PlacementInput


class ExportStepInput(DocumentInput):
    objects: list[NonEmptyString] | None = None
    path: NonEmptyString

    @field_validator("path")
    @classmethod
    def validate_path(cls, value: str) -> str:
        return _absolute_path(value, field="path", suffixes=(".step", ".stp"))


class ExportStlInput(DocumentInput):
    objects: list[NonEmptyString] | None = None
    path: NonEmptyString
    linear_deflection: PositiveNumber | None = None
    angular_deflection: PositiveNumber | None = None

    @field_validator("path")
    @classmethod
    def validate_path(cls, value: str) -> str:
        return _absolute_path(value, field="path", suffixes=(".stl",))


ToolInputT = TypeVar("ToolInputT", bound=ToolInput)

TOOL_INPUT_MODELS: dict[str, type[ToolInput]] = {
    "get_active_document": GetActiveDocumentInput,
    "get_selection": GetSelectionInput,
    "create_document": CreateDocumentInput,
    "recompute": DocumentInput,
    "save_document": SaveDocumentInput,
    "create_body": CreateBodyInput,
    "add_box": AddBoxInput,
    "add_cylinder": AddCylinderInput,
    "create_sketch": CreateSketchInput,
    "add_sketch_geometry": AddSketchGeometryInput,
    "add_sketch_constraint": AddSketchConstraintInput,
    "solve_sketch": SolveSketchInput,
    "pad_sketch": PadSketchInput,
    "fillet_edges": FilletEdgesInput,
    "boolean_operation": BooleanOperationInput,
    "set_property": SetPropertyInput,
    "export_step": ExportStepInput,
    "export_stl": ExportStlInput,
}


def _absolute_path(value: str, *, field: str, suffixes: tuple[str, ...]) -> str:
    if not os.path.isabs(value):
        raise ValueError(f"{field} must be an absolute path")
    if not value.lower().endswith(suffixes):
        allowed = ", ".join(suffixes)
        raise ValueError(f"{field} must end with {allowed}")
    return value


def validate_input(model: type[ToolInputT], data: dict[str, Any]) -> ToolInputT:
    try:
        return model.model_validate(data)
    except ValidationError as exc:
        errors = [
            {
                "field": ".".join(str(part) for part in error["loc"]),
                "message": error["msg"],
                "type": error["type"],
            }
            for error in exc.errors()
        ]
        first = errors[0] if errors else {"field": "input", "message": "Invalid input"}
        field = first["field"] or "input"
        raise ToolFailure(VALIDATION_ERROR, f"{field}: {first['message']}", {"errors": errors}) from exc
