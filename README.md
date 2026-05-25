# FreeCAD MCP Workbench

FreeCAD MCP Workbench exposes a live FreeCAD GUI session through a local Model Context Protocol Streamable HTTP server.

The Workbench is designed for local use only. It binds to `127.0.0.1`, starts only when requested from the FreeCAD UI, and exposes typed CAD tools rather than arbitrary Python execution.

## Load Locally

1. Copy or symlink this repository into a FreeCAD Mod directory, or add the repository root to FreeCAD's macro/module path.
2. Start FreeCAD.
3. Select the `MCP` Workbench.
4. Run `Check MCP Dependencies`.
5. Run `Start MCP Server`.

The default endpoint is:

```text
http://127.0.0.1:8765/mcp
```

If the default port is busy, the Workbench chooses the next available port.

## Development

Run the local test suite outside FreeCAD:

```bash
uv run python -m unittest discover -s tests
```

Install development dependencies and run static checks:

```bash
uv sync --extra dev --extra mcp
uv run ruff check freecad_mcp_workbench tests InitGui.py
uv run ruff format freecad_mcp_workbench tests InitGui.py
uv run mypy freecad_mcp_workbench tests InitGui.py
```

The tests use mocked FreeCAD modules. Full runtime validation still requires a manual FreeCAD acceptance run.

See [docs/user/installation.md](docs/user/installation.md) and [docs/user/troubleshooting.md](docs/user/troubleshooting.md) for local Workbench setup and runtime diagnostics.
