"""FreeCAD GUI entrypoint for the MCP Workbench."""

from __future__ import annotations

from typing import TYPE_CHECKING

from freecad_mcp_workbench.commands import COMMANDS, register_commands
from freecad_mcp_workbench.controller import get_controller

if TYPE_CHECKING:

    class Workbench:
        def appendToolbar(self, name: str, commands: list[str]) -> None: ...

        def appendMenu(self, name: str, commands: list[str]) -> None: ...

    class _Gui:
        def addWorkbench(self, workbench: Workbench) -> None: ...

    Gui: _Gui


class MCPWorkbench(Workbench):
    MenuText = "MCP"
    ToolTip = "Expose this FreeCAD session through a local MCP server"
    Icon = ""

    def Initialize(self) -> None:
        register_commands()
        self.appendToolbar("MCP", COMMANDS)
        self.appendMenu("MCP", COMMANDS)

    def Activated(self) -> None:
        get_controller().report_status()

    def Deactivated(self) -> None:
        pass

    def GetClassName(self) -> str:
        return "Gui::PythonWorkbench"


Gui.addWorkbench(MCPWorkbench())  # noqa: F821
