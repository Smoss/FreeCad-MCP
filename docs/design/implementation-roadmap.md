# FreeCAD MCP Workbench Implementation Roadmap

## Overview

This roadmap turns the live FreeCAD MCP Workbench design into phased implementation work. It intentionally separates design, proof of concept, Workbench packaging, integration testing, and polish.

The implementation should not revisit the core architecture unless a proof of concept invalidates a technical assumption.

## Phase 0: Documentation Review

Deliverables:

- Review `freecad-mcp-workbench.md` for architecture completeness.
- Review `mcp-tools.md` for tool contract clarity.
- Confirm target FreeCAD version and operating systems.
- Confirm where generated `.FCStd`, STEP, STL, and logs should be written.

Acceptance criteria:

- Another engineer can describe the runtime model without asking whether the MCP server is inside or outside FreeCAD.
- Tool contracts are concrete enough to write tests before implementation.
- Open questions are limited to FreeCAD runtime validation, not product direction.

## Phase 1: Live Server Proof of Concept

Purpose:

Validate that an MCP Streamable HTTP server can run inside FreeCAD's Python environment and safely respond while the GUI remains usable.

Deliverables:

- Minimal FreeCAD-loadable script or temporary Workbench command that starts a localhost MCP endpoint.
- One read-only tool: `get_active_document`.
- One mutating tool: `create_document` or `add_box`.
- Basic logging to a local file.
- Manual dependency check for the official MCP Python SDK.

Acceptance criteria:

- FreeCAD remains responsive after server startup.
- An MCP client can connect to `http://127.0.0.1:<port>/mcp`.
- A read-only tool returns active document state.
- A mutating tool updates the visible FreeCAD session.
- Server shutdown works without restarting FreeCAD.

Key validation:

- Confirm the correct GUI/main-thread dispatch mechanism.
- Confirm MCP SDK compatibility with FreeCAD's bundled Python.
- Confirm whether dependency installation can be automated cleanly.

## Phase 2: Workbench Packaging

Purpose:

Convert the proof of concept into a proper FreeCAD Workbench.

Deliverables:

- `InitGui.py` Workbench registration.
- Toolbar/menu commands:
  - Start MCP Server
  - Stop MCP Server
  - Copy MCP URL
  - Show Server Log
  - Check MCP Dependencies
- Server controller with explicit lifecycle states.
- Workbench-local dependency path support.
- Clear user-facing error messages for missing MCP dependencies.

Acceptance criteria:

- User can enable the Workbench in FreeCAD.
- User can start and stop the server from the GUI.
- Server state and URL are visible.
- Missing dependencies are reported with actionable instructions.

## Phase 3: V1 Tool Implementation

Purpose:

Implement the high-level MCP tool set defined in `mcp-tools.md`.

Deliverables:

- Inspection tools:
  - `get_active_document`
  - `get_selection`
- Document tools:
  - `create_document`
  - `recompute`
  - `save_document`
- Modeling tools:
  - `create_body`
  - `add_box`
  - `add_cylinder`
  - `create_sketch`
  - `add_sketch_geometry`
  - `add_sketch_constraint`
  - `solve_sketch`
  - `pad_sketch`
  - `fillet_edges`
  - `boolean_operation`
- Editing tool:
  - `set_property`
- Export tools:
  - `export_step`
  - `export_stl`

Acceptance criteria:

- Each tool validates input before touching FreeCAD.
- Each mutating tool updates the visible FreeCAD document.
- Each mutating tool either recomputes or reports that recompute is required.
- Document inspection returns local and world transforms for objects and sketches where FreeCAD can compute them.
- Sketch tools support command-based profile creation using sketch-local geometry and constraints.
- Tool outputs are structured and JSON-compatible.
- Errors use the documented error code set.

## Phase 4: Testing

Purpose:

Add enough automated and manual coverage to keep the Workbench stable while tool behavior expands.

Automated tests:

- Schema validation for every MCP tool.
- Tool handler tests with mocked FreeCAD modules where practical.
- Error conversion tests for validation and FreeCAD exceptions.
- Dependency detection tests for present and missing MCP SDK cases.

Integration tests:

- Run only when a supported FreeCAD executable is available.
- Start FreeCAD in an integration-friendly mode if possible.
- Verify document creation, primitive creation, recompute, save, and export.

Manual acceptance scenario:

1. Launch FreeCAD.
2. Enable the Workbench.
3. Start the MCP server.
4. Connect an MCP client to the displayed localhost URL.
5. Create a new document.
6. Add a box.
7. Add a second overlapping solid.
8. Fuse the solids with `boolean_operation`, then subtract one solid from another.
9. Change one dimension with `set_property`.
10. Recompute.
11. Save `.FCStd`.
12. Export STEP and STL.
13. Stop the MCP server.

Acceptance criteria:

- The visible FreeCAD UI updates after mutating tool calls.
- Saved and exported files exist at the expected paths.
- Logs show tool calls and errors without leaking large model data.
- FreeCAD can close cleanly after server shutdown.

## Phase 5: Polish and Hardening

Purpose:

Make the Workbench comfortable enough for repeated local design sessions.

Deliverables:

- Better server status UI.
- Clearer dependency setup flow.
- Port conflict handling.
- More detailed object tree summaries.
- Better recovery from failed recompute.
- Documentation for installation, client connection, and troubleshooting.

Future enhancements:

- Token authentication.
- User approval prompts for destructive edits.
- More sketch creation tools.
- Assembly support.
- TechDraw drawing tools.
- Headless batch mode using `FreeCADCmd`.

## Implementation Defaults

- Use `uv` for repository development and tests outside FreeCAD.
- Use the official MCP Python SDK inside FreeCAD.
- Use Streamable HTTP on `127.0.0.1`.
- Keep arbitrary Python execution out of v1.
- Prefer high-level CAD operations over low-level FreeCAD scripting exposure.
- Treat FreeCAD GUI-thread dispatch as the first proof-of-concept risk to validate.

## Completion Criteria for V1

V1 is complete when:

- The Workbench can be installed or loaded locally.
- The MCP server can be started and stopped from FreeCAD.
- An MCP client can connect to the localhost endpoint.
- The v1 tools can inspect, create, modify, recompute, save, and export a simple parametric part.
- The implementation has validation tests and at least one documented manual acceptance run.
