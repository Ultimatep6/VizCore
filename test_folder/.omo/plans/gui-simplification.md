# GUI Simplification Refactor

## TL;DR

> **Quick Summary**: Unify the GUI/widget system's coordinate system, rendering pipeline, and APIs to make widgets easy to create and use. Replace 7-step widget setup with one call, eliminate coordinate confusion, and consolidate three redundant rendering pipelines into one.
>
> **Deliverables**:
> - Bottom-up coordinate system everywhere (no Y-flips)
> - Single `DrawingContext` for all 2D UI rendering
> - One-call widget creation: `widget_manager.add_widget(tile, "Line Plot")`
> - Widgets receive local coordinates only
> - Context menus rendered through the same pipeline as tile popups
> - Regression tests for all coordinate, event, and rendering logic
>
> **Estimated Effort**: Large
> **Parallel Execution**: YES — 5 waves
> **Critical Path**: Phase 0 tests → Phase 1 coordinates → Phase 2 rendering → Phase 3+4 lifecycle/API → Phase 6 menu → F1-F4 verification

---

## Context

### Original Request
User asked to outline challenges and develop a plan to simplify the GUI/widget system so that potential users can easily create and use widgets. After 23 minutes of debugging the LinePlot widget integration, the fundamental complexity became clear.

### Interview Summary
**Key Discussions**:
- Coordinate system: 15+ flip sites across 6 Python files + 3 GLSL shaders
- Three separate rendering pipelines with duplicate shaders/VBOs
- DrawingContext created and destroyed every frame per widget
- 7-step widget setup requiring manual Y-flip coordinate conversion
- Event forwarding through 5 layers with different coordinate assumptions
- MenuRenderer and GuiRenderer are redundant (both draw rectangles + text + outlines)

**Research Findings**:
- Test coverage: DataBus/SignalSchema well-tested (25+ tests), but coordinate conversion, rendering, events, menus, and tile management have ZERO tests
- MenuRenderer is actually a state machine + layout engine (not redundant with GuiRenderer), but DrawingContext and GuiRenderer ARE redundant
- Ctrl toggle is a mode switch (EDIT vs VIEW) with 6+ scattered branches
- Window resize does not resize widgets
- No widget teardown/cleanup on destruction
- Bare imports in settings_gui/elements/ will break when merging

### Metis Review
**Identified Gaps** (addressed):
- Phase 0 (regression tests) must come BEFORE Phase 1 (coordinate unification)
- TileManager rewrite is highest-risk change
- Blend state inconsistency between DrawingContext and GuiRenderer
- Class-level `_initialized` survives context loss
- vizcore/ legacy package has its own WidgetManager — out of scope

---

## Work Objectives

### Core Objective
Simplify the GUI/widget system by unifying coordinates (bottom-up everywhere), merging redundant rendering pipelines into a single `DrawingContext`, and reducing widget setup from 7 steps to one call.

### Concrete Deliverables
- All coordinates bottom-up (remove 15+ Y-flip sites)
- Single shader program + VBO set for all 2D UI
- One `DrawingContext` per widget, created at setup, reused every frame
- `widget_manager.add_widget(tile, "Name")` encapsulates all setup
- Widgets receive local coordinates (0,0 at tile bottom-left)
- Context menus rendered via same `GuiRenderer` as tile popups
- Regression tests for coordinate math, tile geometry, events, menus, DC lifecycle

### Definition of Done
- [ ] `python -m unittest discover -s tests` passes (all existing + new tests)
- [ ] Visual verification: tile borders render correctly, popups at click position, widgets in correct quadrants
- [ ] Widget creation works in one call
- [ ] Menu click triggers correct callback

### Must Have
- Bottom-up coordinate system everywhere
- Single DrawingContext for all 2D UI rendering
- One-call widget creation API
- Widgets receive local coordinates
- Context menus work through unified pipeline
- Regression tests for all refactored areas
- Preserve ctrl toggle behavior (EDIT vs VIEW mode)

### Must NOT Have (Guardrails)
- NO changes to simulation logic or data_bus
- NO changes to vizcore/ legacy package
- NO new features (mouse-move forwarding, new widget types)
- NO removal of gui_playground.py without confirming it's dead code
- AI slop patterns to avoid:
  - Excessive comments explaining obvious code
  - Over-abstraction (interfaces for things with one implementation)
  - Generic names (data/result/item/temp)
  - Leaving commented-out code

---

## Verification Strategy

> **ZERO HUMAN INTERVENTION** — ALL verification is agent-executed. No exceptions.

### Test Decision
- **Infrastructure exists**: YES (unittest)
- **Automated tests**: Phase 0 writes characterization tests BEFORE refactoring
- **Framework**: unittest (stdlib)
- **Command**: `python -m unittest discover -s tests -v`

### QA Policy
Every task MUST include agent-executed QA scenarios.
Evidence saved to `.omo/evidence/task-{N}-{scenario-slug}.{ext}`.

- **Frontend/UI**: Use Playwright (playwright skill) — Navigate, interact, assert DOM, screenshot
- **TUI/CLI**: Use interactive_bash (tmux) — Run command, send keystrokes, validate output
- **API/Backend**: Use Bash (curl) — Send requests, assert status + response fields
- **Library/Module**: Use Bash (python -m unittest) — Run tests, assert PASS

---

## Execution Strategy

### Parallel Execution Waves

```
Wave 1 (Phase 0 — Regression Tests, all independent):
├── Task 1:  Test coordinate conversion math
├── Task 2:  Test tile split/merge/resize geometry
├── Task 3:  Test WidgetManager event forwarding
├── Task 4:  Test menu state machine
└── Task 5:  Test DrawingContext lifecycle

Wave 2 (Phase 1 — Coordinate Unification, depends on Wave 1):
├── Task 6:  Tile stores bottom-up coordinates
├── Task 7:  TileManager uses bottom-up logic
├── Task 8:  Remove shader Y-flips
├── Task 9:  Remove GuiManager/BlipGui/model_aligner flips
├── Task 10: Remove MenuRenderer/WidgetManager flips
└── Task 11: Update mouse event handling

Wave 3 (Phase 2 Rendering + Phase 5 Events, depends on Wave 2):
├── Task 12: GuiRenderer wraps DrawingContext
├── Task 13: Delete duplicate shaders
├── Task 14: Fix bare imports in settings_gui/elements/
├── Task 15: Standardize blend state policy
├── Task 16: WidgetManager screen→local conversion
└── Task 17: Remove modifiers from widget event methods

Wave 4 (Phase 3 DC Lifecycle + Phase 4 Widget API, depends on Wave 3):
├── Task 18: Cache DrawingContext per widget
├── Task 19: DC offset/resolution methods
├── Task 20: Remove per-frame DC creation
├── Task 21: add_widget one-call API
├── Task 22: Widget.teardown() and destroy_widget cleanup
└── Task 23: Update all callers of create_widget

Wave 5 (Phase 6 — Unified Menu, depends on Wave 3+4):
├── Task 24: MenuRenderer returns data structure only
├── Task 25: WidgetManager renders context menus via GuiRenderer
└── Task 26: Update LinePlot.get_context_menu() if needed

Wave FINAL (After ALL tasks — 4 parallel reviews, then user okay):
├── Task F1: Plan compliance audit (oracle)
├── Task F2: Code quality review (unspecified-high)
├── Task F3: Real manual QA (unspecified-high)
└── Task F4: Scope fidelity check (deep)
-> Present results -> Get explicit user okay

Critical Path: T1-5 → T6-11 → T12-17 → T18-23 → T24-26 → F1-F4 → user okay
Parallel Speedup: ~60% faster than sequential
Max Concurrent: 6 (Wave 2)
```

### Dependency Matrix

| Task | Depends On | Blocks |
|---|---|---|
| 1-5 | — | 6-11 |
| 6 | — | 7, 8, 12 |
| 7 | 6 | 9, 10, 16 |
| 8 | 6 | 12 |
| 9 | 7 | 16 |
| 10 | 7 | 16, 25 |
| 11 | 6, 7, 8, 9, 10 | 16 |
| 12 | 8 | 18, 24, 25 |
| 13 | 12 | — |
| 14 | 12 | — |
| 15 | 12 | 24, 25 |
| 16 | 9, 10, 11 | 21, 23 |
| 17 | 9, 10, 11, 16 | 23 |
| 18 | 12 | 20, 21 |
| 19 | 12 | 18 |
| 20 | 18 | 21 |
| 21 | 16, 18, 20 | 22, 23 |
| 22 | 21 | 23 |
| 23 | 17, 21, 22 | — |
| 24 | 12, 15 | 25 |
| 25 | 10, 24 | 26 |
| 26 | 25 | — |

