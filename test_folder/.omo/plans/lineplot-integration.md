# LinePlot Widget Integration

## TL;DR

> **Quick Summary**: Integrate the existing LinePlot widget into the main simulation program (`mainLoop.py`), enabling widget selection from the GUI popup, transparent rendering over the 3D scene, mouse interaction without ctrl, and removal via ctrl+popup.
>
> **Deliverables**:
> - `widgets/registry.py` — WidgetRegistry mapping names to classes
> - `widgets/manager.py` — WidgetManager handling lifecycle, render, events
> - Fixed `DrawingContext.quad()` BLEND bug in `widgets/widget_base.py`
> - Fixed `LinePlot.draw()` scissor safety in `widgets/line_plot.py`
> - New `render_widgets` callback in `window/mainWindow.py`
> - Updated `settings_gui/guiManager.py` for real widget instantiation
> - Updated `mainLoop.py` with DataBus bridge, widget update, render, and event forwarding
>
> **Estimated Effort**: Medium
> **Parallel Execution**: YES — 3 waves
> **Critical Path**: Wave-1 fixes → Wave-2a infrastructure → Wave-2b integration → Wave-3 QA

---

## Context

### Original Request
Integrate the LinePlot widget into the main program so it can be selected from the GUI, interacted with when not pressing ctrl, rendered with a transparent background, and removed whilst holding ctrl. This should serve as a framework for other widgets.

### Interview Summary
**Key Discussions**:
- Widgets are currently stored as strings on tiles (`tile.widget = "Chart"`), never instantiated
- LinePlot is fully implemented in `widgets/line_plot.py` and tested in `tests/test_lineplot.py`
- Widget base class (`widget_base.py`) defines lifecycle: `setup()`, `update()`, `draw()`, signal binding
- `mainLoop.py` has a ctrl toggle: ctrl = tile borders + popup; no ctrl = 3D scene
- Simulation (`SimContainer`) provides `get_signal_schemas()` and `get_value_at(path)` but no DataBus integration

**Research Findings**:
- Test harness (`tests/test_lineplot.py`) demonstrates correct widget wiring: `_bind_renderer`, `_bind_drawing_context`, `_bind_data_bus`, `_on_tile_resize`, `setup()`, `update()`, `draw()`
- `vizcore.renderer.renderer.Renderer` and `vizcore.bus.data_bus.DataBus` are available
- `DrawingContext.quad()` toggles BLEND on/off per call — breaks the main pipeline which keeps BLEND enabled
- `LinePlot.draw()` sets `ctx.scissor` without try/finally — leaks scissor state on exception
- `TileManager.split_focused_tile()` copies `tile.widget` string reference — safe for strings, must remain so

### Metis Review
**Identified Gaps** (addressed):
- `Tile.widget` must remain a string identifier, not a Widget instance
- WidgetRegistry must be a simple dict, not a plugin system
- Widget rendering needs a new callback inserted between nodes and tile borders in `mainWindow.py`
- DataBus must be the local `core.data_bus.DataBus` (has schema methods)
- OpenGL state preservation (BLEND, scissor, depth) is critical
- Widget context menu (MenuRenderer) and tile popup (GuiManager) must be mutually exclusive

---

## Work Objectives

### Core Objective
Build a widget integration framework that bridges the existing LinePlot widget (and future widgets) into the main simulation loop, handling instantiation, DataBus connectivity, rendering, and input events.

### Concrete Deliverables
- `widgets/registry.py` — `WidgetRegistry` class mapping widget names to classes
- `widgets/manager.py` — `WidgetManager` class owning widget instances, DataBus, Renderer, DrawingContext
- Fixed BLEND bug in `widgets/widget_base.py`
- Fixed scissor leak in `widgets/line_plot.py`
- New `render_widgets` callback in `window/mainWindow.py`
- Updated `settings_gui/guiManager.py` — `_add_widget()` instantiates real widgets via WidgetManager; `_remove_widget()` cleans up
- Updated `mainLoop.py` — creates WidgetManager, feeds simulation to DataBus, updates/renders/forwards events to widgets

### Definition of Done
- [ ] Ctrl+RMB on empty tile → "Add Widget" → "Line Plot" → widget renders with transparent background over 3D scene
- [ ] RMB on widget tile (no ctrl) → widget context menu opens with "Attach Signal" / "Remove Signal"
- [ ] Attached signals show live-updating data in LinePlot
- [ ] Ctrl+RMB on widget tile → "Remove Line Plot" → widget disappears, no leaks
- [ ] Tile split with widget → widget survives in primary tile with new dimensions
- [ ] Window resize → widget resizes correctly
- [ ] No regression: ctrl+RMB still shows tile borders, 3D scene renders correctly

### Must Have
- WidgetRegistry with at least `{"Line Plot": LinePlot}`
- WidgetManager handling lifecycle (create, update, render, destroy)
- DataBus bridged from simulation each frame
- Widget rendering when not pressing ctrl (transparent overlay on 3D scene), tile borders only when ctrl pressed
- Mouse events forwarded to widgets when not ctrl
- Widget context menu via `widget_gui.MenuRenderer`
- OpenGL state preserved (no scissor leak, no BLEND toggle bug)

### Must NOT Have (Guardrails)
- NO plugin discovery, dynamic loading, or widget configuration UI
- NO multi-widget-per-tile support
- NO modification to LinePlot widget code (except scissor safety)
- NO modification to simulation code
- NO zoom/pan/interaction built for LinePlot (forward events, widget handles if it wants)
- NO reference counting, widget pooling, or lazy destruction
- NO signal subscription system, rate limiting, or data transformation pipelines

