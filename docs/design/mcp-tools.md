# MCP Tool Contracts

## Overview

This document defines the v1 MCP tool surface for the live FreeCAD MCP Workbench.

All tools must:

- Accept JSON-compatible inputs.
- Validate inputs before touching FreeCAD state.
- Return JSON-compatible outputs.
- Use document and object identifiers instead of raw FreeCAD Python objects.
- Report FreeCAD exceptions as structured errors.
- Avoid arbitrary Python execution.

## Common Types

### Tool Result

Every tool returns one of two shapes.

Success:

```json
{
  "ok": true,
  "data": {}
}
```

Failure:

```json
{
  "ok": false,
  "error": {
    "code": "freecad_error",
    "message": "Human-readable failure message",
    "details": {}
  }
}
```

### Object Reference

```json
{
  "document": "Unnamed",
  "name": "Box",
  "label": "Box",
  "type": "Part::Box"
}
```

Use internal object `Name` for stable lookup within a document. Return `Label` for readability, but do not rely on labels as unique identifiers.

### Placement

```json
{
  "position_mm": [0, 0, 0],
  "rotation_degrees": [0, 0, 0]
}
```

Use millimeters for distances and degrees for user-facing rotations in the MCP schema. Convert to FreeCAD-native values internally.

### Transform

```json
{
  "position_mm": [0, 0, 0],
  "rotation_degrees": [0, 0, 0],
  "matrix": [
    [1, 0, 0, 0],
    [0, 1, 0, 0],
    [0, 0, 1, 0],
    [0, 0, 0, 1]
  ]
}
```

Document inspection must return both local and world transforms for objects when FreeCAD can compute them. Local transform means the object's placement relative to its parent. World transform means the effective placement in document/world coordinates after parent transforms are applied.

## Inspection Tools

### `get_active_document`

Returns the active document summary, including object transforms.

Input:

```json
{}
```

Output data:

```json
{
  "document": {
    "name": "Unnamed",
    "label": "Unnamed",
    "path": null,
    "is_dirty": true
  },
  "objects": [
    {
      "name": "Box",
      "label": "Base",
      "type": "Part::Box",
      "visibility": true,
      "local_transform": {
        "position_mm": [0, 0, 0],
        "rotation_degrees": [0, 0, 0],
        "matrix": [
          [1, 0, 0, 0],
          [0, 1, 0, 0],
          [0, 0, 1, 0],
          [0, 0, 0, 1]
        ]
      },
      "world_transform": {
        "position_mm": [0, 0, 0],
        "rotation_degrees": [0, 0, 0],
        "matrix": [
          [1, 0, 0, 0],
          [0, 1, 0, 0],
          [0, 0, 1, 0],
          [0, 0, 0, 1]
        ]
      },
      "children": []
    }
  ],
  "active_body": null,
  "active_sketch": null
}
```

Behavior:

- If no document is active, return `ok: true` with `document: null`.
- Include enough object metadata for an AI client to refer to existing geometry.
- Include local and world transforms for every object where available.
- Include transform data for sketches so clients can convert between sketch-local coordinates and document/world coordinates.
- Do not recompute or mutate the document.

### `get_selection`

Returns the current FreeCAD GUI selection.

Input:

```json
{}
```

Output data:

```json
{
  "selection": [
    {
      "document": "Unnamed",
      "object": "Box",
      "label": "Base",
      "type": "Part::Box",
      "subelements": ["Face1", "Edge2"]
    }
  ]
}
```

Behavior:

- Requires the FreeCAD GUI selection API.
- Return an empty list if nothing is selected.
- Preserve selection; do not change it.

## Document Tools

### `create_document`

Creates and activates a new FreeCAD document.

Input:

```json
{
  "name": "demo_part"
}
```

Validation:

- `name` is optional.
- If provided, it must be a simple document-safe identifier.

Behavior:

- Create a new document.
- Activate it in FreeCAD.
- Return the document summary.

### `recompute`

Recomputes a document.

Input:

```json
{
  "document": "Unnamed"
}
```

Validation:

- `document` is optional; default to the active document.
- The target document must exist.

Behavior:

- Run FreeCAD recompute.
- Return warnings or errors if recompute fails.

### `save_document`

Saves a document as `.FCStd`.

Input:

```json
{
  "document": "Unnamed",
  "path": "/absolute/path/to/demo.FCStd"
}
```

Validation:

- `document` is optional; default to the active document.
- `path` must be an absolute path ending in `.FCStd`.
- The implementation should restrict saves to user-approved or configured directories.

Behavior:

- Save the document.
- Return the saved path and dirty state.

## Modeling Tools

