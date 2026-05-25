"""V1 MCP tool handlers for FreeCAD."""

from __future__ import annotations

import os
from functools import wraps
from typing import Any

from . import freecad_api as fcapi
from . import models
from .errors import (
    EXPORT_FAILED,
    RECOMPUTE_FAILED,
    SELECTION_ERROR,
    UNSUPPORTED_OPERATION,
    ToolFailure,
    ok,
    result_from_exception,
)


def _wrap(func):
    @wraps(func)
    def inner(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as exc:
            return result_from_exception(exc)

    return inner


def _doc(document: str | None = None):
    params = models.validate_input(models.DocumentInput, {"document": document})
    return fcapi.get_document(params.document)


def _document_state(doc) -> dict[str, Any]:
    return {
        "document": fcapi.document_summary(doc),
        "objects": [fcapi.object_summary(obj) for obj in getattr(doc, "Objects", [])],
        "active_body": fcapi.active_body_name(),
        "active_sketch": fcapi.active_sketch_name(),
    }


def _created_object_data(obj, doc) -> dict[str, Any]:
    data = {"object": fcapi.object_ref(obj, doc)}
    bbox = fcapi.bounding_box(obj)
    if bbox is not None:
        data["bounding_box"] = bbox
    return data


_BOOLEAN_OPERATIONS = {"union", "intersection", "difference"}


@_wrap
def get_active_document() -> dict[str, Any]:
    document = getattr(fcapi.app(), "ActiveDocument", None)
    if document is None:
        return ok({"document": None, "objects": [], "active_body": None, "active_sketch": None})
    return ok(_document_state(document))


@_wrap
def get_selection() -> dict[str, Any]:
    gui = fcapi.gui()
    if gui is None or not hasattr(gui, "Selection"):
        return ok({"selection": []})
    entries = []
    for selected in gui.Selection.getSelectionEx():
        obj = getattr(selected, "Object", None)
        entries.append(
            {
                "document": getattr(getattr(obj, "Document", None), "Name", None),
                "object": getattr(obj, "Name", None),
                "label": getattr(obj, "Label", None),
                "type": getattr(obj, "TypeId", None),
                "subelements": list(getattr(selected, "SubElementNames", []) or []),
            }
        )
    return ok({"selection": entries})


@_wrap
def create_document(name: str | None = None) -> dict[str, Any]:
    params = models.validate_input(models.CreateDocumentInput, {"name": name})
    fc = fcapi.app()
    doc = fc.newDocument(params.name) if params.name else fc.newDocument()
    if hasattr(fc, "setActiveDocument"):
        fc.setActiveDocument(doc.Name)
    return ok({"document": fcapi.document_summary(doc)})


@_wrap
def recompute(document: str | None = None) -> dict[str, Any]:
    params = models.validate_input(models.DocumentInput, {"document": document})
    doc = _doc(params.document)
    try:
        return ok(fcapi.recompute_document(doc))
    except Exception as exc:
        raise ToolFailure(RECOMPUTE_FAILED, str(exc), {"document": getattr(doc, "Name", None)}) from exc


@_wrap
def save_document(document: str | None = None, path: str | None = None) -> dict[str, Any]:
    params = models.validate_input(models.SaveDocumentInput, {"document": document, "path": path})
    doc = _doc(params.document)
    target = params.path
    os.makedirs(os.path.dirname(target), exist_ok=True)
    doc.saveAs(target)
    return ok({"path": target, "document": fcapi.document_summary(doc)})


@_wrap
def create_body(document: str | None = None, label: str = "Body") -> dict[str, Any]:
    params = models.validate_input(models.CreateBodyInput, {"document": document, "label": label})
    doc = _doc(params.document)
    body = doc.addObject("PartDesign::Body", params.label)
    gui = fcapi.gui()
    if gui is not None and hasattr(gui, "activeDocument"):
        active = gui.activeDocument()
        if active is not None and hasattr(active, "setEdit"):
            try:
                active.setEdit(body.Name)
            except Exception:
                pass
    return ok({"object": fcapi.object_ref(body, doc)})


@_wrap
def add_box(
    document: str | None = None,
    label: str = "Box",
    length_mm: float | None = None,
    width_mm: float | None = None,
    height_mm: float | None = None,
    placement: dict[str, Any] | None = None,
) -> dict[str, Any]:
    params = models.validate_input(
        models.AddBoxInput,
        {
            "document": document,
            "label": label,
            "length_mm": length_mm,
            "width_mm": width_mm,
            "height_mm": height_mm,
            "placement": placement,
        },
    )
    doc = _doc(params.document)
    obj = doc.addObject("Part::Box", params.label)
    obj.Length = params.length_mm
    obj.Width = params.width_mm
    obj.Height = params.height_mm
    fcapi.apply_placement(obj, params.placement)
    doc.recompute()
    return ok(_created_object_data(obj, doc))


@_wrap
def add_cylinder(
    document: str | None = None,
    label: str = "Cylinder",
    radius_mm: float | None = None,
    height_mm: float | None = None,
    placement: dict[str, Any] | None = None,
) -> dict[str, Any]:
    params = models.validate_input(
        models.AddCylinderInput,
        {
            "document": document,
            "label": label,
            "radius_mm": radius_mm,
            "height_mm": height_mm,
            "placement": placement,
        },
    )
    doc = _doc(params.document)
    obj = doc.addObject("Part::Cylinder", params.label)
    obj.Radius = params.radius_mm
    obj.Height = params.height_mm
    fcapi.apply_placement(obj, params.placement)
    doc.recompute()
    return ok(_created_object_data(obj, doc))


@_wrap
def create_sketch(
    document: str | None = None, label: str = "Sketch", support: dict[str, Any] | None = None
) -> dict[str, Any]:
    input_data: dict[str, Any] = {"document": document, "label": label}
    if support is not None:
        input_data["support"] = support
    params = models.validate_input(models.CreateSketchInput, input_data)
    doc = _doc(params.document)
    sketch = doc.addObject("Sketcher::SketchObject", params.label)
    if params.support.mode == "plane":
        plane = params.support.plane
        if plane == "XZ":
            sketch.Placement = fcapi.make_placement((0, 0, 0), (0, 90, 0))
        elif plane == "YZ":
            sketch.Placement = fcapi.make_placement((0, 0, 0), (90, 0, 0))
    elif params.support.mode == "selection":
        gui = fcapi.gui()
        selection = gui.Selection.getSelectionEx() if gui and hasattr(gui, "Selection") else []
        if len(selection) != 1 or len(getattr(selection[0], "SubElementNames", []) or []) != 1:
            raise ToolFailure(SELECTION_ERROR, "Selection support requires exactly one selected planar face")
        selected = selection[0]
        sketch.Support = [(selected.Object, selected.SubElementNames[0])]
        sketch.MapMode = "FlatFace"
    doc.recompute()
    return ok(
        {"object": fcapi.object_ref(sketch, doc), "local_transform": fcapi.placement_to_transform(sketch.Placement)}
    )


def _geometry_count(sketch) -> int:
    return len(getattr(sketch, "Geometry", []) or [])


@_wrap
def add_sketch_geometry(
    document: str | None = None, sketch: str | None = None, geometry: list[dict[str, Any]] | None = None
) -> dict[str, Any]:
    params = models.validate_input(
        models.AddSketchGeometryInput, {"document": document, "sketch": sketch, "geometry": geometry}
    )
    doc = _doc(params.document)
    sketch_obj = fcapi.find_object(doc, params.sketch)
    part = fcapi.part()
    freecad = fcapi.app()
    created: list[dict[str, Any]] = []
    for item in params.geometry:
        if isinstance(item, models.LineGeometryInput):
            start = item.start_mm
            end = item.end_mm
            geom = part.LineSegment(freecad.Vector(start[0], start[1], 0), freecad.Vector(end[0], end[1], 0))
            index = sketch_obj.addGeometry(geom, item.construction)
            created.append({"id": f"g{index}", "type": "line"})
        elif isinstance(item, models.RectangleGeometryInput):
            origin = item.origin_mm
            width = item.width_mm
            height = item.height_mm
            x, y = origin
            corners = [(x, y), (x + width, y), (x + width, y + height), (x, y + height)]
            ids = []
            for start, end in zip(corners, corners[1:] + corners[:1], strict=False):
                geom = part.LineSegment(freecad.Vector(start[0], start[1], 0), freecad.Vector(end[0], end[1], 0))
                ids.append(f"g{sketch_obj.addGeometry(geom, item.construction)}")
            created.append({"ids": ids, "type": "rectangle"})
        elif isinstance(item, models.CircleGeometryInput):
            center = item.center_mm
            radius = item.radius_mm
            geom = part.Circle(freecad.Vector(center[0], center[1], 0), freecad.Vector(0, 0, 1), radius)
            index = sketch_obj.addGeometry(geom, item.construction)
            created.append({"id": f"g{index}", "type": "circle"})
        elif isinstance(item, models.ArcGeometryInput):
            center = item.center_mm
            radius = item.radius_mm
            circle = part.Circle(freecad.Vector(center[0], center[1], 0), freecad.Vector(0, 0, 1), radius)
            geom = part.ArcOfCircle(circle, item.start_degrees, item.end_degrees)
            index = sketch_obj.addGeometry(geom, item.construction)
            created.append({"id": f"g{index}", "type": "arc"})
    return ok(
        {
            "sketch": fcapi.object_ref(sketch_obj, doc),
            "geometry": created,
            "geometry_count": _geometry_count(sketch_obj),
        }
    )


def _geometry_index(identifier: str) -> int:
    return int(identifier[1:])


@_wrap
def add_sketch_constraint(
    document: str | None = None, sketch: str | None = None, constraints: list[dict[str, Any]] | None = None
) -> dict[str, Any]:
    params = models.validate_input(
        models.AddSketchConstraintInput,
        {"document": document, "sketch": sketch, "constraints": constraints},
    )
    doc = _doc(params.document)
    sketch_obj = fcapi.find_object(doc, params.sketch)
    sketcher = fcapi.sketcher()
    created = []
    mapping = {
        "horizontal": "Horizontal",
        "vertical": "Vertical",
        "distance": "Distance",
        "distance_x": "DistanceX",
        "distance_y": "DistanceY",
        "radius": "Radius",
        "diameter": "Diameter",
        "equal": "Equal",
        "coincident": "Coincident",
        "symmetric": "Symmetric",
    }
    for item in params.constraints:
        kind = item.type
        geo = _geometry_index(item.geometry)
        if isinstance(item, models.ValueConstraintInput):
            constraint = sketcher.Constraint(mapping[kind], geo, item.value_mm)
        elif isinstance(item, models.EqualConstraintInput):
            other = _geometry_index(item.other_geometry)
            constraint = sketcher.Constraint("Equal", geo, other)
        elif isinstance(item, models.CoincidentConstraintInput):
            other = _geometry_index(item.other_geometry)
            constraint = sketcher.Constraint("Coincident", geo, item.point, other, item.other_point)
        elif isinstance(item, models.SymmetricConstraintInput):
            other = _geometry_index(item.other_geometry)
            axis = _geometry_index(item.axis_geometry)
            constraint = sketcher.Constraint("Symmetric", geo, other, axis)
        else:
            constraint = sketcher.Constraint(mapping[kind], geo)
        index = sketch_obj.addConstraint(constraint)
        created.append({"id": f"c{index}", "type": kind})
    doc.recompute()
    return ok({"constraints": created, "solver": _solver_state(sketch_obj)})


def _solver_state(sketch_obj) -> dict[str, Any]:
    dof = getattr(sketch_obj, "SolverReturn", None)
    status = "unknown"
    if hasattr(sketch_obj, "solve"):
        result = sketch_obj.solve()
        if result == 0:
            status = "solved"
        elif isinstance(result, int) and result > 0:
            status = "underconstrained"
        else:
            status = "conflicting"
    return {
        "status": status,
        "degrees_of_freedom": dof,
        "conflicts": list(getattr(sketch_obj, "ConflictingConstraints", []) or []),
    }


@_wrap
def solve_sketch(document: str | None = None, sketch: str | None = None) -> dict[str, Any]:
    params = models.validate_input(models.SolveSketchInput, {"document": document, "sketch": sketch})
    doc = _doc(params.document)
    sketch_obj = fcapi.find_object(doc, params.sketch)
    doc.recompute()
    return ok({"sketch": fcapi.object_ref(sketch_obj, doc), "solver": _solver_state(sketch_obj)})


@_wrap
def pad_sketch(
    document: str | None = None, sketch: str | None = None, length_mm: float | None = None, symmetric: bool = False
) -> dict[str, Any]:
    params = models.validate_input(
        models.PadSketchInput,
        {"document": document, "sketch": sketch, "length_mm": length_mm, "symmetric": symmetric},
    )
    doc = _doc(params.document)
    sketch_obj = fcapi.find_object(doc, params.sketch)
    parent = getattr(sketch_obj, "InList", [None])[0] if getattr(sketch_obj, "InList", []) else None
    if parent is not None and getattr(parent, "TypeId", "") == "PartDesign::Body":
        pad = doc.addObject("PartDesign::Pad", "Pad")
        if hasattr(parent, "addObject"):
            parent.addObject(pad)
        pad.Profile = sketch_obj
        pad.Length = params.length_mm
        pad.Midplane = params.symmetric
    else:
        pad = doc.addObject("Part::Extrusion", "Extrude")
        pad.Base = sketch_obj
        pad.DirMode = "Normal"
        pad.LengthFwd = params.length_mm
        pad.Solid = True
        if params.symmetric:
            pad.Symmetric = True
    doc.recompute()
    return ok(_created_object_data(pad, doc))


@_wrap
def fillet_edges(
    document: str | None = None,
    object: str | None = None,
    edges: list[str] | None = None,
    radius_mm: float | None = None,
) -> dict[str, Any]:
    params = models.validate_input(
        models.FilletEdgesInput,
        {"document": document, "object": object, "edges": edges, "radius_mm": radius_mm},
    )
    doc = _doc(params.document)
    source = fcapi.find_object(doc, params.object)
    edge_names = params.edges
    if edge_names is None:
        selection = get_selection()["data"]["selection"]
        edge_names = [
            sub
            for entry in selection
            if entry["object"] == source.Name
            for sub in entry["subelements"]
            if sub.startswith("Edge")
        ]
    if not edge_names:
        raise ToolFailure("validation_error", "No edges were provided or selected")
    fillet = doc.addObject("Part::Fillet", "Fillet")
    fillet.Base = source
    fillet.Edges = [(edge, params.radius_mm, params.radius_mm) for edge in edge_names]
    doc.recompute()
    return ok(_created_object_data(fillet, doc))


def _resolve_operand_objects(doc, object_names: list[str] | None):
    if object_names is None:
        selection = get_selection()["data"]["selection"]
        names = [entry["object"] for entry in selection if entry.get("object") and not entry["subelements"]]
    else:
        names = object_names
    if len(names) < 2:
        raise ToolFailure("validation_error", "Boolean operations require at least two objects")
    objects = [fcapi.find_object(doc, name) for name in names]
    for obj in objects:
        if not hasattr(obj, "Shape") or getattr(obj, "Shape", None) is None:
            raise ToolFailure(
                "validation_error", "Boolean operands must be solid objects", {"object": getattr(obj, "Name", None)}
            )
    return objects


@_wrap
def boolean_operation(
    document: str | None = None,
    operation: str | None = None,
    objects: list[str] | None = None,
    label: str = "Boolean",
) -> dict[str, Any]:
    params = models.validate_input(
        models.BooleanOperationInput,
        {"document": document, "operation": operation, "objects": objects, "label": label},
    )
    doc = _doc(params.document)
    operands = _resolve_operand_objects(doc, params.objects)
    if params.operation == "union":
        result = doc.addObject("Part::MultiFuse", params.label)
        result.Shapes = operands
    elif params.operation == "intersection":
        result = doc.addObject("Part::MultiCommon", params.label)
        result.Shapes = operands
    else:
        result = operands[0]
        for index, tool in enumerate(operands[1:], start=1):
            cut_label = params.label if index == len(operands) - 1 else f"{params.label}_Step{index}"
            cut = doc.addObject("Part::Cut", cut_label)
            cut.Base = result
            cut.Tool = tool
            result = cut
    doc.recompute()
    return ok(_created_object_data(result, doc))


@_wrap
def set_property(
    document: str | None = None, object: str | None = None, property: str | None = None, value: Any = None
) -> dict[str, Any]:
    params = models.validate_input(
        models.SetPropertyInput,
        {"document": document, "object": object, "property": property, "value": value},
    )
    doc = _doc(params.document)
    obj = fcapi.find_object(doc, params.object)
    prop = params.property
    type_id = getattr(obj, "TypeId", "")
    allowed = {
        "Part::Box": {"Length", "Width", "Height", "Label", "Placement"},
        "Part::Cylinder": {"Radius", "Height", "Label", "Placement"},
        "PartDesign::Pad": {"Length", "Label"},
        "Part::Extrusion": {"LengthFwd", "Label"},
    }
    common = {"Label", "Placement"}
    if prop not in allowed.get(type_id, common) and prop not in common:
        raise ToolFailure(
            UNSUPPORTED_OPERATION, f"Property is not allowlisted for {type_id}", {"property": prop, "type": type_id}
        )
    if prop == "Label":
        string_value = models.validate_input(models.StringValueInput, {"value": params.value})
        setattr(obj, prop, string_value.value)
    elif prop == "Placement":
        placement_value = models.validate_input(models.PlacementValueInput, {"value": params.value})
        fcapi.apply_placement(obj, placement_value.value)
    else:
        positive_value = models.validate_input(models.PositiveValueInput, {"value": params.value})
        setattr(obj, prop, positive_value.value)
    doc.recompute()
    return ok({"object": fcapi.object_ref(obj, doc), "property": prop, "value": getattr(obj, prop, None)})


def _export_objects(doc, object_names: list[str] | None):
    if object_names:
        return [fcapi.find_object(doc, name) for name in object_names]
    return [
        obj
        for obj in getattr(doc, "Objects", [])
        if bool(getattr(getattr(obj, "ViewObject", None), "Visibility", True)) and hasattr(obj, "Shape")
    ]


@_wrap
def export_step(
    document: str | None = None, objects: list[str] | None = None, path: str | None = None
) -> dict[str, Any]:
    params = models.validate_input(models.ExportStepInput, {"document": document, "objects": objects, "path": path})
    doc = _doc(params.document)
    selected = _export_objects(doc, params.objects)
    try:
        fcapi.import_gui().export(selected, params.path)
    except Exception as exc:
        raise ToolFailure(EXPORT_FAILED, str(exc), {"path": params.path}) from exc
    return ok({"path": params.path, "objects": [fcapi.object_ref(obj, doc) for obj in selected]})


@_wrap
def export_stl(
    document: str | None = None,
    objects: list[str] | None = None,
    path: str | None = None,
    linear_deflection: float | None = None,
    angular_deflection: float | None = None,
) -> dict[str, Any]:
    params = models.validate_input(
        models.ExportStlInput,
        {
            "document": document,
            "objects": objects,
            "path": path,
            "linear_deflection": linear_deflection,
            "angular_deflection": angular_deflection,
        },
    )
    doc = _doc(params.document)
    selected = _export_objects(doc, params.objects)
    try:
        fcapi.mesh().export(selected, params.path)
    except Exception as exc:
        raise ToolFailure(EXPORT_FAILED, str(exc), {"path": params.path}) from exc
    return ok({"path": params.path, "objects": [fcapi.object_ref(obj, doc) for obj in selected]})


TOOL_HANDLERS = {
    "get_active_document": get_active_document,
    "get_selection": get_selection,
    "create_document": create_document,
    "recompute": recompute,
    "save_document": save_document,
    "create_body": create_body,
    "add_box": add_box,
    "add_cylinder": add_cylinder,
    "create_sketch": create_sketch,
    "add_sketch_geometry": add_sketch_geometry,
    "add_sketch_constraint": add_sketch_constraint,
    "solve_sketch": solve_sketch,
    "pad_sketch": pad_sketch,
    "fillet_edges": fillet_edges,
    "boolean_operation": boolean_operation,
    "set_property": set_property,
    "export_step": export_step,
    "export_stl": export_stl,
}
