# FreeCAD MCP Workbench Design

## Purpose

This document defines the architecture for a FreeCAD Workbench that exposes a live FreeCAD GUI session through the Model Context Protocol (MCP). The goal is to let an AI client inspect and modify the currently open FreeCAD document through a small, high-level tool surface.

This is a design document only. It does not define an implementation scaffold, install dependencies, or modify FreeCAD.

## Goals

- Run the MCP server inside the live FreeCAD GUI process.
- Let an MCP client inspect the active document, current selection, and relevant object metadata.
- Let an MCP client perform controlled CAD operations that update the visible FreeCAD session.
- Keep v1 focused on high-level, typed tools rather than arbitrary Python execution.
- Package the integration as a FreeCAD Workbench so it can become a reusable local design tool.

## Non-Goals

- Do not support arbitrary Python macro execution in v1.
- Do not support remote network access in v1.
- Do not require headless batch generation as the primary workflow.
- Do not build a custom CAD kernel or replace FreeCAD modeling semantics.
- Do not attempt Addon Manager distribution until the local Workbench is proven.

## Architecture

The selected architecture is:

```text
AI MCP client
  -> Streamable HTTP on 127.0.0.1
  -> MCP server running inside FreeCAD Python
  -> FreeCAD GUI process
  -> active FreeCAD document and selection
```

The MCP server is loaded by the FreeCAD Workbench and shares the same Python process as FreeCAD. Tool handlers call FreeCAD APIs directly, which allows them to read and mutate the live document the user is viewing.

This differs from a headless `FreeCADCmd` design. A headless design is easier to isolate, but it cannot naturally interact with the active GUI document, current selection, or visible recompute state.

## Runtime Model

The Workbench owns the MCP server lifecycle:

- FreeCAD starts normally.
- The user activates the Workbench.
- The user runs a "Start MCP Server" command.
- The Workbench starts a localhost Streamable HTTP MCP endpoint.
- The MCP client connects to the displayed endpoint.
- Tool calls are routed to FreeCAD-aware handlers.
- Mutating handlers dispatch document changes safely into FreeCAD's GUI/main-thread context.
- The user can stop the server from the Workbench.

The server should not start automatically on FreeCAD launch in v1. Manual start keeps the exposure window obvious and user controlled.

## Transport

Use MCP Streamable HTTP for v1.

- Bind address: `127.0.0.1`.
- Endpoint path: `/mcp`.
- Port: choose a default, then fall back to the next available local port if occupied.
- Visibility: show the active endpoint in FreeCAD status UI and provide a "Copy MCP URL" command.

Do not bind to `0.0.0.0` or any LAN interface in v1.

## Dependency Strategy

Use the official MCP Python SDK inside FreeCAD's Python environment.

The Workbench should include a dependency check command that:

- Detects the Python executable and version used by FreeCAD.
- Checks whether the MCP SDK can be imported.
- If missing, installs the SDK into a Workbench-local dependency directory.
- Adds that dependency directory to `sys.path` before server startup.
- Reports clear errors when installation is not possible.

The dependency directory should live under the user's FreeCAD application data or the Workbench directory, not inside system Python.

Open question: FreeCAD distributions vary by platform and bundled Python version. The implementation must verify whether `pip` is available in the target FreeCAD Python. If not, it may need to bootstrap dependencies from a normal Python environment or provide a documented manual install path.

## Workbench UI

The Workbench should expose a small command set:

- Start MCP Server
- Stop MCP Server
- Copy MCP URL
- Show Server Log
- Check MCP Dependencies

The UI should show server state:

- stopped
- starting
- running with endpoint URL
- failed with actionable error

The Workbench should avoid changing the user's active modeling Workbench except when a requested operation requires a specific FreeCAD context.

## Safety Model

V1 uses localhost-only safety.

- The MCP server binds only to `127.0.0.1`.
- The server is manually started by the user.
- The server stops when requested by the user or when FreeCAD exits.
- Tool calls are high-level and schema validated.
- Arbitrary Python execution is not exposed.

Future enhancement: add token authentication. The Workbench can generate a per-session token, display it in FreeCAD, and require MCP clients to provide it with each request.

## Tool Surface

V1 exposes high-level CAD tools only. The detailed contracts are defined in `mcp-tools.md`.

The initial tool categories are:

- Session inspection: active document, object tree, selection.
- Transform inspection: local and world transforms for objects and sketches.
- Document control: create, activate, save, recompute.
- Primitive creation: box, cylinder.
- Part Design setup: create or activate body.
- Sketch workflow: create sketch, add constrained geometry, solve, and pad sketch.
- Feature editing: property updates, fillets, and boolean union/intersection/difference.
- Export: STEP and STL.

Tool handlers return structured JSON-compatible data. They should not return raw FreeCAD Python objects.

Sketch interaction is not mouse-driven in v1. The AI client interacts with sketches by sending typed geometry and constraint operations in sketch-local coordinates. A user can select a face in the FreeCAD UI, then the AI can attach a sketch to that selected face. Document inspection returns sketch transforms so the client can reason about how sketch-local profiles relate to the surrounding model.

## FreeCAD Threading and Recompute

FreeCAD GUI operations are sensitive to thread context. The implementation must not assume that MCP request handlers can safely mutate documents from arbitrary HTTP worker threads.

Required implementation rule:

- Mutating tool calls must be executed on FreeCAD's GUI/main-thread context or through a FreeCAD-safe scheduling mechanism.
- Each mutating operation must recompute when needed or clearly report that recompute is pending.
- Recompute failures must be returned as structured errors and logged.

Open question: the exact dispatch mechanism should be validated in a proof of concept. Candidates include Qt signal dispatch, `QTimer.singleShot`, or a FreeCAD-supported GUI callback pattern.

## Logging and Diagnostics

The Workbench should keep a local log file with:

- Server start and stop events.
- Endpoint and port selection.
- Dependency check results.
- MCP tool names and request IDs.
- Tool success or failure.
- FreeCAD exceptions and recompute errors.

Logs must not include large binary model data.

## Known Risks

- FreeCAD Python packaging differs across macOS, Windows, Linux, AppImage, and Conda builds.
- Official MCP SDK dependencies may not install cleanly into all FreeCAD Python distributions.
- GUI-thread dispatch may need platform-specific validation.
- FreeCAD object naming and topological references can change after model edits.
- Long-running CAD operations can block the UI unless carefully scheduled.

## Success Criteria

The design is implemented successfully when a user can:

- Install or load the Workbench locally.
- Start the MCP server from FreeCAD.
- Connect an MCP client to the displayed localhost URL.
- Create or inspect a document.
- Add a primitive feature.
- Modify a parameter.
- Recompute and see the live FreeCAD UI update.
- Save the document and export STEP/STL files.
