"""FreeCAD GUI entrypoint for the MCP Workbench."""

from __future__ import annotations


class MCPWorkbench(Workbench):  # type: ignore[name-defined]
    MenuText = "MCP"
    ToolTip = "Expose this FreeCAD session through a local MCP server"
    Icon = ""

    def Initialize(self):
        from freecad_mcp_workbench.commands import COMMANDS, register_commands

        register_commands()
        self.appendToolbar("MCP", COMMANDS)
        self.appendMenu("MCP", COMMANDS)

    def Activated(self):
        from freecad_mcp_workbench.controller import get_controller

        get_controller().report_status()

    def Deactivated(self):
        pass

    def GetClassName(self):
        return "Gui::PythonWorkbench"


Gui.addWorkbench(MCPWorkbench())  # type: ignore[name-defined]