### Agent Dispatch Summary

| Wave | Tasks | Categories |
|---|---|---|
| 1 | 5 | T1-T5 → `quick` (tests) |
| 2 | 6 | T6-T8 → `unspecified-high`, T9-T11 → `quick` |
| 3 | 6 | T12-T15 → `unspecified-high`, T16-T17 → `quick` |
| 4 | 6 | T18-T20 → `unspecified-high`, T21-T23 → `quick` |
| 5 | 3 | T24-T26 → `unspecified-high` |
| FINAL | 4 | F1 → `oracle`, F2 → `unspecified-high`, F3 → `unspecified-high`, F4 → `deep` |

---

## TODOs

- [x] 1. Write regression tests for coordinate conversion math

  **What to do**:
  - Create `tests/test_coordinates.py`
  - Test the 15+ Y-flip sites: `window_h - tile.y - tile.height`, `win_h - y`, `_flip()`, `ndc.y = -ndc.y`
  - For each site, write a test that verifies: given top-down input → produces correct bottom-up output
  - Test edge cases: (0,0), (max_x, max_y), window resize, negative coordinates
  - Test that NO flip produces same output as current flip (characterization tests)
  - Use `unittest.TestCase`, follow `test_widget_integration.py` pattern
  - Use `MockTile` or simple tuple fixtures (no GPU needed)

  **Must NOT do**:
  - Do not test GPU rendering (that's for Task 5)
  - Do not change any source code — these are characterization tests for existing behavior

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Pure Python math tests, no GPU or window needed
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 2, 3, 4, 5)
  - **Blocks**: Tasks 6-11 (coordinate unification)
  - **Blocked By**: None

  **References**:
  - `tests/test_widget_integration.py` — Test structure and `MockTile` pattern
  - `widgets/manager.py:78` — `bottom_up_y = window_h - tile.y - tile.height` (flip to test)
  - `settings_gui/guiManager.py` — `self._win_h - y` flips
  - `widgets/widget_gui.py:122-123` — `_flip() = self._win_h - y`
  - `tile_management/shaders/tile_border.vert:23` — `ndc.y = -ndc.y`

  **Acceptance Criteria**:
  - [ ] `python -m unittest tests.test_coordinates -v` → PASS (≥10 tests)
  - [ ] Each test has concrete expected values (not vague assertions)
  - [ ] Both happy-path and edge-case scenarios covered

  **QA Scenarios**:
  ```
  Scenario: Coordinate flip characterization
    Tool: Bash (python -m unittest)
    Preconditions: tests/test_coordinates.py exists
    Steps:
      1. Run: python -m unittest tests.test_coordinates -v
      2. Assert: All tests PASS, no failures
    Expected Result: ≥10 tests pass, 0 failures
    Evidence: .omo/evidence/task-1-coord-tests.txt
  ```

  **Evidence to Capture**:
  - [ ] Test output saved to `.omo/evidence/task-1-coord-tests.txt`

  **Commit**: YES
  - Message: `test(gui): add coordinate conversion regression tests`
  - Files: `tests/test_coordinates.py`

- [x] 2. Write regression tests for tile split/merge/resize geometry

  **What to do**:
  - Create `tests/test_tile_geometry.py`
  - Test `TileManager._init_tiles()` — verify tile positions and dimensions
  - Test `TileManager.split_focused_tile()` — verify split produces correct sub-tile positions
  - Test `TileManager.merge()` — verify merge produces correct combined tile
  - Test `TileManager.resize_border()` — verify resize changes dimensions correctly
  - Test `TileManager.get_border_at()` — verify border detection at edges
  - Test `TileManager.get_tile_index()` — verify tile lookup at various positions
  - Use characterization approach: test current top-down behavior, document expected values
  - These will become the safety net when we flip to bottom-up in Phase 1

  **Must NOT do**:
  - Do not change TileManager source code
  - Do not test rendering (pure geometry math)

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Pure geometry math, no GPU
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 1, 3, 4, 5)
  - **Blocks**: Tasks 6-7 (TileManager coordinate changes)
  - **Blocked By**: None

  **References**:
  - `tests/test_widget_integration.py` — Test structure pattern
  - `tile_management/manager.py` — TileManager methods to test
  - `tile_management/tiles.py` — Tile class structure

  **Acceptance Criteria**:
  - [ ] `python -m unittest tests.test_tile_geometry -v` → PASS (≥6 tests)
  - [ ] Tests cover split, merge, resize, border detection, tile lookup
  - [ ] Concrete position/dimension assertions (e.g., `assert tile.width == 400`)

  **QA Scenarios**:
  ```
  Scenario: Tile geometry characterization
    Tool: Bash (python -m unittest)
    Preconditions: tests/test_tile_geometry.py exists
    Steps:
      1. Run: python -m unittest tests.test_tile_geometry -v
      2. Assert: All tests PASS
    Expected Result: ≥6 tests pass, 0 failures
    Evidence: .omo/evidence/task-2-tile-geom-tests.txt
  ```

  **Commit**: YES (groups with Task 1)

- [x] 3. Write regression tests for WidgetManager event forwarding

  **What to do**:
  - Create `tests/test_event_forwarding.py`
  - Test `WidgetManager.on_mouse_press(x, y, button)`:
    - Click inside widget → forwards to correct widget
    - Click outside all widgets → does not forward
    - Click on widget border → correct behavior
  - Test coordinate translation: verify screen (x,y) → widget-local (x,y)
  - Test ctrl mode: verify ctrl+click routes to tile popup, not widget
  - Test `WidgetManager.on_mouse_release`, `on_mouse_drag`, `on_mouse_scroll`
  - Mock the widget class (don't need real ModernGL context)

  **Must NOT do**:
  - Do not test actual GPU rendering
  - Do not test menu interaction (that's Task 4)

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Event routing logic, no rendering
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 1, 2, 4, 5)
  - **Blocks**: Tasks 16-17 (event handling refactor)
  - **Blocked By**: None

  **References**:
  - `widgets/manager.py` — WidgetManager event methods
  - `tests/test_widget_integration.py` — Mock patterns
  - `mainLoop.py:128` — Ctrl+click routing

  **Acceptance Criteria**:
  - [ ] `python -m unittest tests.test_event_forwarding -v` → PASS (≥4 tests)
  - [ ] Tests cover press/release/drag/scroll forwarding
  - [ ] Tests verify correct widget receives event

  **QA Scenarios**:
  ```
  Scenario: Event forwarding characterization
    Tool: Bash (python -m unittest)
    Preconditions: tests/test_event_forwarding.py exists
    Steps:
      1. Run: python -m unittest tests.test_event_forwarding -v
      2. Assert: All tests PASS
    Expected Result: ≥4 tests pass, 0 failures
    Evidence: .omo/evidence/task-3-event-tests.txt
  ```

  **Commit**: YES (groups with Tasks 1-2)

- [x] 4. Write regression tests for menu state machine

  **What to do**:
  - Create `tests/test_menu_state.py`
  - Test `MenuRenderer.open(x, y, entries)`:
    - Menu opens at correct position
    - Menu closes with `close()`
    - Menu is visible after open, not visible after close
  - Test `MenuRenderer.on_mouse_press(x, y, button)`:
    - Click on menu item → triggers callback
    - Click outside menu → closes menu
    - Click on branch → opens submenu
  - Test `MenuRenderer._clamp()` — verify menu stays within window bounds
  - Test `MenuRenderer._push_sub_level()` — verify submenu positioning
  - Mock DrawingContext (don't need real GPU)

  **Must NOT do**:
  - Do not test rendering (mock DrawingContext)
  - Do not change MenuRenderer source

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: State machine logic, no rendering
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 1, 2, 3, 5)
  - **Blocks**: Tasks 24-26 (menu refactor)
  - **Blocked By**: None

  **References**:
  - `widgets/widget_gui.py` — MenuRenderer class
  - `tests/test_widget_integration.py` — Mock patterns

  **Acceptance Criteria**:
  - [ ] `python -m unittest tests.test_menu_state -v` → PASS (≥5 tests)
  - [ ] Tests cover open, close, click item, click outside, branch expansion, clamping
  - [ ] Tests use concrete expected values (e.g., `assert menu.x == 100`)

  **QA Scenarios**:
  ```
  Scenario: Menu state machine characterization
    Tool: Bash (python -m unittest)
    Preconditions: tests/test_menu_state.py exists
    Steps:
      1. Run: python -m unittest tests.test_menu_state -v
      2. Assert: All tests PASS
    Expected Result: ≥5 tests pass, 0 failures
    Evidence: .omo/evidence/task-4-menu-tests.txt
  ```

  **Commit**: YES (groups with Tasks 1-3)

- [x] 5. Write regression tests for DrawingContext lifecycle

  **What to do**:
  - Create `tests/test_drawing_context.py`
  - Test `DrawingContext.__init__()` — creates shader program, VBOs, VAOs
  - Test that `quad()` sets all uniforms (`u_pos`, `u_size`, `u_color`) before rendering
  - Test that uniform values don't leak between consecutive `quad()` calls
  - Test `set_offset(x, y)` and `set_resolution(w, h)` methods (add them if not present)
  - Test that multiple DrawingContext instances share the shader program (class-level)
  - Test that VAOs are cached (not created per call)
  - Use headless ModernGL context (follow `test_widget_integration.py` pattern)

  **Must NOT do**:
  - Do not test actual pixel rendering (headless context)
  - Do not change DrawingContext source (characterization tests)

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: GPU setup tests but no visual verification needed
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 1, 2, 3, 4)
  - **Blocks**: Tasks 18-20 (DC lifecycle refactor)
  - **Blocked By**: None

  **References**:
  - `widgets/widget_base.py` — DrawingContext class
  - `tests/test_widget_integration.py` — Headless ModernGL context setup
  - `settings_gui/guiRenderer.py` — Compare with GuiRenderer's resource management

  **Acceptance Criteria**:
  - [ ] `python -m unittest tests.test_drawing_context -v` → PASS (≥4 tests)
  - [ ] Tests verify uniform setting, VAO caching, shared shader
  - [ ] Tests run in headless context (no window)

  **QA Scenarios**:
  ```
  Scenario: DrawingContext lifecycle characterization
    Tool: Bash (python -m unittest)
    Preconditions: tests/test_drawing_context.py exists
    Steps:
      1. Run: python -m unittest tests.test_drawing_context -v
      2. Assert: All tests PASS
    Expected Result: ≥4 tests pass, 0 failures
    Evidence: .omo/evidence/task-5-dc-tests.txt
  ```

  **Commit**: YES
  - Message: `test(gui): add DrawingContext lifecycle regression tests`
  - Files: `tests/test_drawing_context.py`