Boolean operations combine existing solid objects into a new parametric feature. Use them when the requested model needs fused, intersected, or subtracted volume instead of separate overlapping primitives.

## Sketch Interaction Model

Sketch interaction is command-based, not mouse-based. The AI client does not drag points in the FreeCAD UI. Instead, it:

1. Creates or targets a sketch attached to a base plane or selected planar face.
2. Adds geometry in sketch-local 2D coordinates.
3. Adds dimensional and geometric constraints.
4. Solves the sketch and returns constraint/solver status.
5. Uses the sketch as input to a feature such as `pad_sketch`.

The user can still interact normally in FreeCAD. For example, the user can select a face, then the AI can call `create_sketch` with `support.mode: "selection"` to attach a sketch to that face. The sketch transform returned by `get_active_document` lets the AI understand how sketch-local geometry maps back into document/world coordinates.

V1 should support common constrained profile operations. It should not attempt full interactive Sketcher parity or freeform cursor-level editing.

### `create_body`

Creates or activates a Part Design body.

Input:

```json
{
  "document": "Unnamed",
  "label": "Body"
}
```

Validation:

- `document` is optional; default to active document.
- Create a document first if no active document exists only when the caller explicitly requests that behavior in a later version. V1 should return an error.

Behavior:

- Create a `PartDesign::Body` when available.
- Make it active when FreeCAD supports that operation.
- Return the body object reference.

### `add_box`

Creates a parametric box.

Input:

```json
{
  "document": "Unnamed",
  "label": "Base",
  "length_mm": 80,
  "width_mm": 40,
  "height_mm": 12,
  "placement": {
    "position_mm": [0, 0, 0],
    "rotation_degrees": [0, 0, 0]
  }
}
```

Validation:

- Dimensions must be positive finite numbers.
- `document` is optional; default to active document.
- `placement` is optional; default to origin.

Behavior:

- Add a FreeCAD parametric box object.
- Set dimensions and placement.
- Recompute the document.
- Return the new object reference and bounding box metadata.

### `add_cylinder`

Creates a parametric cylinder.

Input:

```json
{
  "document": "Unnamed",
  "label": "Post",
  "radius_mm": 5,
  "height_mm": 20,
  "placement": {
    "position_mm": [0, 0, 0],
    "rotation_degrees": [0, 0, 0]
  }
}
```

Validation:

- Radius and height must be positive finite numbers.
- `placement` is optional; default to origin.

Behavior:

- Add a FreeCAD parametric cylinder object.
- Set dimensions and placement.
- Recompute the document.
- Return the new object reference and bounding box metadata.

### `create_sketch`

Creates a sketch on a base plane or selected face.

Input:

```json
{
  "document": "Unnamed",
  "label": "Profile",
  "support": {
    "mode": "plane",
    "plane": "XY"
  }
}
```

Alternative support:

```json
{
  "mode": "selection"
}
```

Validation:

- Plane must be one of `XY`, `XZ`, or `YZ`.
- Selection support requires exactly one selected planar face.

Behavior:

- Create a sketch.
- Attach it to the requested plane or face.
- Return the sketch-local coordinate frame in the object transform fields exposed by `get_active_document`.
- Return the sketch object reference.

### `add_sketch_geometry`

Adds simple geometry to an existing sketch in sketch-local coordinates.

Input:

```json
{
  "document": "Unnamed",
  "sketch": "Profile",
  "geometry": [
    {
      "type": "rectangle",
      "origin_mm": [0, 0],
      "width_mm": 80,
      "height_mm": 40,
      "construction": false
    },
    {
      "type": "circle",
      "center_mm": [20, 20],
      "radius_mm": 5,
      "construction": false
    }
  ]
}
```

Validation:

- `sketch` must identify an existing sketch.
- Geometry coordinates are sketch-local millimeter values.
- V1 geometry types are `line`, `rectangle`, `circle`, and `arc`.
- Dimensions and radii must be positive finite numbers.

Behavior:

- Add geometry to the sketch.
- Return sketch geometry identifiers that later constraint calls can reference.
- Do not pad or extrude automatically.

### `add_sketch_constraint`

Adds constraints to existing sketch geometry.

Input:

```json
{
  "document": "Unnamed",
  "sketch": "Profile",
  "constraints": [
    {
      "type": "distance_x",
      "geometry": "g1",
      "value_mm": 80
    },
    {
      "type": "radius",
      "geometry": "g5",
      "value_mm": 5
    }
  ]
}
```

Validation:

- `sketch` must identify an existing sketch.
- Referenced geometry identifiers must exist in that sketch.
- V1 constraint types are `coincident`, `horizontal`, `vertical`, `distance`, `distance_x`, `distance_y`, `radius`, `diameter`, `equal`, and `symmetric`.
- Dimensional values must be positive finite numbers when required by the constraint type.