---

## Verification Strategy

### Test Decision
- **Infrastructure exists**: YES — `tests/test_lineplot.py` is a working test harness
- **Automated tests**: Tests-after (no new test framework needed)
- **Framework**: Existing `tests/test_lineplot.py` pattern
- **Agent-Executed QA**: ALWAYS — every task has agent-executable scenarios

### QA Policy
Every task MUST include agent-executed QA scenarios. Evidence saved to `.omo/evidence/task-{N}-{scenario-slug}.{ext}`.

- **Frontend/UI**: Use Playwright or interactive_bash for GUI interactions
- **Library/Module**: Use Bash (python REPL) for import and API verification
- **Shader/Render**: Use Bash (run test script, check stdout/stderr for GL errors)

---

## Execution Strategy

### Parallel Execution Waves

```
Wave 1a (Foundation — 3 parallel tasks):
├── Task 1: Fix DrawingContext BLEND bug — widgets/widget_base.py
├── Task 2: Fix LinePlot scissor safety — widgets/line_plot.py
└── Task 3: Create WidgetRegistry — widgets/registry.py

Wave 1b (Depends on 1a — 1 task):
└── Task 4: Create WidgetManager — widgets/manager.py (needs Task 3's registry)

Wave 2a-1 (Infrastructure — 2 parallel tasks, depends on Wave 1):
├── Task 5: Add render_widgets callback — window/mainWindow.py
└── Task 6: Update GuiManager for widget instantiation — settings_gui/guiManager.py

Wave 2a-2 (Depends on 2a-1 — 1 task):
└── Task 7: mainLoop.py infrastructure (DataBus, Renderer, WidgetManager setup)
    (needs Task 6's GuiManager widget_manager parameter)

Wave 2b (Integration — 4 parallel tasks, depends on Wave 2a):
├── Task 8: mainLoop.py DataBus bridge (sim.get_state() → push_payload)
├── Task 9: mainLoop.py widget update in _on_tick
├── Task 10: mainLoop.py widget rendering
└── Task 11: mainLoop.py mouse event forwarding + context menus

Wave 3 (Verification — 2 parallel tasks, depends on Wave 2b):
├── Task 12: Import verification and syntax check
└── Task 13: Integration test run

Wave FINAL (After ALL tasks — 4 parallel reviews):
├── Task F1: Plan compliance audit (oracle)
├── Task F2: Code quality review (unspecified-high)
├── Task F3: Real manual QA (unspecified-high)
└── Task F4: Scope fidelity check (deep)
-> Present results -> Get explicit user okay
```

### Dependency Matrix

- **1**: — — 5, 7, 10, Wave-1a
- **2**: — — 10, Wave-1a
- **3**: — — 4, 6, Wave-1a
- **4**: 3 — 6-11, Wave-1b
- **5**: — — 10, Wave-2a-1
- **6**: 3, 4 — 7, Wave-2a-1
- **7**: 3, 4, 6 — 8-11, Wave-2a-2
- **8**: 7 — 13, Wave-2b
- **9**: 7 — 13, Wave-2b
- **10**: 5, 7 — 13, Wave-2b
- **11**: 7 — 13, Wave-2b
- **12**: 1-11 — 13, Wave-3
- **13**: 8-11 — F1-F4, Wave-3

### Agent Dispatch Summary

- **1a**: **3** — 1 → `quick`, 2 → `quick`, 3 → `quick`
- **1b**: **1** — 4 → `unspecified-high`
- **2a-1**: **2** — 5 → `quick`, 6 → `quick`
- **2a-2**: **1** — 7 → `unspecified-high`
- **2b**: **4** — 8 → `quick`, 9 → `quick`, 10 → `quick`, 11 → `unspecified-high`
- **3**: **2** — 12 → `quick`, 13 → `unspecified-high`
- **FINAL**: **4** — F1 → `oracle`, F2 → `unspecified-high`, F3 → `unspecified-high`, F4 → `deep`

---

## TODOs

> Implementation + Test = ONE Task. Never separate.
> EVERY task MUST have: Recommended Agent Profile + Parallelization info + QA Scenarios.
> **FORMAT**: Task labels MUST use bare numbers: `1.`, `2.`, `3.` — NOT `T1.`, `Task 1.`, `Phase 1:`.

- [x] 1. Fix DrawingContext BLEND bug in widget_base.py

  **What to do**:
  - `DrawingContext.quad()` toggles `moderngl.BLEND` on and off per call (lines 79-90)
  - The main render pipeline enables BLEND once at init and keeps it on throughout
  - When a widget draws a semi-transparent quad, BLEND gets disabled, breaking all subsequent alpha blending
  - Fix: Remove the `disable(moderngl.BLEND)` call in `quad()`. Only enable BLEND if it wasn't already enabled, never disable it
  - Also check `outline()` for the same pattern

  **Must NOT do**:
  - Do NOT add new parameters to quad/outline signatures
  - Do NOT change coordinate math or color handling
  - Do NOT modify anything outside the BLEND toggle logic

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Single-file, localized fix to existing method behavior
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1a (with Tasks 2, 3)
  - **Blocks**: Tasks 5, 7, 10 (widget rendering depends on correct BLEND)
  - **Blocked By**: None

  **References**:
  - `widgets/widget_base.py:62-90` — Current quad() implementation with BLEND toggle
  - `widgets/widget_base.py:92-110` — outline() implementation (check for same bug)
  - `window/mainWindow.py:25-26` — Main pipeline enables BLEND at init

  **Acceptance Criteria**:
  - [ ] `quad()` no longer calls `ctx.disable(moderngl.BLEND)`
  - [ ] `outline()` no longer calls `ctx.disable(moderngl.BLEND)` (if present)
  - [ ] Syntax check passes: `python3 -m py_compile widgets/widget_base.py`

  **QA Scenarios**:
  ```
  Scenario: BLEND state preserved after widget draws transparent quad
    Tool: Bash (python REPL)
    Preconditions: None
    Steps:
      1. Read widgets/widget_base.py and verify no `disable(moderngl.BLEND)` in quad() or outline()
      2. Run `python3 -m py_compile widgets/widget_base.py`
    Expected Result: No disable() calls found; compilation succeeds
    Evidence: .omo/evidence/task-1-blend-fix.txt
  ```

  **Evidence to Capture**:
  - [ ] File diff showing removed disable() calls
  - [ ] Compilation success output

  **Commit**: YES — Commit #1 from Commit Strategy
  - Message: `fix(widgets): DrawingContext blend state preservation`
  - Files: `widgets/widget_base.py`

