"""V1 MCP tool handlers for FreeCAD."""

from __future__ import annotations

import os
from functools import wraps
from typing import Any

from . import freecad_api as fcapi
from .errors import (
    EXPORT_FAILED,
    RECOMPUTE_FAILED,
    SELECTION_ERROR,
    UNSUPPORTED_OPERATION,
    ToolFailure,
    result_from_exception,
    ok,
)
from .validation import (
    absolute_path,
    ensure_list,
    ensure_mapping,
    finite_number,
    non_empty_string,
    optional_bool,
    optional_document_name,
    point2,
    positive_number,
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
    return fcapi.get_document(optional_document_name(document))


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
    from .validation import document_safe_name

    safe_name = document_safe_name(name)
    fc = fcapi.app()
    doc = fc.newDocument(safe_name) if safe_name else fc.newDocument()
    if hasattr(fc, "setActiveDocument"):
        fc.setActiveDocument(doc.Name)
    return ok({"document": fcapi.document_summary(doc)})


@_wrap
def recompute(document: str | None = None) -> dict[str, Any]:
    doc = _doc(document)
    try:
        return ok(fcapi.recompute_document(doc))
    except Exception as exc:
        raise ToolFailure(RECOMPUTE_FAILED, str(exc), {"document": getattr(doc, "Name", None)}) from exc


@_wrap
def save_document(document: str | None = None, path: str | None = None) -> dict[str, Any]:
    doc = _doc(document)
    target = absolute_path(path, field="path", suffixes=(".fcstd",))
    os.makedirs(os.path.dirname(target), exist_ok=True)
    doc.saveAs(target)
    return ok({"path": target, "document": fcapi.document_summary(doc)})


@_wrap
def create_body(document: str | None = None, label: str = "Body") -> dict[str, Any]:
    doc = _doc(document)
    body_label = non_empty_string(label, field="label")
    body = doc.addObject("PartDesign::Body", body_label)
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
    doc = _doc(document)
    obj = doc.addObject("Part::Box", non_empty_string(label, field="label"))
    obj.Length = positive_number(length_mm, field="length_mm")
    obj.Width = positive_number(width_mm, field="width_mm")
    obj.Height = positive_number(height_mm, field="height_mm")
    fcapi.apply_placement(obj, placement)
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
    doc = _doc(document)
    obj = doc.addObject("Part::Cylinder", non_empty_string(label, field="label"))
    obj.Radius = positive_number(radius_mm, field="radius_mm")
    obj.Height = positive_number(height_mm, field="height_mm")
    fcapi.apply_placement(obj, placement)
    doc.recompute()
    return ok(_created_object_data(obj, doc))


@_wrap
def create_sketch(document: str | None = None, label: str = "Sketch", support: dict[str, Any] | None = None) -> dict[str, Any]:
    doc = _doc(document)
    sketch = doc.addObject("Sketcher::SketchObject", non_empty_string(label, field="label"))
    support_data = ensure_mapping(support or {"mode": "plane", "plane": "XY"}, field="support")
    mode = support_data.get("mode", "plane")
    if mode == "plane":
        plane = support_data.get("plane", "XY")
        if plane not in {"XY", "XZ", "YZ"}:
            raise ToolFailure("validation_error", "support.plane must be XY, XZ, or YZ")
        if plane == "XZ":
            sketch.Placement = fcapi.make_placement((0, 0, 0), (0, 90, 0))
        elif plane == "YZ":
            sketch.Placement = fcapi.make_placement((0, 0, 0), (90, 0, 0))
    elif mode == "selection":
        gui = fcapi.gui()
        selection = gui.Selection.getSelectionEx() if gui and hasattr(gui, "Selection") else []
        if len(selection) != 1 or len(getattr(selection[0], "SubElementNames", []) or []) != 1:
            raise ToolFailure(SELECTION_ERROR, "Selection support requires exactly one selected planar face")
        selected = selection[0]
        sketch.Support = [(selected.Object, selected.SubElementNames[0])]
        sketch.MapMode = "FlatFace"
    else:
        raise ToolFailure("validation_error", "support.mode must be plane or selection")
    doc.recompute()
    return ok({"object": fcapi.object_ref(sketch, doc), "local_transform": fcapi.placement_to_transform(sketch.Placement)})


def _geometry_count(sketch) -> int:
    return len(getattr(sketch, "Geometry", []) or [])


@_wrap
def add_sketch_geometry(document: str | None = None, sketch: str | None = None, geometry: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    doc = _doc(document)
    sketch_obj = fcapi.find_object(doc, non_empty_string(sketch, field="sketch"))
    part = fcapi.part()
    freecad = fcapi.app()
    operations = ensure_list(geometry, field="geometry")
    created = []
    for entry in operations:
        item = ensure_mapping(entry, field="geometry[]")
        kind = item.get("type")
        construction = optional_bool(item.get("construction"), field="construction")
        if kind == "line":
            start = point2(item.get("start_mm"), field="start_mm")
            end = point2(item.get("end_mm"), field="end_mm")
            geom = part.LineSegment(freecad.Vector(start[0], start[1], 0), freecad.Vector(end[0], end[1], 0))
            index = sketch_obj.addGeometry(geom, construction)
            created.append({"id": f"g{index}", "type": "line"})
        elif kind == "rectangle":
            origin = point2(item.get("origin_mm"), field="origin_mm")
            width = positive_number(item.get("width_mm"), field="width_mm")
            height = positive_number(item.get("height_mm"), field="height_mm")
            x, y = origin
            corners = [(x, y), (x + width, y), (x + width, y + height), (x, y + height)]
            ids = []
            for start, end in zip(corners, corners[1:] + corners[:1]):
                geom = part.LineSegment(freecad.Vector(start[0], start[1], 0), freecad.Vector(end[0], end[1], 0))
                ids.append(f"g{sketch_obj.addGeometry(geom, construction)}")
            created.append({"ids": ids, "type": "rectangle"})
        elif kind == "circle":
            center = point2(item.get("center_mm"), field="center_mm")
            radius = positive_number(item.get("radius_mm"), field="radius_mm")
            geom = part.Circle(freecad.Vector(center[0], center[1], 0), freecad.Vector(0, 0, 1), radius)
            index = sketch_obj.addGeometry(geom, construction)
            created.append({"id": f"g{index}", "type": "circle"})
        elif kind == "arc":
            center = point2(item.get("center_mm"), field="center_mm")
            radius = positive_number(item.get("radius_mm"), field="radius_mm")
            start = finite_number(item.get("start_degrees"), field="start_degrees")
            end = finite_number(item.get("end_degrees"), field="end_degrees")
            circle = part.Circle(freecad.Vector(center[0], center[1], 0), freecad.Vector(0, 0, 1), radius)
            geom = part.ArcOfCircle(circle, start, end)
            index = sketch_obj.addGeometry(geom, construction)
            created.append({"id": f"g{index}", "type": "arc"})
        else:
            raise ToolFailure("validation_error", "geometry type must be line, rectangle, circle, or arc")
    return ok({"sketch": fcapi.object_ref(sketch_obj, doc), "geometry": created, "geometry_count": _geometry_count(sketch_obj)})


def _geometry_index(identifier: Any) -> int:
    value = non_empty_string(identifier, field="geometry")
    if not value.startswith("g") or not value[1:].isdigit():
        raise ToolFailure("validation_error", "geometry identifiers must look like g0")
    return int(value[1:])


@_wrap
def add_sketch_constraint(document: str | None = None, sketch: str | None = None, constraints: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    doc = _doc(document)
    sketch_obj = fcapi.find_object(doc, non_empty_string(sketch, field="sketch"))
    sketcher = fcapi.sketcher()
    operations = ensure_list(constraints, field="constraints")
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
    for entry in operations:
        item = ensure_mapping(entry, field="constraints[]")
        kind = item.get("type")
        if kind not in mapping:
            raise ToolFailure("validation_error", "Unsupported sketch constraint type")
        geo = _geometry_index(item.get("geometry"))
        if kind in {"distance", "distance_x", "distance_y", "radius", "diameter"}:
            value = positive_number(item.get("value_mm"), field="value_mm")
            constraint = sketcher.Constraint(mapping[kind], geo, value)
        elif kind == "equal":
            other = _geometry_index(item.get("other_geometry"))
            constraint = sketcher.Constraint("Equal", geo, other)
        elif kind == "coincident":
            other = _geometry_index(item.get("other_geometry"))
            constraint = sketcher.Constraint("Coincident", geo, int(item.get("point", 1)), other, int(item.get("other_point", 1)))
        elif kind == "symmetric":
            other = _geometry_index(item.get("other_geometry"))
            axis = _geometry_index(item.get("axis_geometry"))
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
    doc = _doc(document)
    sketch_obj = fcapi.find_object(doc, non_empty_string(sketch, field="sketch"))
    doc.recompute()
    return ok({"sketch": fcapi.object_ref(sketch_obj, doc), "solver": _solver_state(sketch_obj)})


@_wrap
def pad_sketch(document: str | None = None, sketch: str | None = None, length_mm: float | None = None, symmetric: bool = False) -> dict[str, Any]:
    doc = _doc(document)
    sketch_obj = fcapi.find_object(doc, non_empty_string(sketch, field="sketch"))
    length = positive_number(length_mm, field="length_mm")
    symmetric_flag = optional_bool(symmetric, field="symmetric")
    parent = getattr(sketch_obj, "InList", [None])[0] if getattr(sketch_obj, "InList", []) else None
    if parent is not None and getattr(parent, "TypeId", "") == "PartDesign::Body":
        pad = doc.addObject("PartDesign::Pad", "Pad")
        if hasattr(parent, "addObject"):
            parent.addObject(pad)
        pad.Profile = sketch_obj
        pad.Length = length
        pad.Midplane = symmetric_flag
    else:
        pad = doc.addObject("Part::Extrusion", "Extrude")
        pad.Base = sketch_obj
        pad.DirMode = "Normal"
        pad.LengthFwd = length
        pad.Solid = True
        if symmetric_flag:
            pad.Symmetric = True
    doc.recompute()
    return ok(_created_object_data(pad, doc))


@_wrap
def fillet_edges(document: str | None = None, object: str | None = None, edges: list[str] | None = None, radius_mm: float | None = None) -> dict[str, Any]:
    doc = _doc(document)
    source = fcapi.find_object(doc, non_empty_string(object, field="object"))
    radius = positive_number(radius_mm, field="radius_mm")
    edge_names = edges
    if edge_names is None:
        selection = get_selection()["data"]["selection"]
        edge_names = [sub for entry in selection if entry["object"] == source.Name for sub in entry["subelements"] if sub.startswith("Edge")]
    if not edge_names:
        raise ToolFailure("validation_error", "No edges were provided or selected")
    fillet = doc.addObject("Part::Fillet", "Fillet")
    fillet.Base = source
    fillet.Edges = [(edge, radius, radius) for edge in edge_names]
    doc.recompute()
    return ok(_created_object_data(fillet, doc))


@_wrap
def set_property(document: str | None = None, object: str | None = None, property: str | None = None, value: Any = None) -> dict[str, Any]:
    doc = _doc(document)
    obj = fcapi.find_object(doc, non_empty_string(object, field="object"))
    prop = non_empty_string(property, field="property")
    type_id = getattr(obj, "TypeId", "")
    allowed = {
        "Part::Box": {"Length", "Width", "Height", "Label", "Placement"},
        "Part::Cylinder": {"Radius", "Height", "Label", "Placement"},
        "PartDesign::Pad": {"Length", "Label"},
        "Part::Extrusion": {"LengthFwd", "Label"},
    }
    common = {"Label", "Placement"}
    if prop not in allowed.get(type_id, common) and prop not in common:
        raise ToolFailure(UNSUPPORTED_OPERATION, f"Property is not allowlisted for {type_id}", {"property": prop, "type": type_id})
    if prop == "Label":
        setattr(obj, prop, non_empty_string(value, field="value"))
    elif prop == "Placement":
        fcapi.apply_placement(obj, ensure_mapping(value, field="value"))
    else:
        setattr(obj, prop, positive_number(value, field="value"))
    doc.recompute()
    return ok({"object": fcapi.object_ref(obj, doc), "property": prop, "value": getattr(obj, prop, None)})


def _export_objects(doc, object_names: list[str] | None):
    if object_names:
        return [fcapi.find_object(doc, non_empty_string(name, field="objects[]")) for name in object_names]
    return [
        obj
        for obj in getattr(doc, "Objects", [])
        if bool(getattr(getattr(obj, "ViewObject", None), "Visibility", True)) and hasattr(obj, "Shape")
    ]


@_wrap
def export_step(document: str | None = None, objects: list[str] | None = None, path: str | None = None) -> dict[str, Any]:
    doc = _doc(document)
    target = absolute_path(path, field="path", suffixes=(".step", ".stp"))
    selected = _export_objects(doc, objects)
    try:
        fcapi.import_gui().export(selected, target)
    except Exception as exc:
        raise ToolFailure(EXPORT_FAILED, str(exc), {"path": target}) from exc
    return ok({"path": target, "objects": [fcapi.object_ref(obj, doc) for obj in selected]})


@_wrap
def export_stl(
    document: str | None = None,
    objects: list[str] | None = None,
    path: str | None = None,
    linear_deflection: float | None = None,
    angular_deflection: float | None = None,
) -> dict[str, Any]:
    doc = _doc(document)
    target = absolute_path(path, field="path", suffixes=(".stl",))
    if linear_deflection is not None:
        positive_number(linear_deflection, field="linear_deflection")
    if angular_deflection is not None:
        positive_number(angular_deflection, field="angular_deflection")
    selected = _export_objects(doc, objects)
    try:
        fcapi.mesh().export(selected, target)
    except Exception as exc:
        raise ToolFailure(EXPORT_FAILED, str(exc), {"path": target}) from exc
    return ok({"path": target, "objects": [fcapi.object_ref(obj, doc) for obj in selected]})


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
    "set_property": set_property,
    "export_step": export_step,
    "export_stl": export_stl,
}
