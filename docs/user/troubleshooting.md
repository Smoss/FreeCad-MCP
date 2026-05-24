# Troubleshooting

## Server Does Not Start

Run `MCP -> Check MCP Dependencies`.

If the MCP SDK is missing, install it through the prompt or manually install `mcp` into the dependency directory shown by the command.

## Port Is Already In Use

The Workbench binds only to `127.0.0.1`. It starts at port `8765` and scans upward when that port is occupied.

Use `MCP -> Copy MCP URL` after startup to avoid connecting to a stale URL.

## Tools Return Recompute Errors

Open `MCP -> Show Server Log` and check the FreeCAD exception. The tool response should also include a structured error code such as `recompute_failed` or `freecad_error`.

After a failed recompute, inspect the visible model tree in FreeCAD, correct the invalid feature or property, and call `recompute` again.

## Exports Fail

Confirm that:

- The export path is absolute.
- The path has the expected suffix: `.step`, `.stp`, or `.stl`.
- The target directory is writable by FreeCAD.
- The document contains visible objects with shapes.

## Local Tests

The repository tests run without FreeCAD by installing mocked FreeCAD modules:

```bash
python3 -m unittest discover -s tests
```

These tests cover schema registration, validation, error conversion paths, primitive creation, property allowlisting, sketch geometry bookkeeping, and port fallback logic. They do not replace a manual FreeCAD GUI acceptance run.