- [x] 2. Fix LinePlot scissor state leak in line_plot.py

  **What to do**:
  - `LinePlot.draw()` sets `ctx.scissor = (x, y, w, h)` at line 155 and clears it at line 162
  - If an exception occurs between these lines, scissor remains set, corrupting subsequent rendering
  - Fix: Wrap the scissor-block in a `try/finally` so `ctx.scissor = None` always executes
  - Alternatively, use a context manager pattern if moderngl supports it

  **Must NOT do**:
  - Do NOT change the scissor rectangle calculation
  - Do NOT change any draw logic (grid, legend, line_buffer calls)
  - Do NOT modify anything outside the scissor set/clear block

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Single-file, localized safety fix
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1a (with Tasks 1, 3)
  - **Blocks**: Task 10 (widget rendering depends on clean OpenGL state)
  - **Blocked By**: None

  **References**:
  - `widgets/line_plot.py:153-163` — Current scissor usage
  - `tests/test_lineplot.py` — Verify test still passes after change

  **Acceptance Criteria**:
  - [ ] `ctx.scissor` is set inside `try`, cleared in `finally`
  - [ ] `tests/test_lineplot.py` still runs successfully

  **QA Scenarios**:
  ```
  Scenario: Scissor state always restored after LinePlot.draw()
    Tool: Bash (grep + python)
    Preconditions: None
    Steps:
      1. Grep for `try:` and `finally:` around scissor in widgets/line_plot.py
      2. Run `python tests/test_lineplot.py` and capture first 10 lines of output
    Expected Result: try/finally block present; test runs without GL errors
    Evidence: .omo/evidence/task-2-scissor-fix.txt
  ```

  **Evidence to Capture**:
  - [ ] File diff showing try/finally block
  - [ ] test_lineplot.py run output (first 10 lines)

  **Commit**: YES — Commit #2 from Commit Strategy
  - Message: `fix(widgets): LinePlot scissor safety`
  - Files: `widgets/line_plot.py`

- [x] 3. Create WidgetRegistry in widgets/registry.py

  **What to do**:
  - Create `widgets/registry.py` with a `WidgetRegistry` class
  - Simple dict mapping: `{"Line Plot": LinePlot}`
  - Methods: `register(name, widget_class)`, `get(name) -> Widget class`, `list_names() -> list of str`
  - At module level, create a default registry instance and register LinePlot
  - Future widgets can be added by importing and calling `register()`

  **Must NOT do**:
  - Do NOT build plugin discovery (filesystem scanning, dynamic import)
  - Do NOT build configuration UI or widget metadata beyond name→class mapping
  - Do NOT modify existing widget files

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Small standalone module, simple API
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1a (with Tasks 1, 2)
  - **Blocks**: Task 4 (WidgetManager uses registry), Task 6 (GuiManager uses registry)
  - **Blocked By**: None

  **References**:
  - `widgets/line_plot.py:8` — `LinePlot` class definition
  - `settings_gui/guiManager.py:8` — `_widgets = ["Chart", "Plugin A", "Plugin B"]` (will be replaced with registry)

  **Acceptance Criteria**:
  - [ ] `widgets/registry.py` created with WidgetRegistry class
  - [ ] Default registry instance at module level with LinePlot registered
  - [ ] `registry.get("Line Plot")` returns `LinePlot` class
  - [ ] `registry.list_names()` returns `["Line Plot"]`
  - [ ] Syntax check passes

  **QA Scenarios**:
  ```
  Scenario: WidgetRegistry correctly maps names to classes
    Tool: Bash (python REPL)
    Preconditions: None
    Steps:
      1. Run `python -c "from widgets.registry import default_registry; from widgets.line_plot import LinePlot; assert default_registry.get('Line Plot') is LinePlot; print('PASS')"`
    Expected Result: Output contains "PASS"
    Evidence: .omo/evidence/task-3-registry.txt
  ```

  **Evidence to Capture**:
  - [ ] REPL output showing successful import and lookup

  **Commit**: YES — Commit #3 from Commit Strategy
  - Message: `feat(widgets): add WidgetRegistry`
  - Files: `widgets/registry.py`

