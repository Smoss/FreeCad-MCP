from __future__ import annotations

import sys
import types


class FakeVector:
    def __init__(self, x=0, y=0, z=0):
        self.x = x
        self.y = y
        self.z = z


class FakeRotation:
    def __init__(self, yaw=0, pitch=0, roll=0):
        self._angles = [yaw, pitch, roll]

    def toEuler(self):
        return self._angles


class FakeMatrix:
    A11 = 1
    A12 = 0
    A13 = 0
    A14 = 0
    A21 = 0
    A22 = 1
    A23 = 0
    A24 = 0
    A31 = 0
    A32 = 0
    A33 = 1
    A34 = 0
    A41 = 0
    A42 = 0
    A43 = 0
    A44 = 1


class FakePlacement:
    def __init__(self, base=None, rotation=None):
        self.Base = base or FakeVector()
        self.Rotation = rotation or FakeRotation()
        self.Matrix = FakeMatrix()


class FakeBoundBox:
    XMin = 0
    YMin = 0
    ZMin = 0
    XMax = 1
    YMax = 1
    ZMax = 1


class FakeShape:
    BoundBox = FakeBoundBox()


class FakeViewObject:
    Visibility = True


class FakeObject:
    def __init__(self, type_id, label, document, name):
        self.TypeId = type_id
        self.Label = label
        self.Document = document
        self.Name = name
        self.Placement = FakePlacement()
        self.ViewObject = FakeViewObject()
        self.OutList = []
        self.InList = []
        self.Geometry = []
        self.Constraints = []
        if type_id in {"Part::Box", "Part::Cylinder", "Part::Fillet", "Part::Extrusion"}:
            self.Shape = FakeShape()

    def addGeometry(self, geom, construction=False):
        self.Geometry.append((geom, construction))
        return len(self.Geometry) - 1

    def addConstraint(self, constraint):
        self.Constraints.append(constraint)
        return len(self.Constraints) - 1

    def solve(self):
        return 0

    def getGlobalPlacement(self):
        return self.Placement


class FakeDocument:
    def __init__(self, name="Unnamed"):
        self.Name = name
        self.Label = name
        self.FileName = ""
        self.Modified = True
        self.Objects = []
        self._objects = {}
        self.recompute_count = 0

    def addObject(self, type_id, label):
        name = label.replace(" ", "_")
        counter = 1
        original = name
        while name in self._objects:
            counter += 1
            name = f"{original}{counter}"
        obj = FakeObject(type_id, label, self, name)
        self._objects[name] = obj
        self.Objects.append(obj)
        return obj

    def getObject(self, name):
        return self._objects.get(name)

    def recompute(self):
        self.recompute_count += 1

    def saveAs(self, path):
        self.FileName = path
        self.Modified = False


def install_fake_freecad():
    state = {"docs": {}, "active": None}

    freecad = types.ModuleType("FreeCAD")

    def new_document(name=None):
        doc = FakeDocument(name or "Unnamed")
        state["docs"][doc.Name] = doc
        state["active"] = doc
        freecad.ActiveDocument = doc
        return doc

    def get_document(name):
        return state["docs"].get(name)

    def set_active_document(name):
        state["active"] = state["docs"].get(name)
        freecad.ActiveDocument = state["active"]

    freecad.ActiveDocument = None
    freecad.newDocument = new_document
    freecad.getDocument = get_document
    freecad.setActiveDocument = set_active_document
    freecad.Vector = FakeVector
    freecad.Rotation = FakeRotation
    freecad.Placement = FakePlacement

    gui = types.ModuleType("FreeCADGui")
    gui.Selection = types.SimpleNamespace(getSelectionEx=lambda: [])

    part = types.ModuleType("Part")
    part.LineSegment = lambda start, end: ("line", start, end)
    part.Circle = lambda center, normal, radius: ("circle", center, normal, radius)
    part.ArcOfCircle = lambda circle, start, end: ("arc", circle, start, end)

    sketcher = types.ModuleType("Sketcher")
    sketcher.Constraint = lambda *args: ("constraint", args)

    mesh = types.ModuleType("Mesh")
    mesh.export = lambda objects, path: None

    import_gui = types.ModuleType("ImportGui")
    import_gui.export = lambda objects, path: None

    sys.modules["FreeCAD"] = freecad
    sys.modules["FreeCADGui"] = gui
    sys.modules["Part"] = part
    sys.modules["Sketcher"] = sketcher
    sys.modules["Mesh"] = mesh
    sys.modules["ImportGui"] = import_gui
    return state


def remove_fake_freecad():
    for name in ("FreeCAD", "FreeCADGui", "Part", "Sketcher", "Mesh", "ImportGui"):
        sys.modules.pop(name, None)
