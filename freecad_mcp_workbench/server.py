"""MCP Streamable HTTP server adapter."""

from __future__ import annotations

import socket
import threading
from collections.abc import Callable
from dataclasses import dataclass
from functools import wraps
from typing import Any

from .errors import DEPENDENCY_MISSING, ToolFailure
from .logging_config import get_logger
from .tools import TOOL_HANDLERS

FastMCP: Any | None
_FASTMCP_IMPORT_ERROR: Exception | None = None
try:
    from mcp.server.fastmcp import FastMCP
except Exception as exc:
    FastMCP = None
    _FASTMCP_IMPORT_ERROR = exc

uvicorn: Any | None
_UVICORN_IMPORT_ERROR: Exception | None = None
try:
    import uvicorn
except Exception as exc:
    uvicorn = None
    _UVICORN_IMPORT_ERROR = exc


DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8765
MCP_PATH = "/mcp"


@dataclass
class ServerRuntime:
    host: str
    port: int
    server: Any
    thread: threading.Thread

    @property
    def url(self) -> str:
        return f"http://{self.host}:{self.port}{MCP_PATH}"


def find_available_port(host: str = DEFAULT_HOST, start: int = DEFAULT_PORT, attempts: int = 50) -> int:
    for port in range(start, start + attempts):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                sock.bind((host, port))
            except OSError:
                continue
            return port
    raise OSError(f"No available localhost port in range {start}-{start + attempts - 1}")


def build_mcp_app(dispatch: Callable[[Callable[[], Any]], Any], host: str, port: int):
    if FastMCP is None:
        exc = _FASTMCP_IMPORT_ERROR
        raise ToolFailure(DEPENDENCY_MISSING, "MCP SDK is not importable", {"exception": str(exc)}) from exc

    mcp = FastMCP(
        "FreeCAD MCP Workbench",
        host=host,
        port=port,
        stateless_http=True,
        json_response=True,
        streamable_http_path=MCP_PATH,
    )

    for name, handler in TOOL_HANDLERS.items():

        def make_tool(tool_name=name, tool_handler=handler):
            @wraps(tool_handler)
            def tool(**kwargs) -> dict[str, Any]:
                get_logger().info("tool_call name=%s", tool_name)
                result = dispatch(lambda: tool_handler(**kwargs))
                get_logger().info("tool_result name=%s ok=%s", tool_name, result.get("ok"))
                return result

            tool.__name__ = tool_name
            return tool

        mcp.tool(name=name, description=f"FreeCAD MCP tool: {name}")(make_tool())

    return mcp.streamable_http_app()


def start_runtime(
    dispatch: Callable[[Callable[[], Any]], Any], host: str = DEFAULT_HOST, port: int | None = None
) -> ServerRuntime:
    if uvicorn is None:
        exc = _UVICORN_IMPORT_ERROR
        raise ToolFailure(
            DEPENDENCY_MISSING, "uvicorn is required by the MCP SDK HTTP transport", {"exception": str(exc)}
        ) from exc

    selected_port = find_available_port(host, port or DEFAULT_PORT)
    app = build_mcp_app(dispatch, host, selected_port)
    config = uvicorn.Config(app, host=host, port=selected_port, log_level="warning", access_log=False)
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, name="FreeCADMCPServer", daemon=True)
    thread.start()
    return ServerRuntime(host=host, port=selected_port, server=server, thread=thread)


def stop_runtime(runtime: ServerRuntime, timeout: float = 5.0) -> None:
    runtime.server.should_exit = True
    runtime.thread.join(timeout)