- [x] 4. Create WidgetManager in widgets/manager.py

  **What to do**:
  - Create `widgets/manager.py` with a `WidgetManager` class
  - Responsibilities:
    - Own a `dict[(tile_x, tile_y) → Widget instance]` mapping (or tile index → widget)
    - Create widgets: given a tile and widget name, instantiate via registry, bind renderer/context/DataBus, call setup()
    - Destroy widgets: given a tile, call cleanup (if any), remove from dict
    - Update all widgets: iterate and call `widget.update()`
    - Render all widgets: for each widget, set DrawingContext size to tile size, call `widget.draw()`
    - Handle mouse events: find widget under cursor, forward event
    - Handle context menus: open/close `MenuRenderer` for widget under cursor
  - Constructor takes: `mainWindow`, `data_bus`, optional `widget_registry`
  - Creates internal `Renderer` and `DrawingContext` instances

  **Must NOT do**:
  - Do NOT store Widget instances on Tile objects (Tile.widget stays string)
  - Do NOT build multi-widget-per-tile support
  - Do NOT modify existing widget classes

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: Needs to understand the full widget lifecycle, ModernGL context, coordinate systems, and event forwarding. Touches multiple subsystems.
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: NO (blocked by Task 3)
  - **Parallel Group**: Wave 1b (after Task 3 completes)
  - **Blocks**: Tasks 6-11 (all integration depends on WidgetManager)
  - **Blocked By**: Task 3 (WidgetManager imports WidgetRegistry)

  **References**:
  - `widgets/widget_base.py:138-381` — Widget base class with lifecycle methods
  - `tests/test_lineplot.py:126-134` — Test harness wiring pattern
  - `widgets/widget_gui.py:108-336` — MenuRenderer for context menus
  - `vizcore.renderer.renderer` — Renderer class (import and instantiate)
  - `vizcore.bus.data_bus` — DataBus class (import and pass in)

  **Acceptance Criteria**:
  - [ ] `widgets/manager.py` created with WidgetManager class
  - [ ] Constructor signature: `WidgetManager(mainWindow, data_bus, registry=None)`
  - [ ] Methods: `create_widget(tile, name)`, `destroy_widget(tile)`, `update_all()`, `render_all()`, `on_mouse_press(x, y, button, modifiers)`, `on_mouse_release(...)`, `on_mouse_drag(...)`, `on_mouse_scroll(...)`
  - [ ] `create_widget` follows test harness pattern: `_bind_renderer`, `_bind_drawing_context`, `_bind_data_bus`, `_on_tile_resize`, `setup()`
  - [ ] `render_all` iterates widgets, creates DrawingContext per tile size, calls `widget.draw()`
  - [ ] `update_all` iterates widgets and calls `widget.update()`
  - [ ] Syntax check passes

  **QA Scenarios**:
  ```
  Scenario: WidgetManager can instantiate and bind a LinePlot
    Tool: Bash (python REPL)
    Preconditions: None
    Steps:
      1. Run `python -c "from widgets.manager import WidgetManager; print(type(WidgetManager))"`
      2. Verify all required methods exist via `dir(WidgetManager)`
    Expected Result: WidgetManager class exists with create_widget, destroy_widget, update_all, render_all, on_mouse_press, on_mouse_release, on_mouse_drag, on_mouse_scroll
    Evidence: .omo/evidence/task-4-manager-class.txt
  ```

  **Evidence to Capture**:
  - [ ] REPL output showing class exists with required methods

  **Commit**: YES — Commit #4 from Commit Strategy
  - Message: `feat(widgets): add WidgetManager`
  - Files: `widgets/manager.py`

- [x] 5. Add render_widgets callback in window/mainWindow.py

  **What to do**:
  - In `window/mainWindow.py:on_render()`, after `render_nodes` callback and before `render_tileManager` callback, add a new `render_widgets` callback invocation
  - The callback should be called within the existing `depth_mask = False` / `DEPTH_TEST` disabled block
  - Add registration: `self.render_callbacks.render_widgets = None` in constructor or callback binding
  - In `mainLoop.py:_bind_callbacks()`, bind `rc.render_widgets = self._render_widgets`

  **Must NOT do**:
  - Do NOT reorder existing callbacks (grid → axis → nodes → tiles → gui)
  - Do NOT modify depth_test or depth_mask state beyond the existing block
  - Do NOT add new OpenGL state changes

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Small insertion into existing callback chain
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2a-1 (with Task 6)
  - **Blocks**: Task 10 (widget rendering needs the callback)
  - **Blocked By**: None (can be done before WidgetManager exists, just adds the hook)

  **References**:
  - `window/mainWindow.py:465-477` — Current callback chain in on_render()
  - `mainLoop.py:72-74` — Current render_callbacks binding

  **Acceptance Criteria**:
  - [ ] `render_widgets` callback invoked between `render_nodes` and `render_tileManager`
  - [ ] `mainLoop.py` binds `rc.render_widgets = self._render_widgets`
  - [ ] `_render_widgets` method stub exists in mainLoop.py (will be fleshed out in Task 10)
  - [ ] Syntax check passes

  **QA Scenarios**:
  ```
  Scenario: render_widgets callback is properly inserted in render pipeline
    Tool: Bash (grep)
    Preconditions: None
    Steps:
      1. Grep for "render_widgets" in window/mainWindow.py and mainLoop.py
      2. Verify callback is called between render_nodes and render_tileManager in mainWindow.py
    Expected Result: render_widgets found in both files, positioned correctly in callback chain
    Evidence: .omo/evidence/task-5-callback-insertion.txt
  ```

  **Evidence to Capture**:
  - [ ] grep output showing render_widgets in correct position

  **Commit**: YES — Commit #5 from Commit Strategy
  - Message: `feat(window): add render_widgets callback`
  - Files: `window/mainWindow.py`, `mainLoop.py`

