---
name: freecad-mcp-workbench
description: Use when the user wants Codex to connect to or control a live FreeCAD GUI session through the FreeCAD MCP Workbench, including creating CAD geometry, checking the MCP setup, troubleshooting the localhost MCP connection, or preparing a new Codex session to use FreeCAD tools.
metadata:
  short-description: Control FreeCAD through MCP
---

# FreeCAD MCP Workbench

Use this skill when the user wants to operate FreeCAD from Codex through the local MCP server implemented by this repository.

## Runtime model

The MCP server runs inside the live FreeCAD GUI process. Codex connects to it as a remote MCP server.

Expected Codex config:

```toml
[mcp_servers.freecad]
url = "http://127.0.0.1:8765/mcp"
startup_timeout_sec = 30.0
```

If FreeCAD chooses a fallback port, update the URL to the displayed port.

## Startup checklist

1. FreeCAD must be open.
2. The repository must be installed as a FreeCAD Workbench, usually by symlinking the repo into the FreeCAD user `Mod` directory.
3. In FreeCAD, select the `MCP` Workbench.
4. Run `MCP -> Check MCP Dependencies`.
5. Run `MCP -> Start MCP Server`.
6. Copy or confirm the displayed URL.
7. Codex must be restarted or opened in a fresh session after the MCP server is added to `~/.codex/config.toml`.

Do not assume the current Codex session has loaded the `freecad` MCP server just because the config file was edited. MCP tools are loaded at session start.

## Detect available tools

At the start of a FreeCAD control task, search for FreeCAD MCP tools with `tool_search`.

If FreeCAD tools are available, use them directly. Expected v1 tool names:

- `get_active_document`
- `get_selection`
- `create_document`
- `recompute`
- `save_document`
- `create_body`
- `add_box`
- `add_cylinder`
- `create_sketch`
- `add_sketch_geometry`
- `add_sketch_constraint`
- `solve_sketch`
- `pad_sketch`
- `fillet_edges`
- `set_property`
- `export_step`
- `export_stl`

If FreeCAD tools are not available, tell the user to start the FreeCAD MCP server and open a fresh Codex session. Do not fake FreeCAD results with local Python.

## Common geometry request

For “create a box with cylinder,” use this sequence once the MCP tools are available:

1. `create_document` with `name: "box_with_cylinder"`.
2. `add_box` with `label: "Base"`, `length_mm: 80`, `width_mm: 40`, `height_mm: 12`.
3. `add_cylinder` with `label: "Post"`, `radius_mm: 8`, `height_mm: 30`, and placement:

```json
{
  "position_mm": [40, 20, 12],
  "rotation_degrees": [0, 0, 0]
}
```

The placement centers the cylinder on top of the box.

## Troubleshooting

- If Codex cannot see FreeCAD tools, the current session probably predates the config change. Start a new session.
- If Codex sees tools but calls fail to connect, FreeCAD probably is not running the server or the port changed.
- If the Workbench fails to start the server, run `MCP -> Check MCP Dependencies` in FreeCAD and inspect `MCP -> Show Server Log`.
- If geometry tools fail in live FreeCAD, prefer reporting the structured MCP error and checking the log over guessing at FreeCAD state.

## Local repo references

- Workbench entrypoint: `InitGui.py`
- MCP lifecycle: `freecad_mcp_workbench/controller.py`
- MCP adapter: `freecad_mcp_workbench/server.py`
- Tool handlers: `freecad_mcp_workbench/tools.py`
- Setup docs: `docs/user/installation.md`
- Troubleshooting docs: `docs/user/troubleshooting.md`

