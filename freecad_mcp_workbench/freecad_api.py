"""Lazy FreeCAD access and JSON-compatible serialization helpers."""

from __future__ import annotations

import importlib
import queue
import threading
from collections.abc import Callable
from typing import Any

from . import ui
from .errors import DOCUMENT_NOT_FOUND, NO_ACTIVE_DOCUMENT, OBJECT_NOT_FOUND, ToolFailure


def app():
    return importlib.import_module("FreeCAD")


def gui():
    try:
        return importlib.import_module("FreeCADGui")
    except Exception:
        return None


def part():
    return importlib.import_module("Part")


def sketcher():
    return importlib.import_module("Sketcher")


def mesh():
    return importlib.import_module("Mesh")


def import_gui():
    return importlib.import_module("ImportGui")


def active_document():
    doc = getattr(app(), "ActiveDocument", None)
    if doc is None:
        raise ToolFailure(NO_ACTIVE_DOCUMENT, "No active FreeCAD document")
    return doc


def get_document(name: str | None = None):
    fc = app()
    if not name:
        return active_document()
    doc = fc.getDocument(name) if hasattr(fc, "getDocument") else None
    if doc is None:
        raise ToolFailure(DOCUMENT_NOT_FOUND, f"Document not found: {name}", {"document": name})
    return doc


def find_object(doc: Any, name: str):
    obj = doc.getObject(name) if hasattr(doc, "getObject") else None
    if obj is None:
        raise ToolFailure(OBJECT_NOT_FOUND, f"Object not found: {name}", {"object": name})
    return obj


def object_ref(obj: Any, doc: Any | None = None) -> dict[str, Any]:
    document = doc or getattr(obj, "Document", None)
    return {
        "document": getattr(document, "Name", None),
        "name": getattr(obj, "Name", None),
        "label": getattr(obj, "Label", None),
        "type": getattr(obj, "TypeId", None),
    }


def matrix_to_rows(matrix: Any) -> list[list[float]]:
    attrs = (
        ("A11", "A12", "A13", "A14"),
        ("A21", "A22", "A23", "A24"),
        ("A31", "A32", "A33", "A34"),
        ("A41", "A42", "A43", "A44"),
    )
    rows: list[list[float]] = []
    for row in attrs:
        rows.append([float(getattr(matrix, attr, 0.0)) for attr in row])
    return rows


def placement_to_transform(placement: Any | None) -> dict[str, Any] | None:
    if placement is None:
        return None
    base = getattr(placement, "Base", None)
    rotation = getattr(placement, "Rotation", None)
    position = [
        float(getattr(base, "x", 0.0)),
        float(getattr(base, "y", 0.0)),
        float(getattr(base, "z", 0.0)),
    ]
    angles = [0.0, 0.0, 0.0]
    if rotation is not None:
        if hasattr(rotation, "toEuler"):
            angles = [float(v) for v in rotation.toEuler()]
        elif all(hasattr(rotation, attr) for attr in ("Yaw", "Pitch", "Roll")):
            angles = [float(rotation.Yaw), float(rotation.Pitch), float(rotation.Roll)]
    matrix = getattr(placement, "Matrix", None)
    return {
        "position_mm": position,
        "rotation_degrees": angles,
        "matrix": matrix_to_rows(matrix) if matrix is not None else identity_matrix(),
    }


def identity_matrix() -> list[list[float]]:
    return [
        [1.0, 0.0, 0.0, 0.0],
        [0.0, 1.0, 0.0, 0.0],
        [0.0, 0.0, 1.0, 0.0],
        [0.0, 0.0, 0.0, 1.0],
    ]


def make_placement(position_mm: tuple[float, float, float], rotation_degrees: tuple[float, float, float]):
    fc = app()
    vector = fc.Vector(*position_mm)
    rotation = fc.Rotation(*rotation_degrees)
    return fc.Placement(vector, rotation)


def apply_placement(obj: Any, placement_data: Any | None) -> None:
    if not placement_data:
        return
    position = tuple(placement_data.position_mm)
    rotation = tuple(placement_data.rotation_degrees)
    obj.Placement = make_placement(position, rotation)