- [x] 6. Update GuiManager for widget instantiation via WidgetManager

  **What to do**:
  - Modify `settings_gui/guiManager.py`:
    - Import `WidgetRegistry` default instance
    - `__init__`: accept optional `widget_manager` parameter; if provided, use it for widget lifecycle
    - `_add_widget(name)`: if `widget_manager` is set, call `widget_manager.create_widget(self._popup_tile, name)` instead of just `tile.widget = name`. Still set `tile.widget = name` for the string identifier.
    - `_remove_widget(tile)`: if `widget_manager` is set, call `widget_manager.destroy_widget(tile)` before `tile.widget = None`
    - `_build_widget_list()`: use `widget_registry.list_names()` instead of hardcoded `self._widgets`
  - If no `widget_manager` is provided, fall back to current string-only behavior (backward compatibility)

  **Must NOT do**:
  - Do NOT change the popup UI layout or Button/Branch element usage
  - Do NOT modify tile popup behavior beyond widget add/remove
  - Do NOT store Widget instances on tiles

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Modifications to existing GuiManager methods, straightforward integration
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2a-1 (with Task 5)
  - **Blocks**: Task 7 (mainLoop creates GuiManager with widget_manager)
  - **Blocked By**: Tasks 3, 4 (WidgetRegistry and WidgetManager must exist to import)

  **References**:
  - `settings_gui/guiManager.py:81-90` — _add_widget and _remove_widget
  - `settings_gui/guiManager.py:68-79` — _build_widget_list
  - `settings_gui/guiManager.py:6-8` — Constructor with _widgets list

  **Acceptance Criteria**:
  - [ ] GuiManager constructor accepts optional `widget_manager` parameter
  - [ ] `_add_widget` calls `widget_manager.create_widget()` if available
  - [ ] `_remove_widget` calls `widget_manager.destroy_widget()` if available
  - [ ] `_build_widget_list` uses registry names instead of hardcoded list
  - [ ] Backward compatible: works without widget_manager (string-only mode)
  - [ ] Syntax check passes

  **QA Scenarios**:
  ```
  Scenario: GuiManager updated to support widget lifecycle
    Tool: Bash (grep + python)
    Preconditions: None
    Steps:
      1. Grep for "widget_manager" in settings_gui/guiManager.py
      2. Grep for "WidgetRegistry\|registry" in settings_gui/guiManager.py
      3. Run `python -c "from settings_gui.guiManager import GuiManager; import inspect; sig = inspect.signature(GuiManager.__init__); print(list(sig.parameters.keys()))"`
    Expected Result: widget_manager parameter present; registry imported; signature shows widget_manager
    Evidence: .omo/evidence/task-6-gui-manager.txt
  ```

  **Evidence to Capture**:
  - [ ] grep output showing widget_manager integration
  - [ ] Constructor signature verification

  **Commit**: YES — Commit #6 from Commit Strategy
  - Message: `feat(gui): instantiate real widgets via WidgetManager`
  - Files: `settings_gui/guiManager.py`

- [x] 7. mainLoop.py infrastructure setup (DataBus, Renderer, WidgetManager)

  **What to do**:
  - In `mainLoop.py`:
    - Import `core.data_bus.DataBus` (local, has schema methods)
    - Import `vizcore.renderer.renderer.Renderer`
    - Import `widgets.manager.WidgetManager`
    - Import `widgets.registry.default_registry`
    - In `__init__()`: create `self.data_bus = DataBus()`
    - In `run()`: after creating `self.guiManager`, create `self.widget_manager = WidgetManager(self.dashboardInstance, self.data_bus, default_registry)`
    - Pass `widget_manager` to `GuiManager`: `self.guiManager = GuiManager(self.dashboardInstance, widget_manager=self.widget_manager)`
    - Remove hardcoded `self._widgets` from GuiManager initialization (or let it default to registry)
    - Bind `rc.render_widgets = self._render_widgets` (stub method)

  **Must NOT do**:
  - Do NOT modify the simulation attachment or window creation logic
  - Do NOT change the order of existing initialization steps

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: Modifies the core orchestrator file, needs to wire multiple new components correctly
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: NO (blocked by Task 6)
  - **Parallel Group**: Wave 2a-2 (after Task 6 completes)
  - **Blocks**: Tasks 8-11 (all integration logic depends on this infrastructure)
  - **Blocked By**: Tasks 3, 4, 6 (registry, manager, and GuiManager widget_manager parameter must exist)

  **References**:
  - `mainLoop.py:24-57` — __init__ and run() methods
  - `mainLoop.py:60-74` — _bind_callbacks
  - `tests/test_lineplot.py:111-134` — Test harness wiring pattern

  **Acceptance Criteria**:
  - [ ] `mainLoop.py` imports DataBus, Renderer, WidgetManager, default_registry
  - [ ] `__init__` creates `self.data_bus`
  - [ ] `run()` creates `self.widget_manager` and passes it to `GuiManager`
  - [ ] `render_widgets` callback bound
  - [ ] Syntax check passes

  **QA Scenarios**:
  ```
  Scenario: mainLoop creates all infrastructure without errors
    Tool: Bash (python)
    Preconditions: None
    Steps:
      1. Run `python -c "from mainLoop import MainLoopHandler; m = MainLoopHandler(); print(type(m.data_bus))"`
    Expected Result: No import errors; data_bus is DataBus instance
    Evidence: .omo/evidence/task-7-infrastructure.txt
  ```

  **Evidence to Capture**:
  - [ ] REPL output showing successful import and instantiation

  **Commit**: YES — Commit #7 from Commit Strategy
  - Message: `feat(app): mainLoop WidgetManager infrastructure`
  - Files: `mainLoop.py`