- [x] 6. Convert Tile to store bottom-up coordinates

  **What to do**:
  - In `tile_management/tiles.py`, change `Tile.__init__()`:
    - Currently stores x, y as top-down (y=0 at top)
    - Change to store y as bottom-up (y=0 at bottom of window)
    - `self.y = window_height - y - height` → becomes `self.y = y` (already bottom-up if caller passes bottom-up)
  - Update `Tile` docstring to clarify coordinate system
  - All other tile attributes (width, height, row, col, widget) remain unchanged
  - Ensure `Tile.set_widget()` still works (widget is a string, not instance)

  **Must NOT do**:
  - Do NOT change TileManager yet (Task 7)
  - Do NOT change any rendering code yet
  - Do NOT change the widget attribute type (keep as string)

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Simple data structure change
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (with Task 8)
  - **Parallel Group**: Wave 2 (with Tasks 7-11)
  - **Blocks**: Tasks 7, 9, 10 (TileManager and renderers depend on Tile coords)
  - **Blocked By**: Task 2 (tile geometry tests)

  **References**:
  - `tile_management/tiles.py` — Tile class
  - `tests/test_tile_geometry.py` — Update tests to match new coordinate system

  **Acceptance Criteria**:
  - [ ] `python -m unittest tests.test_tile_geometry -v` → PASS (updated for bottom-up)
  - [ ] Tile stores y as bottom-up coordinate
  - [ ] All Tile properties accessible and correct

  **QA Scenarios**:
  ```
  Scenario: Tile bottom-up coordinates
    Tool: Bash (python -m unittest)
    Preconditions: Tile updated, tests updated
    Steps:
      1. Run: python -m unittest tests.test_tile_geometry -v
      2. Assert: All tests PASS
    Expected Result: 0 failures
    Evidence: .omo/evidence/task-6-tile-coords.txt
  ```

  **Commit**: YES
  - Message: `refactor(tile): store bottom-up coordinates in Tile`
  - Files: `tile_management/tiles.py`, `tests/test_tile_geometry.py`

- [x] 7. Convert TileManager to bottom-up logic

  **What to do**:
  - In `tile_management/manager.py`, update ALL methods that assume top-down:
    - `_init_tiles()`: Calculate tile positions in bottom-up from the start
    - `get_tile_index(x, y)`: Compare using bottom-up (y=0 at bottom)
    - `split_focused_tile()`: When splitting, new tile positions use bottom-up math
    - `merge()`: Combined tile position uses bottom-up
    - `resize_border()`: Resize math uses bottom-up
    - `get_border_at(x, y)`: Border detection uses bottom-up
    - `render()`: Pass bottom-up coordinates to shader
  - Update `TileManager.render()` vertex data generation to emit bottom-up coordinates
  - Remove any `win_h - y` conversions in TileManager

  **Must NOT do**:
  - Do NOT change shaders yet (Task 8)
  - Do NOT change how tiles are displayed (visual check comes after shader update)

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: Complex geometry logic, highest risk change
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: NO (depends on Task 6)
  - **Parallel Group**: Wave 2
  - **Blocks**: Tasks 9, 10, 11 (other components depend on TileManager)
  - **Blocked By**: Task 6

  **References**:
  - `tile_management/manager.py` — All methods
  - `tests/test_tile_geometry.py` — Safety net
  - `tile_management/tiles.py` — Tile now uses bottom-up

  **Acceptance Criteria**:
  - [ ] `python -m unittest tests.test_tile_geometry -v` → PASS
  - [ ] All TileManager methods use bottom-up consistently
  - [ ] No `win_h - y` or similar flips remain in TileManager

  **QA Scenarios**:
  ```
  Scenario: TileManager bottom-up geometry
    Tool: Bash (python -m unittest)
    Preconditions: TileManager updated
    Steps:
      1. Run: python -m unittest tests.test_tile_geometry -v
      2. Assert: All tests PASS
    Expected Result: 0 failures
    Evidence: .omo/evidence/task-7-tile-manager.txt
  ```

  **Commit**: YES
  - Message: `refactor(tile): bottom-up coordinates in TileManager`
  - Files: `tile_management/manager.py`

- [x] 8. Remove Y-flip from tile border and background shaders

  **What to do**:
  - In `tile_management/shaders/tile_border.vert`:
    - Remove `ndc.y = -ndc.y;` line
    - Vertex data now comes in bottom-up, so no flip needed
  - In `settings_gui/shaders/tile_border.vert`:
    - Same: remove `ndc.y = -ndc.y;`
  - In `settings_gui/shaders/tile_bg.vert`:
    - Same: remove `ndc.y = -ndc.y;`
  - Verify that vertex data passed to these shaders is now bottom-up
    - `TileManager.render()` should pass bottom-up coordinates
    - `GuiRenderer` (settings tiles) should pass bottom-up coordinates

  **Must NOT do**:
  - Do NOT change shader inputs (still receive pixel coordinates)
  - Do NOT change fragment shaders (only vertex shaders flip)

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Simple shader edits, high impact
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (with Task 6)
  - **Parallel Group**: Wave 2
  - **Blocks**: Tasks 12-15 (rendering pipeline depends on correct coordinates)
  - **Blocked By**: Task 6 (Tile must be bottom-up first)

  **References**:
  - `tile_management/shaders/tile_border.vert` — Remove flip
  - `settings_gui/shaders/tile_border.vert` — Remove flip
  - `settings_gui/shaders/tile_bg.vert` — Remove flip
  - `tile_management/manager.py` — Verify render() passes bottom-up

  **Acceptance Criteria**:
  - [ ] No `ndc.y = -ndc.y` remains in any shader file
  - [ ] `grep -r "ndc.y = -ndc.y" tile_management/ settings_gui/` returns empty
  - [ ] Tile borders render correctly (visual check in Task 11)

  **QA Scenarios**:
  ```
  Scenario: Shader flip removal
    Tool: Bash (grep)
    Preconditions: Shaders edited
    Steps:
      1. Run: grep -r "ndc.y = -ndc.y" tile_management/ settings_gui/
      2. Assert: No matches found
    Expected Result: Empty output
    Evidence: .omo/evidence/task-8-shader-flip.txt
  ```

  **Commit**: YES (groups with Tasks 6-7)

