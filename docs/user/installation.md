# Installation

## Local Workbench Install

This repository is structured as a FreeCAD Workbench. FreeCAD discovers it when the repository root is available as a module directory containing `InitGui.py`.

Common local options:

- Copy this repository into the FreeCAD user `Mod` directory.
- Symlink this repository into the FreeCAD user `Mod` directory.
- Add this repository root to FreeCAD's Python path for development.

Restart FreeCAD after adding the Workbench path, then choose the `MCP` Workbench from the Workbench selector.

## Dependency Setup

The MCP server uses the official Python SDK package named `mcp`. Use the Workbench command:

```text
MCP -> Check MCP Dependencies
```

If the package is missing, the command can install it into:

```text
~/.freecad_mcp_workbench/python
```

The Workbench adds that directory to `sys.path` before server startup.

## Client Connection

Start the server from FreeCAD:

```text
MCP -> Start MCP Server
```

Connect an MCP client to the displayed localhost URL:

```text
http://127.0.0.1:8765/mcp
```

If port `8765` is busy, the Workbench picks the next available local port and shows the selected URL.

## Manual Acceptance Run

1. Launch FreeCAD.
2. Enable the `MCP` Workbench.
3. Run `Check MCP Dependencies`.
4. Run `Start MCP Server`.
5. Connect an MCP client to the displayed URL.
6. Call `create_document`.
7. Call `add_box`.
8. Call `set_property` for one box dimension.
9. Call `recompute`.
10. Call `save_document`.
11. Call `export_step` and `export_stl`.
12. Run `Stop MCP Server`.