- [x] 8. mainLoop.py DataBus bridge (simulation → DataBus)

  **What to do**:
  - In `mainLoop.py:_on_tick()`:
    - After `self._simulation.step(frame_time)`, add:
    ```python
    if self._simulation is not None:
        state = self._simulation.get_state()
        if state:
            self.data_bus.push_payload(state)
    ```
    - Then call `self.widget_manager.update_all()` to update all widgets with fresh data
  - The simulation's `get_state()` returns a nested dict of Signal values — DataBus.flatten_and_push handles the flattening

  **Must NOT do**:
  - Do NOT modify SimContainer or any simulation subclass
  - Do NOT build rate limiting or data transformation
  - Do NOT push data if simulation is None or paused

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Small addition to existing _on_tick method
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2b (with Tasks 9, 10, 11)
  - **Blocks**: Task 13 (integration test needs data flowing)
  - **Blocked By**: Task 7 (data_bus and widget_manager must exist)

  **References**:
  - `mainLoop.py:88-94` — Current _on_tick implementation
  - `core/data_bus.py:35-51` — push_payload and _flatten_and_push
  - `core/simulation.py:37-47` — SimContainer.get_state()

  **Acceptance Criteria**:
  - [ ] `get_state()` result pushed to `self.data_bus` after each simulation step
  - [ ] `widget_manager.update_all()` called after data push
  - [ ] No data pushed when `self._simulation is None`

  **QA Scenarios**:
  ```
  Scenario: DataBus receives simulation data after each tick
    Tool: Bash (python REPL)
    Preconditions: mainLoop.py modified
    Steps:
      1. Run `python -c "from core.simulation import SimContainer; s = SimContainer(); print(s.get_state())"` — verify get_state works
      2. Check that _on_tick calls data_bus.push_payload in mainLoop.py via grep
    Expected Result: get_state returns dict; grep finds push_payload in _on_tick
    Evidence: .omo/evidence/task-8-databus-bridge.txt
  ```

  **Evidence to Capture**:
  - [ ] get_state() output sample
  - [ ] grep showing push_payload in _on_tick

  **Commit**: YES — Commit #8 from Commit Strategy
  - Message: `feat(app): mainLoop DataBus bridge and widget update`
  - Files: `mainLoop.py`

- [x] 9. mainLoop.py widget update in _on_tick

  **What to do**:
  - Already covered by Task 8 (widget_manager.update_all() called after data push)
  - This task is essentially verifying that update_all works correctly
  - Ensure that widget updates happen BEFORE any render operations

  **Must NOT do**:
  - Do NOT add separate update logic outside WidgetManager

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Already implemented as part of Task 8, just needs verification
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2b (with Tasks 8, 10, 11)
  - **Blocks**: Task 13
  - **Blocked By**: Task 7

  **References**:
  - `widgets/manager.py` — update_all() method (created in Task 4)
  - `mainLoop.py:88-94` — _on_tick

  **Acceptance Criteria**:
  - [ ] `widget_manager.update_all()` is called in _on_tick after data push

  **QA Scenarios**:
  ```
  Scenario: Widget update called every tick
    Tool: Bash (grep)
    Preconditions: None
    Steps:
      1. Grep for "update_all" in mainLoop.py
    Expected Result: Found in _on_tick method
    Evidence: .omo/evidence/task-9-widget-update.txt
  ```

  **Evidence to Capture**:
  - [ ] grep output

  **Commit**: NO — Included in Commit #8 from Commit Strategy

- [x] 10. mainLoop.py widget rendering

  **What to do**:
  - Implement `_render_widgets()` in `mainLoop.py`:
  ```python
  def _render_widgets(self):
      if self.input.ctrl_pressed:
          return  # Tile border mode; skip widget rendering
      if self.widget_manager:
          self.widget_manager.render_all()
  ```
  - The `render_all()` method in WidgetManager should:
    - Iterate over all widget instances
    - For each widget, set up a DrawingContext sized to the tile dimensions
    - Call `widget.draw(ctx)`
    - Handle OpenGL state: save/restore viewport, scissor if needed
  - Widgets render with transparent backgrounds on top of the 3D scene

  **Must NOT do**:
  - Do NOT render widgets when ctrl is pressed (tile border mode takes precedence)
  - Do NOT modify the 3D scene rendering
  - Do NOT change existing tile border rendering logic

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Mainly wiring existing WidgetManager.render_all into the callback
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2b (with Tasks 8, 9, 11)
  - **Blocks**: Task 13
  - **Blocked By**: Tasks 5, 7 (render_widgets callback must exist; widget_manager must exist)

  **References**:
  - `mainLoop.py:181-184` — Current _render_tiles (ctrl-gated)
  - `window/mainWindow.py:468-475` — render callback chain (render_widgets inserted here)
  - `widgets/widget_base.py:203-210` — Widget.draw() signature

  **Acceptance Criteria**:
  - [ ] `_render_widgets()` method exists and calls `widget_manager.render_all()`
  - [ ] Method returns early if ctrl is pressed (so tile borders show instead)
  - [ ] WidgetManager.render_all() iterates widgets and calls draw() with proper DrawingContext

  **QA Scenarios**:
  ```
  Scenario: Widget rendering wired into main loop
    Tool: Bash (grep)
    Preconditions: None
    Steps:
      1. Grep for "_render_widgets" in mainLoop.py
      2. Verify it calls widget_manager.render_all()
      3. Verify it returns early if ctrl_pressed
    Expected Result: Method exists with correct logic
    Evidence: .omo/evidence/task-10-widget-render.txt
  ```

  **Evidence to Capture**:
  - [ ] grep output showing _render_widgets implementation

  **Commit**: YES — Commit #9 from Commit Strategy
  - Message: `feat(app): mainLoop widget rendering`
  - Files: `mainLoop.py`, `widgets/manager.py`