- [x] 9. Remove Y-flip from GuiManager, BlipGui, and model_aligner

  **What to do**:
  - In `settings_gui/guiManager.py`:
    - Find all `self._win_h - y` conversions (5+ sites)
    - Remove the flip — mouse events are now bottom-up
    - Update `show_popup()`, `on_mouse_press()`, `on_mouse_release()`, `on_mouse_move()`, `on_mouse_drag()`
  - In `settings_gui/blipGui.py`:
    - Find all `self._win_h - y` conversions (4+ sites)
    - Remove the flip
  - In `window/model_aligner.py`:
    - Find all `self.renderer.height - y` conversions (3+ sites)
    - Remove the flip
  - Update any popup/menu positioning that relied on top-down input

  **Must NOT do**:
  - Do NOT change the ctrl toggle logic (just remove the Y-flip, keep the branching)
  - Do NOT change how popups look (only their coordinate math)

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Coordinate math removal across 3 files
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (with Tasks 10, 11)
  - **Parallel Group**: Wave 2
  - **Blocks**: Tasks 16-17 (event handling uses these coordinates)
  - **Blocked By**: Task 7 (TileManager must be bottom-up first)

  **References**:
  - `settings_gui/guiManager.py` — 5+ flip sites
  - `settings_gui/blipGui.py` — 4+ flip sites
  - `window/model_aligner.py` — 3+ flip sites
  - `tests/test_coordinates.py` — Safety net

  **Acceptance Criteria**:
  - [ ] `grep -r "win_h - y\|height - y" settings_gui/ window/` returns no matches (except in comments)
  - [ ] `python -m unittest tests.test_coordinates -v` → PASS
  - [ ] Popup menus appear at click position (visual check in Task 11)

  **QA Scenarios**:
  ```
  Scenario: GUI flip removal
    Tool: Bash (grep)
    Preconditions: Files edited
    Steps:
      1. Run: grep -r "win_h - y\|height - y" settings_gui/ window/
      2. Assert: No flip matches found
    Expected Result: Empty output
    Evidence: .omo/evidence/task-9-gui-flip.txt
  ```

  **Commit**: YES (groups with Tasks 6-8)

- [x] 10. Remove Y-flip from MenuRenderer and WidgetManager

  **What to do**:
  - In `widgets/widget_gui.py`:
    - Remove `_flip()` method entirely
    - Update `open()`, `on_mouse_press()`, `on_mouse_move()`, `on_mouse_release()` to use y directly (bottom-up)
    - Update `_clamp()` if it uses window height
  - In `widgets/manager.py`:
    - Remove `bottom_up_y = window_h - tile.y - tile.height` in `create_widget()`
    - Store tile coordinates directly (now bottom-up)
    - Update `_find_widget_at()` to use bottom-up coordinates
    - Update `render_all()` to use bottom-up for DrawingContext offset

  **Must NOT do**:
  - Do NOT change MenuRenderer's state machine logic (only coordinate math)
  - Do NOT change how widget creation works (just the flip)

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Coordinate math removal in 2 files
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (with Tasks 9, 11)
  - **Parallel Group**: Wave 2
  - **Blocks**: Tasks 16, 24-26 (event and menu refactor)
  - **Blocked By**: Task 7

  **References**:
  - `widgets/widget_gui.py` — MenuRenderer class
  - `widgets/manager.py` — WidgetManager class
  - `tests/test_coordinates.py` — Safety net
  - `tests/test_menu_state.py` — Update tests to use bottom-up

  **Acceptance Criteria**:
  - [ ] `grep -r "_flip\|bottom_up_y\|win_h - tile" widgets/` returns empty
  - [ ] `python -m unittest tests.test_coordinates tests.test_menu_state -v` → PASS
  - [ ] Menu appears at correct position (visual check in Task 11)

  **QA Scenarios**:
  ```
  Scenario: Widget flip removal
    Tool: Bash (grep + unittest)
    Preconditions: Files edited
    Steps:
      1. Run: grep -r "_flip\|bottom_up_y" widgets/
      2. Assert: No matches
      3. Run: python -m unittest tests.test_coordinates tests.test_menu_state -v
      4. Assert: All PASS
    Expected Result: Empty grep + 0 test failures
    Evidence: .omo/evidence/task-10-widget-flip.txt
  ```

  **Commit**: YES (groups with Tasks 6-9)

- [x] 11. Update mouse event handling for bottom-up coordinates

  **What to do**:
  - In `mainLoop.py`:
    - Remove any Y-flip in mouse event handlers
    - Ensure `on_mouse_press`, `on_mouse_release`, `on_mouse_drag`, `on_mouse_scroll` pass bottom-up coordinates to WidgetManager and GuiManager
    - The moderngl_window wrapper already provides bottom-up — verify this is true
    - If wrapper provides top-down, add a single flip at the entry point and document it
  - In `window/mainWindow.py`:
    - Check mouse event methods for any flips
    - Remove if present
  - Visual verification: run the app and confirm:
    - Tile borders render at correct positions
    - Right-click popup appears at cursor position
    - Widget renders in correct quadrant
    - Widget context menu appears at right-click position
    - Ctrl+click opens tile popup (mode preserved)

  **Must NOT do**:
  - Do NOT change ctrl toggle branching (only coordinate values)
  - Do NOT change any simulation logic

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: Integration verification, visual check required
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (with Tasks 9, 10)
  - **Parallel Group**: Wave 2
  - **Blocks**: Tasks 12-17 (rendering and events depend on correct coords)
  - **Blocked By**: Tasks 6-10

  **References**:
  - `mainLoop.py` — Mouse event handlers
  - `window/mainWindow.py` — Mouse event forwarding
  - `tests/test_event_forwarding.py` — Safety net

  **Acceptance Criteria**:
  - [ ] `python -m unittest tests.test_event_forwarding -v` → PASS
  - [ ] No Y-flip in mouse event chain (verified by grep)
  - [ ] Visual: all UI elements at correct positions

  **QA Scenarios**:
  ```
  Scenario: Mouse event coordinate verification
    Tool: Bash (grep + unittest)
    Preconditions: All Wave 2 tasks complete
    Steps:
      1. Run: grep -n "win_h -\|height -\|_flip" mainLoop.py window/mainWindow.py
      2. Assert: No flips in mouse handling
      3. Run: python -m unittest tests.test_event_forwarding -v
      4. Assert: All PASS
    Expected Result: Empty grep + 0 failures
    Evidence: .omo/evidence/task-11-mouse-events.txt
  ```

  **Commit**: YES
  - Message: `refactor(input): bottom-up mouse coordinates throughout`
  - Files: `mainLoop.py`, `window/mainWindow.py`

- [x] 12. Make GuiRenderer a wrapper around DrawingContext

  **What to do**:
  - In `settings_gui/guiRenderer.py`:
    - Change `GuiRenderer` to hold a `DrawingContext` instance instead of its own shader/VBOs
    - `quad()`, `outline()`, `text()` should delegate to `self._dc.quad()`, etc.
    - `__init__(renderer, width, height)` creates a `DrawingContext(renderer, width, height)`
    - Keep the same public API (methods, signatures) so callers don't break
    - Remove `_init_gl()`, `_init_shared()` — DrawingContext handles this
    - Remove `_vbo`, `_ibo`, `_outline_vbo`, `_vao`, `_outline_vao` — DrawingContext owns these
    - Keep `set_resolution(w, h)` — delegate to `self._dc.set_resolution(w, h)`
  - Add `DrawingContext.set_resolution(w, h)` method if not present
  - Verify that `GuiRenderer` still works for settings popups, blip GUI, model aligner

  **Must NOT do**:
  - Do NOT change `GuiRenderer` method signatures (keep public API stable)
  - Do NOT change how callers use GuiRenderer

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: Core rendering pipeline change, high regression risk
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (with Tasks 13-17)
  - **Parallel Group**: Wave 3
  - **Blocks**: Tasks 18-20, 24-25 (DC caching and menu rendering depend on unified DC)
  - **Blocked By**: Tasks 6-11 (coordinates must be unified first)

  **References**:
  - `settings_gui/guiRenderer.py` — Current implementation
  - `widgets/widget_base.py` — DrawingContext (the target wrapper)
  - `settings_gui/guiManager.py` — GuiRenderer usage
  - `settings_gui/blipGui.py` — GuiRenderer usage
  - `window/model_aligner.py` — GuiRenderer usage

  **Acceptance Criteria**:
  - [ ] `GuiRenderer.quad()` delegates to `DrawingContext.quad()`
  - [ ] `GuiRenderer.outline()` delegates to `DrawingContext.outline()`
  - [ ] `GuiRenderer.text()` delegates to `DrawingContext.text()`
  - [ ] No duplicate shader program or VBOs in GuiRenderer
  - [ ] Settings popup still renders correctly (visual check)

  **QA Scenarios**:
  ```
  Scenario: GuiRenderer delegates to DrawingContext
    Tool: Bash (python -c "import ...")
    Preconditions: GuiRenderer updated
    Steps:
      1. Verify: GuiRenderer.__init__ creates DrawingContext
      2. Verify: GuiRenderer.quad calls self._dc.quad
      3. Verify: No shader compilation in GuiRenderer
    Expected Result: All verifications pass
    Evidence: .omo/evidence/task-12-gui-renderer.txt
  ```

  **Commit**: YES
  - Message: `refactor(gui): GuiRenderer wraps DrawingContext`
  - Files: `settings_gui/guiRenderer.py`, `widgets/widget_base.py`

