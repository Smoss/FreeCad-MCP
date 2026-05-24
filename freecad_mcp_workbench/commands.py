"""FreeCAD command registration for the MCP Workbench."""

from __future__ import annotations

from typing import Any

from .controller import get_controller
from .dependencies import install_mcp_dependency
from .logging_config import log_path


COMMANDS = [
    "FreeCAD_MCP_Start",
    "FreeCAD_MCP_Stop",
    "FreeCAD_MCP_CopyURL",
    "FreeCAD_MCP_ShowLog",
    "FreeCAD_MCP_CheckDependencies",
]


def _gui():
    import FreeCADGui  # type: ignore

    return FreeCADGui


def _console_message(message: str) -> None:
    try:
        import FreeCAD  # type: ignore

        FreeCAD.Console.PrintMessage(f"{message}\n")
    except Exception:
        print(message)


def _dialog(title: str, message: str) -> None:
    try:
        from PySide import QtWidgets  # type: ignore

        QtWidgets.QMessageBox.information(None, title, message)
    except Exception:
        _console_message(f"{title}: {message}")


class _BaseCommand:
    menu_text = ""
    tooltip = ""

    def GetResources(self) -> dict[str, Any]:
        return {"MenuText": self.menu_text, "ToolTip": self.tooltip}

    def IsActive(self) -> bool:
        return True


class StartServerCommand(_BaseCommand):
    menu_text = "Start MCP Server"
    tooltip = "Start the local MCP Streamable HTTP server"

    def Activated(self) -> None:
        status = get_controller().start()
        if status.url:
            _dialog("MCP Server", f"Server running at {status.url}")
        elif status.error:
            _dialog("MCP Server", f"Server failed: {status.error}")


class StopServerCommand(_BaseCommand):
    menu_text = "Stop MCP Server"
    tooltip = "Stop the local MCP server"

    def Activated(self) -> None:
        status = get_controller().stop()
        _dialog("MCP Server", f"Server {status.state.value}")


class CopyURLCommand(_BaseCommand):
    menu_text = "Copy MCP URL"
    tooltip = "Copy the running MCP server URL"

    def Activated(self) -> None:
        url = get_controller().url
        if not url:
            _dialog("MCP Server", "The MCP server is not running.")
            return
        try:
            from PySide import QtWidgets  # type: ignore

            QtWidgets.QApplication.clipboard().setText(url)
            _dialog("MCP Server", f"Copied {url}")
        except Exception:
            _console_message(url)


class ShowLogCommand(_BaseCommand):
    menu_text = "Show Server Log"
    tooltip = "Open the MCP Workbench log file"

    def Activated(self) -> None:
        path = log_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.touch(exist_ok=True)
        try:
            from PySide import QtCore, QtGui  # type: ignore

            QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(str(path)))
        except Exception:
            _dialog("MCP Server Log", str(path))


class CheckDependenciesCommand(_BaseCommand):
    menu_text = "Check MCP Dependencies"
    tooltip = "Check and optionally install the MCP Python SDK"

    def Activated(self) -> None:
        status = get_controller().dependency_status()
        if status["available"]:
            _dialog("MCP Dependencies", status["message"])
            return
        install = False
        try:
            from PySide import QtWidgets  # type: ignore

            response = QtWidgets.QMessageBox.question(
                None,
                "MCP Dependencies",
                f"{status['message']}\n\nInstall into:\n{status['dependency_dir']}?",
            )
            install = response == QtWidgets.QMessageBox.Yes
        except Exception:
            _console_message(status["message"])
        if install:
            result = install_mcp_dependency()
            _dialog("MCP Dependencies", result.message)


def register_commands() -> None:
    gui = _gui()
    gui.addCommand("FreeCAD_MCP_Start", StartServerCommand())
    gui.addCommand("FreeCAD_MCP_Stop", StopServerCommand())
    gui.addCommand("FreeCAD_MCP_CopyURL", CopyURLCommand())
    gui.addCommand("FreeCAD_MCP_ShowLog", ShowLogCommand())
    gui.addCommand("FreeCAD_MCP_CheckDependencies", CheckDependenciesCommand())