- [x] 11. mainLoop.py mouse event forwarding and widget context menus

  **What to do**:
  - Modify mouse event handlers in `mainLoop.py` to forward events to widgets when not pressing ctrl:
    - `_on_mouse_press(x, y, button)`:
      - If not ctrl and button == 2 (RMB): check if mouse is inside a tile with a widget
      - If yes: get widget's context menu via `widget.get_context_menu()`, open MenuRenderer
      - If no: fall through to existing blip picking
      - If ctrl: existing tile popup behavior (unchanged)
    - `_on_mouse_release(x, y, button)`:
      - Forward to widget_manager if a widget context menu is open or a widget is active
    - `_on_mouse_drag(x, y, dx, dy)`:
      - Forward to widget_manager if not ctrl and inside a widget tile
    - `_on_scroll(x, y, scroll_x, scroll_y)`:
      - Forward to widget_manager if not ctrl and inside a widget tile
  - WidgetManager should track which widget (if any) has mouse capture
  - When ctrl is pressed while widget menu is open, close the widget menu

  **Must NOT do**:
  - Do NOT change ctrl-gated tile popup behavior
  - Do NOT change blip picking behavior when not on a widget tile
  - Do NOT build new interaction features for LinePlot (just forward events)

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: Complex event routing logic, needs to handle multiple interacting systems (widgets, blips, tiles, popups)
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2b (with Tasks 8, 9, 10)
  - **Blocks**: Task 13
  - **Blocked By**: Task 7 (widget_manager must exist)

  **References**:
  - `mainLoop.py:96-137` — Current _on_mouse_press
    - `mainLoop.py:139-146` — _on_mouse_release
    - `mainLoop.py:151-158` — _on_mouse_drag
    - `mainLoop.py:148-149` — _on_scroll (currently pass)
    - `tests/test_lineplot.py:172-189` — Test harness mouse event pattern
    - `widgets/widget_gui.py:125-151` — MenuRenderer.open/close

  **Acceptance Criteria**:
  - [ ] RMB without ctrl on widget tile opens widget context menu
  - [ ] RMB without ctrl on empty tile falls through to blip picking
  - [ ] Ctrl+RMB still opens tile popup
  - [ ] Mouse drag forwarded to widget when not ctrl
  - [ ] MenuRenderer closes when ctrl is pressed
  - [ ] Widget context menu and tile popup are mutually exclusive

  **QA Scenarios**:
  ```
  Scenario: Mouse events correctly routed to widgets
    Tool: Bash (grep)
    Preconditions: None
    Steps:
      1. Grep for "widget_manager.on_mouse" in mainLoop.py
      2. Verify _on_mouse_press has widget menu logic for RMB without ctrl
      3. Verify _on_mouse_drag forwards to widget_manager
    Expected Result: Event forwarding logic present in all three handlers
    Evidence: .omo/evidence/task-11-mouse-events.txt
  ```

  **Evidence to Capture**:
  - [ ] grep output showing event forwarding logic

  **Commit**: YES — Commit #10 from Commit Strategy
  - Message: `feat(app): mainLoop mouse event forwarding`
  - Files: `mainLoop.py`, `widgets/manager.py`

- [x] 12. Import verification and syntax check

  **What to do**:
  - Verify all new and modified files compile without syntax errors
  - Check all imports resolve correctly (no ModuleNotFoundError)
  - Run `python3 -m py_compile` on every modified/new file:
    - `widgets/registry.py`
    - `widgets/manager.py`
    - `widgets/widget_base.py`
    - `widgets/line_plot.py`
    - `window/mainWindow.py`
    - `settings_gui/guiManager.py`
    - `mainLoop.py`
  - Run a quick import check: `python -c "from mainLoop import MainLoopHandler"`

  **Must NOT do**:
  - Do NOT skip any modified file

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Automated verification, fast to run
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 3 (with Task 13)
  - **Blocks**: Task F1-F4 (verification needs clean code)
  - **Blocked By**: Tasks 8-11 (transitive through 1-7 dependencies)

  **References**:
  - All modified files listed above

  **Acceptance Criteria**:
  - [ ] `python3 -m py_compile` passes for all 7 files
  - [ ] `python -c "from mainLoop import MainLoopHandler"` succeeds
  - [ ] No import errors

  **QA Scenarios**:
  ```
  Scenario: All modified files compile without errors
    Tool: Bash
    Preconditions: None
    Steps:
      1. Run `python3 -m py_compile widgets/registry.py widgets/manager.py widgets/widget_base.py widgets/line_plot.py window/mainWindow.py settings_gui/guiManager.py mainLoop.py`
      2. Run `python -c "from mainLoop import MainLoopHandler; print('OK')"`
    Expected Result: Both commands exit with code 0, output contains "OK"
    Evidence: .omo/evidence/task-12-syntax-check.txt
  ```

  **Evidence to Capture**:
  - [ ] Command output showing success

  **Commit**: NO — No commit (verification-only task; see Commit Strategy)