- [x] 13. Delete duplicate shaders in settings_gui/shaders/

  **What to do**:
  - Delete `settings_gui/shaders/ui.vert` (duplicate of `widgets/shaders/ui.vert`)
  - Delete `settings_gui/shaders/ui.frag` (duplicate of `widgets/shaders/ui.frag`)
  - Delete `settings_gui/shaders/tile_border.vert` (after removing Y-flip in Task 8)
  - Delete `settings_gui/shaders/tile_bg.vert` (after removing Y-flip in Task 8)
  - Update any code that references these deleted shaders to use `widgets/shaders/` versions
  - Verify no broken references remain

  **Must NOT do**:
  - Do NOT delete `widgets/shaders/ui.vert` or `ui.frag` (these are the canonical versions)
  - Do NOT delete `tile_management/shaders/tile_border.vert` (that's for tile grid)

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: File cleanup
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (with Tasks 12, 14-17)
  - **Parallel Group**: Wave 3
  - **Blocks**: None (cleanup task)
  - **Blocked By**: Tasks 8, 12 (shaders must be unflipped and unused first)

  **References**:
  - `settings_gui/shaders/` — Directory to clean up
  - `widgets/shaders/` — Canonical shader location
  - `grep -r "settings_gui/shaders" .` — Find all references

  **Acceptance Criteria**:
  - [ ] `settings_gui/shaders/` contains no `.vert` or `.frag` files
  - [ ] `grep -r "settings_gui/shaders" .` returns no references
  - [ ] App still runs (uses widgets/shaders/ versions)

  **QA Scenarios**:
  ```
  Scenario: Duplicate shader cleanup
    Tool: Bash (ls + grep)
    Preconditions: Shaders deleted
    Steps:
      1. Run: ls settings_gui/shaders/
      2. Assert: No .vert or .frag files
      3. Run: grep -r "settings_gui/shaders" .
      4. Assert: No references
    Expected Result: Empty directory + no references
    Evidence: .omo/evidence/task-13-shader-cleanup.txt
  ```

  **Commit**: YES (groups with Task 12)

- [x] 14. Fix bare imports in settings_gui/elements/

  **What to do**:
  - In `settings_gui/elements/button.py`, `toggle.py`, `slider.py`, `branch.py`:
    - Change `from guiRenderer import GuiRenderer` to `from settings_gui.guiRenderer import GuiRenderer`
    - Or use relative import: `from ..guiRenderer import GuiRenderer`
  - Ensure `settings_gui/__init__.py` does NOT add its directory to `sys.path`
    - If it does, remove the `sys.path` manipulation
  - Verify all settings_gui modules can be imported without path hacks

  **Must NOT do**:
  - Do NOT change the `GuiRenderer` class itself (that's Task 12)
  - Do NOT change any element logic (only imports)

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Import fixes only
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (with Tasks 12-13, 15-17)
  - **Parallel Group**: Wave 3
  - **Blocks**: None (cleanup task)
  - **Blocked By**: Task 12 (GuiRenderer must be in correct module)

  **References**:
  - `settings_gui/elements/*.py` — Files with bare imports
  - `settings_gui/__init__.py` — Check for sys.path manipulation

  **Acceptance Criteria**:
  - [ ] No `from guiRenderer import` remains in settings_gui/elements/
  - [ ] `python -c "from settings_gui.elements.button import Button"` works
  - [ ] No `sys.path` manipulation in `settings_gui/__init__.py`

  **QA Scenarios**:
  ```
  Scenario: Import structure fix
    Tool: Bash (grep + python -c)
    Preconditions: Imports fixed
    Steps:
      1. Run: grep -r "from guiRenderer import" settings_gui/
      2. Assert: No bare imports
      3. Run: python -c "from settings_gui.elements.button import Button"
      4. Assert: No ImportError
    Expected Result: Empty grep + successful import
    Evidence: .omo/evidence/task-14-imports.txt
  ```

  **Commit**: YES (groups with Tasks 12-13)

- [x] 15. Standardize blend state policy

  **What to do**:
  - Decide on ONE blend policy:
    - Option A: Always enable BLEND before any quad/outline call (DrawingContext current behavior)
    - Option B: Only enable BLEND when alpha < 1.0, disable after (GuiRenderer current behavior)
  - **Recommendation**: Option A (always blend) — simpler, no state thrashing
  - In `DrawingContext.quad()` and `outline()`:
    - Ensure blend is enabled: `self._ctx.enable(self._ctx.BLEND)`
    - Set blend function explicitly: `self._ctx.blend_func = (self._ctx.SRC_ALPHA, self._ctx.ONE_MINUS_SRC_ALPHA)`
  - In `GuiRenderer` (after Task 12 wrapper):
    - Remove conditional blend logic
    - Just delegate to DrawingContext (which handles blend)
  - Verify no rendering artifacts (semi-transparent widgets and popups)

  **Must NOT do**:
  - Do NOT change the blend function equation (keep SRC_ALPHA, ONE_MINUS_SRC_ALPHA)
  - Do NOT change how alpha values are passed

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: State policy standardization
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (with Tasks 12-14, 16-17)
  - **Parallel Group**: Wave 3
  - **Blocks**: Tasks 24-25 (menu rendering depends on correct blend)
  - **Blocked By**: Task 12 (GuiRenderer must wrap DrawingContext first)

  **References**:
  - `widgets/widget_base.py` — DrawingContext blend handling
  - `settings_gui/guiRenderer.py` — GuiRenderer blend handling
  - `tests/test_drawing_context.py` — Test blend state

  **Acceptance Criteria**:
  - [ ] Single blend policy across all rendering
  - [ ] No conditional `if alpha < 1.0` blend logic
  - [ ] Semi-transparent elements render correctly

  **QA Scenarios**:
  ```
  Scenario: Blend state standardization
    Tool: Bash (python -m unittest)
    Preconditions: Blend standardized
    Steps:
      1. Run: python -m unittest tests.test_drawing_context -v
      2. Assert: Tests PASS (blend state verified)
    Expected Result: 0 failures
    Evidence: .omo/evidence/task-15-blend.txt
  ```

  **Commit**: YES (groups with Tasks 12-14)

- [x] 16. WidgetManager converts screen to local coordinates

  **What to do**:
  - In `widgets/manager.py`:
    - Add screen→local conversion in `on_mouse_press(x, y, button)`:
      ```python
      widget = self._find_widget_at(x, y)
      if widget:
          local_x = x - widget.tile_x
          local_y = y - widget.tile_y
          widget.on_mouse_press(local_x, local_y, button)
      ```
    - Same for `on_mouse_release`, `on_mouse_drag`, `on_mouse_scroll`
  - Remove `modifiers` parameter from WidgetManager event methods
    - Widgets don't need modifiers (ctrl is handled by caller)
  - Update `mainLoop.py` event handlers to NOT pass `modifiers` to WidgetManager
  - Ensure `WidgetManager.on_mouse_press` checks for open menu FIRST:
    - If menu is open and click is inside menu → handle menu
    - If menu is open and click is outside → close menu
    - Otherwise → forward to widget

  **Must NOT do**:
  - Do NOT change how ctrl toggle works (just remove modifiers param)
  - Do NOT change widget event method signatures yet (Task 17 does that)

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Coordinate conversion logic
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (with Tasks 12-15, 17)
  - **Parallel Group**: Wave 3
  - **Blocks**: Tasks 21, 23 (widget API and callers)
  - **Blocked By**: Tasks 9-11 (coordinates must be unified)

  **References**:
  - `widgets/manager.py` — Event forwarding methods
  - `tests/test_event_forwarding.py` — Update tests for local coords
  - `mainLoop.py` — Event handler wiring

  **Acceptance Criteria**:
  - [ ] `python -m unittest tests.test_event_forwarding -v` → PASS (updated for local coords)
  - [ ] Widget receives local coordinates (0,0 at tile bottom-left)
  - [ ] Menu gets priority over widget events

  **QA Scenarios**:
  ```
  Scenario: Screen to local coordinate conversion
    Tool: Bash (python -m unittest)
    Preconditions: WidgetManager updated
    Steps:
      1. Run: python -m unittest tests.test_event_forwarding -v
      2. Assert: All PASS
      3. Verify: mock widget received local_x = screen_x - tile_x
    Expected Result: 0 failures, correct local coordinates
    Evidence: .omo/evidence/task-16-local-coords.txt
  ```

  **Commit**: YES
  - Message: `refactor(widget): screen to local coordinate conversion`
  - Files: `widgets/manager.py`, `mainLoop.py`, `tests/test_event_forwarding.py`

- [x] 17. Remove modifiers parameter from widget event methods

  **What to do**:
  - In `widgets/widget_base.py`:
    - Change `Widget.on_mouse_press(self, x, y, button, modifiers)` to `on_mouse_press(self, x, y, button)`
    - Same for `on_mouse_release`, `on_mouse_drag`, `on_mouse_scroll`
    - Update docstrings
  - In `widgets/line_plot.py`:
    - Update method signatures to match base class
  - In any other widget files:
    - Update method signatures
  - Update `widgets/manager.py` to match (if not already done in Task 16)
  - Update `mainLoop.py` to not pass modifiers

  **Must NOT do**:
  - Do NOT change any method bodies (just signatures)
  - Do NOT change how ctrl works (ctrl is handled before reaching widget)

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Signature changes across files
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (with Tasks 12-16)
  - **Parallel Group**: Wave 3
  - **Blocks**: Task 23 (callers updated)
  - **Blocked By**: Task 16 (WidgetManager must not pass modifiers first)

  **References**:
  - `widgets/widget_base.py` — Widget base class
  - `widgets/line_plot.py` — LinePlot widget
  - `widgets/manager.py` — WidgetManager forwarding
  - `mainLoop.py` — Event wiring

  **Acceptance Criteria**:
  - [ ] No `modifiers` parameter in any widget event method
  - [ ] `python -m unittest tests.test_event_forwarding -v` → PASS
  - [ ] No `modifiers` passed through event chain

  **QA Scenarios**:
  ```
  Scenario: Modifiers parameter removal
    Tool: Bash (grep + unittest)
    Preconditions: Signatures updated
    Steps:
      1. Run: grep -r "modifiers" widgets/ mainLoop.py
      2. Assert: No matches in event methods
      3. Run: python -m unittest tests.test_event_forwarding -v
      4. Assert: All PASS
    Expected Result: Empty grep + 0 failures
    Evidence: .omo/evidence/task-17-modifiers.txt
  ```

  **Commit**: YES (groups with Task 16)

- [x] 18. Cache DrawingContext per widget (create at setup)

  **What to do**:
  - In `widgets/manager.py`:
    - Change `create_widget()` to create ONE DrawingContext for the widget
    - Store it on the widget or in a parallel dict: `self._widget_contexts[(tile.x, tile.y)] = ctx`
    - The DC is sized to the tile: `DrawingContext(renderer, tile.width, tile.height)`
    - Set offset: `ctx.set_offset(tile.x, tile.y)`
  - In `widgets/widget_base.py`:
    - Add `Widget._drawing_context` attribute
    - `Widget._bind_drawing_context(ctx)` stores it
  - In `Widget._on_tile_resize(x, y, w, h)`:
    - Update the cached DrawingContext's resolution and offset

  **Must NOT do**:
  - Do NOT change DrawingContext creation in `render_all()` yet (Task 20)
  - Do NOT remove the old create_widget path yet

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: Core lifecycle change
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (with Tasks 19-20)
  - **Parallel Group**: Wave 4
  - **Blocks**: Tasks 20-22 (lifecycle and API depend on cached DC)
  - **Blocked By**: Tasks 12 (GuiRenderer wraps DrawingContext)

  **References**:
  - `widgets/manager.py` — create_widget and render_all
  - `widgets/widget_base.py` — Widget base class
  - `tests/test_drawing_context.py` — Verify caching

  **Acceptance Criteria**:
  - [ ] Each widget has one DrawingContext created at setup
  - [ ] `python -m unittest tests.test_drawing_context -v` → PASS
  - [ ] No duplicate DC creation for same widget

  **QA Scenarios**:
  ```
  Scenario: Per-widget DrawingContext caching
    Tool: Bash (python -m unittest)
    Preconditions: Caching implemented
    Steps:
      1. Run: python -m unittest tests.test_drawing_context -v
      2. Assert: All PASS
      3. Verify: Widget._drawing_context exists and is reused
    Expected Result: 0 failures, single DC per widget
    Evidence: .omo/evidence/task-18-dc-cache.txt
  ```

  **Commit**: YES
  - Message: `refactor(widget): cache DrawingContext per widget`
  - Files: `widgets/manager.py`, `widgets/widget_base.py`

- [x] 19. Add set_offset and set_resolution to DrawingContext

  **What to do**:
  - In `widgets/widget_base.py`:
    - Add `DrawingContext.set_offset(x, y)`:
      ```python
      def set_offset(self, x, y):
          self._ox = x
          self._oy = y
      ```
    - Add `DrawingContext.set_resolution(w, h)`:
      ```python
      def set_resolution(self, w, h):
          self._w = w
          self._h = h
      ```
    - Ensure `quad()` and `outline()` use `_ox`, `_oy` for positioning
    - Ensure `u_resolution` uniform uses `_w`, `_h`
  - Verify these methods work with the cached DC in Task 18

  **Must NOT do**:
  - Do NOT change how `quad()` calculates NDC (only the offset/resolution inputs)
  - Do NOT break existing callers

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Simple method additions
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (with Tasks 18, 20)
  - **Parallel Group**: Wave 4
  - **Blocks**: Task 21 (add_widget uses these methods)
  - **Blocked By**: Task 12 (DrawingContext must be unified first)

  **References**:
  - `widgets/widget_base.py` — DrawingContext class
  - `tests/test_drawing_context.py` — Test new methods

  **Acceptance Criteria**:
  - [ ] `set_offset` and `set_resolution` methods exist
  - [ ] `python -m unittest tests.test_drawing_context -v` → PASS
  - [ ] DC updates offset/resolution correctly

  **QA Scenarios**:
  ```
  Scenario: DrawingContext offset and resolution methods
    Tool: Bash (python -m unittest)
    Preconditions: Methods added
    Steps:
      1. Run: python -m unittest tests.test_drawing_context -v
      2. Assert: All PASS
    Expected Result: 0 failures
    Evidence: .omo/evidence/task-19-dc-methods.txt
  ```

  **Commit**: YES (groups with Task 18)

- [x] 20. Remove per-frame DrawingContext creation from render_all

  **What to do**:
  - In `widgets/manager.py`:
    - Change `render_all()` to reuse cached DrawingContexts
    - Remove the per-frame `DrawingContext(renderer, tile.width, tile.height, ...)` creation
    - Just iterate widgets and call `widget.draw()` (widget has its own cached DC)
    - Update `render_widgets` callback in `window/mainWindow.py` if it creates DCs
  - Verify no new DrawingContext is created during `render_all()`
  - Verify uniform values don't leak between widgets (each widget has its own DC, but they share the shader — ensure uniforms are set per-draw call)

  **Must NOT do**:
  - Do NOT change how widgets draw (they still call `ui.quad()`, etc.)
  - Do NOT remove the `_drawing_ctx` prototype in WidgetManager (used for menus)

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: Core rendering path change
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (with Tasks 18-19, 21-23)
  - **Parallel Group**: Wave 4
  - **Blocks**: Task 21 (add_widget assumes cached DC)
  - **Blocked By**: Tasks 18-19 (DC must be cached and have set methods)

  **References**:
  - `widgets/manager.py` — render_all method
  - `window/mainWindow.py` — render_widgets callback
  - `tests/test_drawing_context.py` — Verify no per-frame creation

  **Acceptance Criteria**:
  - [ ] `render_all()` does not create new DrawingContext instances
  - [ ] Each widget's DC is reused every frame
  - [ ] `python -m unittest tests.test_drawing_context -v` → PASS
  - [ ] Visual: widgets render correctly (no missing elements)

  **QA Scenarios**:
  ```
  Scenario: No per-frame DC creation
    Tool: Bash (python -m unittest)
    Preconditions: render_all updated
    Steps:
      1. Run: python -m unittest tests.test_drawing_context -v
      2. Assert: All PASS
      3. Verify: render_all does not call DrawingContext.__init__
    Expected Result: 0 failures, no new DC creation
    Evidence: .omo/evidence/task-20-render-all.txt
  ```

  **Commit**: YES (groups with Tasks 18-19)

- [x] 21. Implement add_widget one-call API

  **What to do**:
  - In `widgets/manager.py`:
    - Rename `create_widget()` to `add_widget(tile, name)`
    - Encapsulate ALL setup steps:
      ```python
      def add_widget(self, tile, name):
          widget_class = self._registry.get(name)
          widget = widget_class()
          ctx = DrawingContext(self._renderer, tile.width, tile.height)
          ctx.set_offset(tile.x, tile.y)
          widget._bind_renderer(self._renderer)
          widget._bind_drawing_context(ctx)  # Cached, reused every frame
          widget._bind_data_bus(self._data_bus)
          widget._on_tile_resize(tile.x, tile.y, tile.width, tile.height)
          widget.setup()
          self._widgets[(tile.x, tile.y)] = widget
          return widget
      ```
    - Remove the separate public methods: `_bind_renderer`, `_bind_drawing_context`, `_bind_data_bus`, `_on_tile_resize`
      - Make them private (single underscore) or remove entirely
    - Keep `destroy_widget(tile_x, tile_y)` public
  - Update `settings_gui/guiManager.py` to call `add_widget()` instead of `create_widget()`
  - Update `tests/test_widget_integration.py` to use `add_widget()`

  **Must NOT do**:
  - Do NOT change the registry system (still uses `default_registry`)
  - Do NOT change how widgets are destroyed

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: API refactoring
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (with Tasks 18-20, 22-23)
  - **Parallel Group**: Wave 4
  - **Blocks**: Task 23 (all callers must be updated)
  - **Blocked By**: Tasks 18-20 (cached DC must exist)

  **References**:
  - `widgets/manager.py` — create_widget method (the target)
  - `settings_gui/guiManager.py` — Caller of create_widget
  - `tests/test_widget_integration.py` — Test caller

  **Acceptance Criteria**:
  - [ ] `add_widget(tile, "Line Plot")` works in one call
  - [ ] `python -m unittest tests.test_widget_integration -v` → PASS (updated tests)
  - [ ] No public `_bind_*` methods remain
  - [ ] Widget is fully functional after one call

  **QA Scenarios**:
  ```
  Scenario: One-call widget creation
    Tool: Bash (python -m unittest)
    Preconditions: add_widget implemented
    Steps:
      1. Run: python -m unittest tests.test_widget_integration -v
      2. Assert: All PASS
      3. Verify: add_widget returns fully configured widget
    Expected Result: 0 failures, widget ready to use
    Evidence: .omo/evidence/task-21-add-widget.txt
  ```

  **Commit**: YES
  - Message: `feat(widget): one-call add_widget API`
  - Files: `widgets/manager.py`, `settings_gui/guiManager.py`, `tests/test_widget_integration.py`

- [x] 22. Add Widget.teardown() and call in destroy_widget

  **What to do**:
  - In `widgets/widget_base.py`:
    - Add `Widget.teardown()` method:
      ```python
      def teardown(self):
          """Clean up GPU resources and signal bindings."""
          pass  # Base class does nothing
      ```
  - In `widgets/line_plot.py`:
    - Override `teardown()` to detach signals, clear buffers
  - In `widgets/manager.py`:
    - Update `destroy_widget(tile_x, tile_y)`:
      ```python
      def destroy_widget(self, tile_x, tile_y):
          widget = self._widgets.pop((tile_x, tile_y), None)
          if widget:
              widget.teardown()
          return widget is not None
      ```
  - Ensure `LinePlot.teardown()` clears `self._signal` and `self._buffer`

  **Must NOT do**:
  - Do NOT change how widgets are created (only destruction)
  - Do NOT change the destroy_widget signature

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Cleanup method addition
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (with Tasks 18-21, 23)
  - **Parallel Group**: Wave 4
  - **Blocks**: Task 23 (callers may need update)
  - **Blocked By**: Task 21 (destroy_widget must be stable first)

  **References**:
  - `widgets/widget_base.py` — Widget base class
  - `widgets/line_plot.py` — LinePlot widget
  - `widgets/manager.py` — destroy_widget method

  **Acceptance Criteria**:
  - [ ] `Widget.teardown()` exists in base class
  - [ ] `LinePlot.teardown()` detaches signals and clears buffers
  - [ ] `destroy_widget()` calls `teardown()` before removal
  - [ ] `python -m unittest tests.test_widget_integration -v` → PASS

  **QA Scenarios**:
  ```
  Scenario: Widget teardown cleanup
    Tool: Bash (python -m unittest)
    Preconditions: teardown implemented
    Steps:
      1. Run: python -m unittest tests.test_widget_integration -v
      2. Assert: All PASS
      3. Verify: destroy_widget calls teardown
    Expected Result: 0 failures, proper cleanup
    Evidence: .omo/evidence/task-22-teardown.txt
  ```

  **Commit**: YES (groups with Tasks 18-21)

- [x] 23. Update all callers of create_widget to add_widget

  **What to do**:
  - Find all callers of `create_widget()`:
    - `settings_gui/guiManager.py` — update to `add_widget()`
    - `tests/test_widget_integration.py` — update to `add_widget()`
    - `tests/test_lineplot.py` — update to `add_widget()`
    - Any other files: search with `grep -r "create_widget"`
  - Update each call site to use the new signature:
    - Old: `wm.create_widget(tile, "Line Plot")` + manual setup
    - New: `wm.add_widget(tile, "Line Plot")`
  - Remove any manual setup code that's now encapsulated
  - Update `mainLoop.py` `_on_resize()`:
    - Add `widget_manager.on_resize(width, height)` to propagate window resize to all widgets
    - This updates each widget's cached DrawingContext resolution and offset
    - Currently `_on_resize` only recreates TileManager but does not resize widgets
  - Verify `grep -r "create_widget"` returns only the definition in manager.py

  **Must NOT do**:
  - Do NOT change any logic beyond renaming the call
  - Do NOT leave manual setup code that add_widget now handles

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Call site updates
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (with Tasks 18-22)
  - **Parallel Group**: Wave 4
  - **Blocks**: None (last Wave 4 task)
  - **Blocked By**: Tasks 21-22 (API must be ready)

  **References**:
  - `grep -r "create_widget" .` — Find all call sites
  - `widgets/manager.py` — New add_widget definition

  **Acceptance Criteria**:
  - [ ] `grep -r "create_widget"` returns only definition in manager.py
  - [ ] All existing tests pass with add_widget
  - [ ] `mainLoop.py` `_on_resize()` calls `widget_manager.on_resize(width, height)`
  - [ ] `python -m unittest discover -s tests -v` → PASS

  **QA Scenarios**:
  ```
  Scenario: Call site migration
    Tool: Bash (grep + unittest)
    Preconditions: Callers updated
    Steps:
      1. Run: grep -r "create_widget" . | grep -v "def add_widget"
      2. Assert: No old call sites remain
      3. Run: python -m unittest discover -s tests -v
      4. Assert: All PASS
    Expected Result: Empty grep + 0 failures
    Evidence: .omo/evidence/task-23-callers.txt
  ```

  **Commit**: YES (groups with Tasks 18-22)

- [x] 24. Convert MenuRenderer to data structure only

  **What to do**:
  - In `widgets/widget_gui.py`:
    - Remove all rendering logic from `MenuRenderer` (no more `draw()`)
    - Keep state machine: `open()`, `close()`, `visible`, `_entries`, `_sub_level`
    - Add `get_render_commands()` method:
      ```python
      def get_render_commands(self):
          """Return list of (type, x, y, w, h, text, color) tuples for rendering."""
          # Calculate positions, return draw commands
          pass
      ```
    - Keep event handling: `on_mouse_press()`, `on_mouse_release()`, `on_mouse_move()`
    - Remove dependency on DrawingContext (no more `_dc`)
  - The menu still tracks which item is hovered, which submenu is open, etc.
  - But it does NOT draw anything — it just returns what SHOULD be drawn

  **Must NOT do**:
  - Do NOT change the event handling logic (open, close, click, hover)
  - Do NOT change how widgets create context menus (still call `get_context_menu()`)

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: Core menu architecture change
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (with Tasks 25-26)
  - **Parallel Group**: Wave 5
  - **Blocks**: Task 25 (WidgetManager needs render commands)
  - **Blocked By**: Tasks 15 (blend state), 16 (event forwarding)

  **References**:
  - `widgets/widget_gui.py` — MenuRenderer class
  - `tests/test_menu_state.py` — Update tests (menu still has state machine)

  **Acceptance Criteria**:
  - [ ] MenuRenderer has no `draw()` method
  - [ ] `get_render_commands()` returns structured draw data
  - [ ] Event handling still works (open, close, click, hover)
  - [ ] `python -m unittest tests.test_menu_state -v` → PASS

  **QA Scenarios**:
  ```
  Scenario: MenuRenderer data structure
    Tool: Bash (python -m unittest)
    Preconditions: MenuRenderer refactored
    Steps:
      1. Run: python -m unittest tests.test_menu_state -v
      2. Assert: All PASS
      3. Verify: MenuRenderer.get_render_commands returns list
    Expected Result: 0 failures, data structure returned
    Evidence: .omo/evidence/task-24-menu-data.txt
  ```

  **Commit**: YES
  - Message: `refactor(menu): MenuRenderer returns data structure`
  - Files: `widgets/widget_gui.py`, `tests/test_menu_state.py`

- [x] 25. WidgetManager renders context menus via GuiRenderer

  **What to do**:
  - In `widgets/manager.py`:
    - Add menu rendering to `render_all()`:
      ```python
      def render_all(self):
          # ... render widgets ...
          
          # Render open menu
          if self._menu_renderer.visible:
              commands = self._menu_renderer.get_render_commands()
              for cmd in commands:
                  if cmd['type'] == 'quad':
                      self._gui_renderer.quad(cmd['x'], cmd['y'], cmd['w'], cmd['h'], cmd['color'])
                  elif cmd['type'] == 'text':
                      self._gui_renderer.text(cmd['x'], cmd['y'], cmd['text'], cmd['color'], cmd['size'])
                  elif cmd['type'] == 'outline':
                      self._gui_renderer.outline(cmd['x'], cmd['y'], cmd['w'], cmd['h'], cmd['color'])
          ```
    - Or better: have MenuRenderer use GuiRenderer directly if it has access
  - Ensure menu uses the same rendering pipeline as tile popups
  - Ensure menu renders above widgets (draw after widgets)

  **Must NOT do**:
  - Do NOT change how menu state works (only rendering path)
  - Do NOT create a new DrawingContext for menus (use GuiRenderer/DrawingContext)

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: Integration of menu into unified pipeline
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (with Tasks 24, 26)
  - **Parallel Group**: Wave 5
  - **Blocks**: Task 26 (LinePlot may need update)
  - **Blocked By**: Tasks 12 (GuiRenderer wraps DC), 24 (MenuRenderer returns data)

  **References**:
  - `widgets/manager.py` — render_all and menu handling
  - `settings_gui/guiRenderer.py` — GuiRenderer (unified pipeline)
  - `widgets/widget_gui.py` — MenuRenderer data structure

  **Acceptance Criteria**:
  - [ ] Context menu renders using GuiRenderer/DrawingContext
  - [ ] Menu appears at correct position
  - [ ] Menu click triggers correct callback
  - [ ] Visual: menu looks correct (background, text, outline)

  **QA Scenarios**:
  ```
  Scenario: Unified menu rendering
    Tool: Bash (python -m unittest tests.test_menu_state -v)
    Preconditions: Menu rendering updated
    Steps:
      1. Run: python -m unittest tests.test_menu_state -v
      2. Assert: All PASS
      3. Visual check: menu renders correctly
    Expected Result: 0 failures, correct rendering
    Evidence: .omo/evidence/task-25-menu-render.txt
  ```

  **Commit**: YES (groups with Task 24)

- [x] 26. Update LinePlot.get_context_menu() if needed

  **What to do**:
  - In `widgets/line_plot.py`:
    - Verify `get_context_menu()` returns the expected data structure
    - Ensure it works with the new MenuRenderer (still returns list of tuples)
    - Update if the data format changed in Task 24
  - Test that the context menu shows correct signal names
  - Test that clicking a signal name attaches it to the plot

  **Must NOT do**:
  - Do NOT change LinePlot's core drawing logic
  - Do NOT change how signals are attached (only menu data format)

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Verification and minor update
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (with Tasks 24-25)
  - **Parallel Group**: Wave 5
  - **Blocks**: None (last implementation task)
  - **Blocked By**: Tasks 24-25 (menu system must be updated)

  **References**:
  - `widgets/line_plot.py` — get_context_menu method
  - `tests/test_widget_integration.py` — Test menu interaction

  **Acceptance Criteria**:
  - [ ] `get_context_menu()` returns correct data structure
  - [ ] Menu shows signal names
  - [ ] Clicking signal attaches it to plot
  - [ ] `python -m unittest tests.test_widget_integration -v` → PASS

  **QA Scenarios**:
  ```
  Scenario: LinePlot context menu
    Tool: Bash (python -m unittest)
    Preconditions: LinePlot updated
    Steps:
      1. Run: python -m unittest tests.test_widget_integration -v
      2. Assert: All PASS
      3. Verify: get_context_menu returns valid menu data
    Expected Result: 0 failures, correct menu data
    Evidence: .omo/evidence/task-26-lineplot-menu.txt
  ```

  **Commit**: YES (groups with Tasks 24-25)

---

## Final Verification Wave

> 4 review agents run in PARALLEL. ALL must APPROVE. Present consolidated results to user and get explicit "okay" before completing.

- [x] F1. **Plan Compliance Audit** — `oracle`
  Read the plan end-to-end. For each "Must Have": verify implementation exists (read file, curl endpoint, run command). For each "Must NOT Have": search codebase for forbidden patterns — reject with file:line if found. Check evidence files exist in .omo/evidence/. Compare deliverables against plan.
  Output: `Must Have [N/N] | Must NOT Have [N/N] | Tasks [N/N] | VERDICT: APPROVE/REJECT`

- [x] F2. **Code Quality Review** — `unspecified-high`
  Run `python -m unittest discover -s tests -v` + linter. Review all changed files for: `as any`/`@ts-ignore`, empty catches, `print`/`console.log` in prod, commented-out code, unused imports. Check AI slop: excessive comments, over-abstraction, generic names.
  Output: `Build [PASS/FAIL] | Lint [PASS/FAIL] | Tests [N pass/N fail] | Files [N clean/N issues] | VERDICT`

- [x] F3. **Real Manual QA** — `unspecified-high`
  Start from clean state. Execute EVERY QA scenario from EVERY task — follow exact steps, capture evidence. Test cross-task integration. Test edge cases: empty state, invalid input, rapid actions. Save to `.omo/evidence/final-qa/`.
  Output: `Scenarios [N/N pass] | Integration [N/N] | Edge Cases [N tested] | VERDICT`

- [x] F4. **Scope Fidelity Check** — `deep`
  For each task: read "What to do", read actual diff (git log/diff). Verify 1:1 — everything in spec was built, nothing beyond spec was built. Check "Must NOT do" compliance. Detect cross-task contamination.
  Output: `Tasks [N/N compliant] | Contamination [CLEAN/N issues] | Unaccounted [CLEAN/N files] | VERDICT`

---

## Commit Strategy

- **Phase 0**: `test(gui): add regression tests for coordinates, events, tiles, menus`
- **Phase 1**: `refactor(tile): bottom-up coordinates everywhere`
- **Phase 2**: `refactor(gui): merge GuiRenderer into DrawingContext`
- **Phase 3**: `refactor(widget): cache DrawingContext per widget`
- **Phase 4**: `feat(widget): one-call add_widget API`
- **Phase 5**: `refactor(widget): local coordinates for widgets`
- **Phase 6**: `refactor(menu): unified menu rendering pipeline`
- **Final**: `chore(gui): cleanup and verification`

---

## Success Criteria

### Verification Commands
```bash
# All tests pass
python -m unittest discover -s tests -v

# Visual verification (run app, check):
# 1. Tile borders render at correct positions
# 2. Right-click popup appears at cursor position
# 3. Widget renders in correct tile quadrant
# 4. Widget context menu appears at right-click position
# 5. Menu click triggers correct action
# 6. Ctrl+click still opens tile popup (mode preserved)
```

### Final Checklist
- [ ] All "Must Have" present
- [ ] All "Must NOT Have" absent
- [ ] All tests pass
- [ ] No Y-flip conversions remain (verified by grep)
- [ ] Only one ui.vert/ui.frag shader exists
- [ ] Widget creation is one call
- [ ] Widgets receive local coordinates
- [ ] Context menus render and respond correctly
- [ ] Ctrl toggle behavior preserved
- [ ] No changes to data_bus, SignalSchema, or simulation logic
- [ ] No changes to vizcore/ legacy package
