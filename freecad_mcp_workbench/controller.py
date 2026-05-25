"""Workbench server lifecycle controller."""

from __future__ import annotations

import enum
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from .dependencies import check_mcp_dependency
from .errors import ToolFailure
from .freecad_api import GuiDispatcher, app, gui
from .logging_config import get_logger, log_path
from .server import DEFAULT_HOST, DEFAULT_PORT, ServerRuntime, start_runtime, stop_runtime
from .tools import TOOL_HANDLERS


class ServerState(str, enum.Enum):
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    FAILED = "failed"


@dataclass
class ControllerStatus:
    state: ServerState
    url: str | None = None
    error: str | None = None
    log_path: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "state": self.state.value,
            "url": self.url,
            "error": self.error,
            "log_path": self.log_path,
        }


def _console_message(message: str) -> None:
    try:
        app().Console.PrintMessage(f"{message}\n")
    except Exception:
        print(message)


def _available_tools_message() -> str:
    tools = "\n".join(f"  - {name}" for name in TOOL_HANDLERS)
    return f"MCP available tools ({len(TOOL_HANDLERS)}):\n{tools}"


class ServerController:
    def __init__(self) -> None:
        self.state = ServerState.STOPPED
        self.error: str | None = None
        self.runtime: ServerRuntime | None = None
        self.dispatcher = GuiDispatcher()
        self.logger = get_logger()

    @property
    def url(self) -> str | None:
        return self.runtime.url if self.runtime else None

    def status(self) -> ControllerStatus:
        return ControllerStatus(self.state, self.url, self.error, str(log_path()))

    def dispatch(self, func: Callable[[], Any]) -> Any:
        return self.dispatcher.call(func)

    def start(self, host: str = DEFAULT_HOST, port: int | None = None) -> ControllerStatus:
        if self.runtime is not None:
            return self.status()
        self.state = ServerState.STARTING
        self.error = None
        self.logger.info("server_start_requested")
        try:
            status = check_mcp_dependency()
            if not status.available:
                raise ToolFailure("dependency_missing", status.message, status.to_dict())
            self.runtime = start_runtime(self.dispatch, host=host, port=port or DEFAULT_PORT)
            self.state = ServerState.RUNNING
            self.logger.info("server_started url=%s", self.runtime.url)
            _console_message(_available_tools_message())
        except Exception as exc:
            self.runtime = None
            self.state = ServerState.FAILED
            self.error = str(exc)
            self.logger.exception("server_start_failed")
        self.report_status()
        return self.status()

    def stop(self) -> ControllerStatus:
        if self.runtime is None:
            self.state = ServerState.STOPPED
            self.error = None
            self.report_status()
            return self.status()
        self.logger.info("server_stop_requested url=%s", self.runtime.url)
        try:
            stop_runtime(self.runtime)
            self.state = ServerState.STOPPED
            self.error = None
            self.logger.info("server_stopped")
        except Exception as exc:
            self.state = ServerState.FAILED
            self.error = str(exc)
            self.logger.exception("server_stop_failed")
        finally:
            self.runtime = None
        self.report_status()
        return self.status()

    def dependency_status(self) -> dict[str, Any]:
        status = check_mcp_dependency()
        self.logger.info("dependency_check available=%s python=%s", status.available, status.python_version)
        return status.to_dict()

    def report_status(self) -> None:
        g = gui()
        if g is None:
            return
        message = f"MCP server {self.state.value}"
        if self.url:
            message = f"{message}: {self.url}"
        if self.error:
            message = f"{message}: {self.error}"
        try:
            g.updateGui()
            g.addModule("freecad_mcp_workbench")
            g.doCommand(f"print({message!r})")
        except Exception:
            pass


_CONTROLLER: ServerController | None = None


def get_controller() -> ServerController:
    global _CONTROLLER
    if _CONTROLLER is None:
        _CONTROLLER = ServerController()
    return _CONTROLLER
