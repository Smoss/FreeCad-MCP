from __future__ import annotations

import unittest

from freecad_mcp_workbench import models
from freecad_mcp_workbench.errors import ToolFailure
from freecad_mcp_workbench.schemas import TOOL_SCHEMAS
from freecad_mcp_workbench.tools import TOOL_HANDLERS


class ModelTests(unittest.TestCase):
    def test_add_box_rejects_non_positive_dimension(self):
        with self.assertRaises(ToolFailure) as context:
            models.validate_input(
                models.AddBoxInput,
                {"length_mm": 0, "width_mm": 40, "height_mm": 12},
            )

        self.assertEqual(context.exception.code, "validation_error")

    def test_save_document_requires_absolute_fcstd_path(self):
        with self.assertRaises(ToolFailure) as context:
            models.validate_input(models.SaveDocumentInput, {"path": "demo.step"})

        self.assertEqual(context.exception.code, "validation_error")

    def test_schema_registry_matches_tool_registry(self):
        self.assertEqual(set(TOOL_SCHEMAS), set(TOOL_HANDLERS))

    def test_generated_schema_forbids_extra_root_properties(self):
        self.assertFalse(TOOL_SCHEMAS["add_box"]["additionalProperties"])


if __name__ == "__main__":
    unittest.main()