Behavior:

- Add constraints to the sketch.
- Solve the sketch after adding constraints.
- Return solver status, degrees of freedom when available, and any constraint conflicts.

### `solve_sketch`

Solves an existing sketch and reports status.

Input:

```json
{
  "document": "Unnamed",
  "sketch": "Profile"
}
```

Validation:

- `sketch` must identify an existing sketch.

Behavior:

- Ask FreeCAD to solve/recompute the sketch.
- Return whether the sketch is solved, underconstrained, or conflicting when that information is available.

### `pad_sketch`

Pads or extrudes a sketch.

Input:

```json
{
  "document": "Unnamed",
  "sketch": "Profile",
  "length_mm": 10,
  "symmetric": false
}
```

Validation:

- `sketch` must identify an existing sketch.
- `length_mm` must be a positive finite number.

Behavior:

- Create a Part Design pad when the sketch is inside a body.
- Otherwise use the most appropriate FreeCAD extrusion operation and report the resulting object type.
- Recompute the document.

### `fillet_edges`

Applies a fillet to selected or named edges.

Input:

```json
{
  "document": "Unnamed",
  "object": "Base",
  "edges": ["Edge1", "Edge2"],
  "radius_mm": 2
}
```

Validation:

- `radius_mm` must be positive.
- `object` must exist.
- If `edges` is omitted, use the current selected edges.
- If no edges are available, return a validation error.

Behavior:

- Create a fillet feature.
- Recompute the document.
- Return the resulting object reference.

### `boolean_operation`

Creates a parametric boolean feature from two or more solid objects.

Input:

```json
{
  "document": "Unnamed",
  "operation": "difference",
  "objects": ["Base", "Post"],
  "label": "BaseMinusPost"
}
```

Validation:

- `operation` must be `union`, `intersection`, or `difference`.
- `objects` is optional. If provided, it must contain at least two object names.
- If `objects` is omitted, use the current whole-object selection. Subelement selections are ignored.
- At least two operands must be available.
- Each operand must exist and expose a solid shape.

Behavior:

- `union` fuses all operands into a `Part::MultiFuse` feature.
- `intersection` creates the common volume of all operands with a `Part::MultiCommon` feature.
- `difference` subtracts later operands from the first operand with one or more `Part::Cut` features.
- Recompute the document.
- Return the resulting object reference and bounding box when available.
- Leave source objects in the document.

## Editing Tools

### `set_property`

Updates an allowlisted FreeCAD object property.

Input:

```json
{
  "document": "Unnamed",
  "object": "Base",
  "property": "Length",
  "value": 100
}
```

Validation:

- Object must exist.
- Property must be allowlisted for the object type.
- Value must match the expected property type.

Behavior:

- Set the property.
- Recompute the document when the property affects geometry.
- Return the updated object reference and property value.

Initial allowlist:

- Box dimensions: `Length`, `Width`, `Height`.
- Cylinder dimensions: `Radius`, `Height`.
- Common object metadata: `Label`.
- Placement fields through a structured placement update.

## Export Tools

### `export_step`

Exports selected objects or the whole active document to STEP.

Input:

```json
{
  "document": "Unnamed",
  "objects": ["Base"],
  "path": "/absolute/path/to/demo.step"
}
```

Validation:

- `path` must be absolute and end in `.step` or `.stp`.
- If `objects` is omitted, export visible solid objects from the active document.

Behavior:

- Export using FreeCAD's STEP export facilities.
- Return exported path and object references.

### `export_stl`

Exports selected objects or the whole active document to STL.

Input:

```json
{
  "document": "Unnamed",
  "objects": ["Base"],
  "path": "/absolute/path/to/demo.stl",
  "linear_deflection": 0.1,
  "angular_deflection": 0.5
}
```

Validation:

- `path` must be absolute and end in `.stl`.
- Deflection values are optional and must be positive if provided.

Behavior:

- Export mesh data using FreeCAD mesh export facilities.
- Return exported path and object references.

## Error Codes

Recommended v1 error codes:

- `validation_error`
- `no_active_document`
- `document_not_found`
- `object_not_found`
- `selection_error`
- `unsupported_operation`
- `freecad_error`
- `recompute_failed`
- `export_failed`
- `dependency_missing`

## Out of Scope for V1

- Arbitrary Python execution.
- Generated macro execution.
- Remote clients beyond localhost.
- Assembly constraints.
- TechDraw drawing generation.
- Full interactive Sketcher parity or cursor-level sketch editing.
- Long-running job management.