def document_summary(doc: Any | None) -> dict[str, Any] | None:
    if doc is None:
        return None
    path = getattr(doc, "FileName", None) or None
    is_dirty = bool(getattr(doc, "Modified", False))
    return {
        "name": getattr(doc, "Name", None),
        "label": getattr(doc, "Label", getattr(doc, "Name", None)),
        "path": path,
        "is_dirty": is_dirty,
    }


def object_summary(obj: Any) -> dict[str, Any]:
    placement = getattr(obj, "Placement", None)
    world = getattr(obj, "getGlobalPlacement", lambda: placement)()
    summary = {
        "name": getattr(obj, "Name", None),
        "label": getattr(obj, "Label", None),
        "type": getattr(obj, "TypeId", None),
        "visibility": bool(getattr(getattr(obj, "ViewObject", None), "Visibility", True)),
        "local_transform": placement_to_transform(placement),
        "world_transform": placement_to_transform(world),
        "children": [getattr(child, "Name", None) for child in getattr(obj, "OutList", [])],
    }
    if hasattr(obj, "Shape") and obj.Shape is not None:
        bbox = bounding_box(obj)
        if bbox is not None:
            summary["bounding_box"] = bbox
    return summary


def bounding_box(obj: Any) -> dict[str, Any] | None:
    shape = getattr(obj, "Shape", None)
    box = getattr(shape, "BoundBox", None)
    if box is None:
        return None
    return {
        "x_min": float(getattr(box, "XMin", 0.0)),
        "y_min": float(getattr(box, "YMin", 0.0)),
        "z_min": float(getattr(box, "ZMin", 0.0)),
        "x_max": float(getattr(box, "XMax", 0.0)),
        "y_max": float(getattr(box, "YMax", 0.0)),
        "z_max": float(getattr(box, "ZMax", 0.0)),
    }


def active_body_name() -> str | None:
    g = gui()
    active_doc = getattr(g, "ActiveDocument", None) if g else None
    body = getattr(active_doc, "ActiveView", None)
    if body is None:
        return None
    active = getattr(body, "getActiveObject", lambda *_args: None)("pdbody")
    return getattr(active, "Name", None)


def active_sketch_name() -> str | None:
    g = gui()
    active_doc = getattr(g, "ActiveDocument", None) if g else None
    if active_doc is None:
        return None
    sketch = getattr(active_doc, "getInEdit", lambda: None)()
    return getattr(sketch, "Name", None)


class GuiDispatcher:
    """Run work on the FreeCAD GUI thread when Qt is available."""

    def __init__(self) -> None:
        self._dispatcher = None
        if ui.QtCore is not None:
            QtCore = ui.QtCore

            class _Dispatcher(QtCore.QObject):  # type: ignore[name-defined]
                request = QtCore.Signal(object)

                def __init__(self):
                    super().__init__()
                    self.request.connect(self._handle, QtCore.Qt.QueuedConnection)

                def _handle(self, payload):
                    func, done, results = payload
                    try:
                        results.put((True, func()))
                    except Exception as exc:
                        results.put((False, exc))
                    finally:
                        done.set()

            self._dispatcher = _Dispatcher()

    def call(self, func: Callable[[], Any], *, timeout: float = 60.0) -> Any:
        if self._dispatcher is None or threading.current_thread() is threading.main_thread():
            return func()
        done = threading.Event()
        results: queue.Queue[tuple[bool, Any]] = queue.Queue(maxsize=1)
        self._dispatcher.request.emit((func, done, results))
        if not done.wait(timeout):
            raise TimeoutError("Timed out waiting for FreeCAD GUI thread")
        success, value = results.get()
        if success:
            return value
        raise value


def recompute_document(doc: Any) -> dict[str, Any]:
    warnings: list[str] = []
    doc.recompute()
    if hasattr(doc, "OpenTransaction"):
        warnings.append("Document transaction support detected")
    return {"document": document_summary(doc), "warnings": warnings}
