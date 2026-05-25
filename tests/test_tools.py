from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from freecad_mcp_workbench import tools
from freecad_mcp_workbench.schemas import TOOL_SCHEMAS
from tests.conftest import install_fake_freecad, remove_fake_freecad


class ToolTests(unittest.TestCase):
    def setUp(self):
        self.fake_freecad = install_fake_freecad()

    def tearDown(self):
        remove_fake_freecad()

    def test_create_document_returns_summary(self):
        result = tools.create_document(name="demo_part")

        self.assertTrue(result["ok"])
        self.assertEqual(result["data"]["document"]["name"], "demo_part")

    def test_get_active_document_without_document(self):
        result = tools.get_active_document()

        self.assertEqual(
            result,
            {"ok": True, "data": {"document": None, "objects": [], "active_body": None, "active_sketch": None}},
        )

    def test_add_box_validates_and_recomputes(self):
        tools.create_document(name="demo")

        result = tools.add_box(document="demo", label="Base", length_mm=80, width_mm=40, height_mm=12)

        self.assertTrue(result["ok"])
        self.assertEqual(result["data"]["object"]["name"], "Base")
        self.assertEqual(self.fake_freecad["docs"]["demo"].recompute_count, 1)

    def test_add_box_rejects_invalid_dimensions(self):
        tools.create_document(name="demo")

        result = tools.add_box(document="demo", label="Base", length_mm=0, width_mm=40, height_mm=12)

        self.assertFalse(result["ok"])
        self.assertEqual(result["error"]["code"], "validation_error")

    def test_set_property_uses_allowlist(self):
        tools.create_document(name="demo")
        tools.add_box(document="demo", label="Base", length_mm=80, width_mm=40, height_mm=12)

        accepted = tools.set_property(document="demo", object="Base", property="Length", value=100)
        rejected = tools.set_property(document="demo", object="Base", property="Radius", value=5)

        self.assertTrue(accepted["ok"])
        self.assertEqual(accepted["data"]["value"], 100)
        self.assertFalse(rejected["ok"])
        self.assertEqual(rejected["error"]["code"], "unsupported_operation")

    def test_create_sketch_and_add_geometry(self):
        tools.create_document(name="demo")
        sketch = tools.create_sketch(document="demo", label="Profile", support={"mode": "plane", "plane": "XY"})
        geometry = tools.add_sketch_geometry(
            document="demo",
            sketch="Profile",
            geometry=[{"type": "rectangle", "origin_mm": [0, 0], "width_mm": 10, "height_mm": 5}],
        )

        self.assertTrue(sketch["ok"])
        self.assertTrue(geometry["ok"])
        self.assertEqual(geometry["data"]["geometry"][0]["ids"], ["g0", "g1", "g2", "g3"])

    def test_save_document_requires_fcstd_path(self):
        tools.create_document(name="demo")
        with tempfile.TemporaryDirectory() as temp_dir:
            tmp_path = Path(temp_dir)
            rejected = tools.save_document(document="demo", path=str(tmp_path / "demo.step"))
            accepted = tools.save_document(document="demo", path=str(tmp_path / "demo.FCStd"))

        self.assertFalse(rejected["ok"])
        self.assertTrue(accepted["ok"])
        self.assertFalse(accepted["data"]["document"]["is_dirty"])

    def test_boolean_operation_union_creates_multifuse(self):
        tools.create_document(name="demo")
        tools.add_box(document="demo", label="Base", length_mm=80, width_mm=40, height_mm=12)
        tools.add_box(document="demo", label="Tool", length_mm=10, width_mm=10, height_mm=10)

        result = tools.boolean_operation(document="demo", operation="union", objects=["Base", "Tool"], label="Union")

        doc = self.fake_freecad["docs"]["demo"]
        obj = doc.getObject("Union")
        self.assertTrue(result["ok"])
        self.assertEqual(result["data"]["object"]["type"], "Part::MultiFuse")
        self.assertEqual(obj.Shapes, [doc.getObject("Base"), doc.getObject("Tool")])
        self.assertEqual(doc.recompute_count, 3)

    def test_boolean_operation_difference_wires_base_and_tool(self):
        tools.create_document(name="demo")
        tools.add_box(document="demo", label="Base", length_mm=80, width_mm=40, height_mm=12)
        tools.add_box(document="demo", label="Tool", length_mm=10, width_mm=10, height_mm=10)

        result = tools.boolean_operation(document="demo", operation="difference", objects=["Base", "Tool"], label="Cut")

        doc = self.fake_freecad["docs"]["demo"]
        obj = doc.getObject("Cut")
        self.assertTrue(result["ok"])
        self.assertEqual(result["data"]["object"]["type"], "Part::Cut")
        self.assertEqual(obj.Base, doc.getObject("Base"))
        self.assertEqual(obj.Tool, doc.getObject("Tool"))
        self.assertEqual(doc.recompute_count, 3)

    def test_boolean_operation_rejects_invalid_operation(self):
        tools.create_document(name="demo")

        result = tools.boolean_operation(document="demo", operation="disjoint", objects=["Base", "Tool"])

        self.assertFalse(result["ok"])
        self.assertEqual(result["error"]["code"], "validation_error")

    def test_boolean_operation_requires_two_objects(self):
        tools.create_document(name="demo")
        tools.add_box(document="demo", label="Base", length_mm=80, width_mm=40, height_mm=12)

        result = tools.boolean_operation(document="demo", operation="union", objects=["Base"])

        self.assertFalse(result["ok"])
        self.assertEqual(result["error"]["code"], "validation_error")

    def test_all_v1_tool_names_registered(self):
        expected = {
            "get_active_document",
            "get_selection",
            "create_document",
            "recompute",
            "save_document",
            "create_body",
            "add_box",
            "add_cylinder",
            "create_sketch",
            "add_sketch_geometry",
            "add_sketch_constraint",
            "solve_sketch",
            "pad_sketch",
            "fillet_edges",
            "boolean_operation",
            "set_property",
            "export_step",
            "export_stl",
        }
        self.assertEqual(set(tools.TOOL_HANDLERS), expected)
        self.assertEqual(set(TOOL_SCHEMAS), expected)


if __name__ == "__main__":
    unittest.main()