- [x] 13. Integration test — verify widget lifecycle end-to-end

  **What to do**:
  - Create a minimal integration test script in `tests/` or run inline
  - Test the full lifecycle:
    1. Create MainLoopHandler
    2. Attach ExampleSim
    3. Simulate adding a LinePlot widget to a tile
    4. Verify widget instance exists in WidgetManager
    5. Run a few "ticks" to verify DataBus receives data and widget updates
    6. Simulate removing the widget
    7. Verify widget instance is cleaned up
  - Since we can't run the full GUI in a headless environment, verify what we can programmatically:
    - Imports work
    - Instantiation works
    - DataBus receives data
    - WidgetManager tracks widgets correctly

  **Must NOT do**:
  - Do NOT try to open a real window in the test
  - Do NOT skip testing DataBus data flow

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: Needs to verify integration of multiple components without a real GUI
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 3 (with Task 12)
  - **Blocks**: Task F1-F4
  - **Blocked By**: Tasks 8-11 (transitive through 1-7 dependencies)

  **References**:
  - `tests/test_lineplot.py` — Widget test harness pattern
  - `tests/test_schema_system.py` — DataBus test patterns

  **Acceptance Criteria**:
  - [ ] Integration test script created and runs successfully
  - [ ] Test verifies: widget creation, DataBus data flow, widget update, widget removal
  - [ ] No exceptions during test run

  **QA Scenarios**:
  ```
  Scenario: Widget lifecycle works end-to-end
    Tool: Bash (python)
    Preconditions: All code changes applied
    Steps:
      1. Run integration test script
      2. Verify output shows all lifecycle stages passed
    Expected Result: Test runs without errors, all assertions pass
    Evidence: .omo/evidence/task-13-integration-test.txt
  ```

  **Evidence to Capture**:
  - [ ] Test run output

  **Commit**: YES — Commit #11 from Commit Strategy
  - Message: `test(integration): verify widget lifecycle`
  - Files: `tests/test_widget_integration.py`

---

## Final Verification Wave

> 4 review agents run in PARALLEL. ALL must APPROVE. Present consolidated results to user and get explicit "okay" before completing.

- [x] F1. **Plan Compliance Audit** — `oracle`
  Read the plan end-to-end. For each "Must Have": verify implementation exists (read file, curl endpoint, run command). For each "Must NOT Have": search codebase for forbidden patterns — reject with file:line if found. Check evidence files exist in .omo/evidence/. Compare deliverables against plan.
  Output: `Must Have [N/N] | Must NOT Have [N/N] | Tasks [N/N] | VERDICT: APPROVE/REJECT`

- [x] F2. **Code Quality Review** — `unspecified-high`
  Run `tsc --noEmit` + linter + `bun test`. Review all changed files for: `as any`/`@ts-ignore`, empty catches, console.log in prod, commented-out code, unused imports. Check AI slop: excessive comments, over-abstraction, generic names (data/result/item/temp).
  Output: `Build [PASS/FAIL] | Lint [PASS/FAIL] | Tests [N pass/N fail] | Files [N clean/N issues] | VERDICT`

- [x] F3. **Real Manual QA** — `unspecified-high`
  Start from clean state. Execute EVERY QA scenario from EVERY task — follow exact steps, capture evidence. Test cross-task integration (features working together, not isolation). Test edge cases: empty state, invalid input, rapid actions. Save to `.omo/evidence/final-qa/`.
  Output: `Scenarios [N/N pass] | Integration [N/N] | Edge Cases [N tested] | VERDICT`

- [x] F4. **Scope Fidelity Check** — `deep`
  For each task: read "What to do", read actual diff (git log/diff). Verify 1:1 — everything in spec was built (no missing), nothing beyond spec was built (no creep). Check "Must NOT do" compliance. Detect cross-task contamination: Task N touching Task M's files. Flag unaccounted changes.
  Output: `Tasks [N/N compliant] | Contamination [CLEAN/N issues] | Unaccounted [CLEAN/N files] | VERDICT`

---

## Commit Strategy

- **1**: `fix(widgets): DrawingContext blend state preservation` — widgets/widget_base.py
- **2**: `fix(widgets): LinePlot scissor safety` — widgets/line_plot.py
- **3**: `feat(widgets): add WidgetRegistry` — widgets/registry.py
- **4**: `feat(widgets): add WidgetManager` — widgets/manager.py
- **5**: `feat(window): add render_widgets callback` — window/mainWindow.py, mainLoop.py
- **6**: `feat(gui): instantiate real widgets via WidgetManager` — settings_gui/guiManager.py
- **7**: `feat(app): mainLoop WidgetManager infrastructure` — mainLoop.py
- **8**: `feat(app): mainLoop DataBus bridge and widget update` — mainLoop.py
- **9**: `feat(app): mainLoop widget rendering` — mainLoop.py, widgets/manager.py
- **10**: `feat(app): mainLoop mouse event forwarding` — mainLoop.py, widgets/manager.py
- **11**: `test(integration): verify widget lifecycle` — tests/test_widget_integration.py

---

## Success Criteria

### Verification Commands
```bash
# Syntax check all modified/new files
python3 -m py_compile widgets/registry.py widgets/manager.py widgets/widget_base.py widgets/line_plot.py window/mainWindow.py settings_gui/guiManager.py mainLoop.py

# Run integration test
python tests/test_lineplot.py  # Should still pass (widget itself unchanged)

# Launch main program and verify no immediate crash
python mainLoop.py  # Should open window without errors
```

### Final Checklist
- [ ] All "Must Have" present
- [ ] All "Must NOT Have" absent
- [ ] All tests pass
- [ ] No broken imports
- [ ] OpenGL state preserved across frames
- [ ] Widget lifecycle (add → update → render → remove) works end-to-end
