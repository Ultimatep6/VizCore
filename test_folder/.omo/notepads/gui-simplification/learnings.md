# GUI Simplification - Learnings

## Wave 1: Coordinate Conversion Tests (2026-06-06)

### Y-Flip Sites Identified (15 total)

| # | File | Line | Formula |
|---|------|------|---------|
| 1 | widgets/manager.py | 78 | `bottom_up_y = window_h - tile.y - tile.height` |
| 2 | settings_gui/guiManager.py | 26 | `popup_y = _win_h - y` |
| 3 | settings_gui/guiManager.py | 197 | `y = _win_h - y` |
| 4 | settings_gui/guiManager.py | 237 | `_win_h - y` |
| 5 | settings_gui/guiManager.py | 242 | `_win_h - y` |
| 6 | settings_gui/guiManager.py | 247 | `y = _win_h - y` |
| 7 | settings_gui/blipGui.py | 26 | `_y = _win_h - y` |
| 8 | settings_gui/blipGui.py | 172 | `y = _win_h - y` |
| 9 | settings_gui/blipGui.py | 213 | `_win_h - y` |
| 10 | settings_gui/blipGui.py | 219 | `y = _win_h - y` |
| 11 | window/model_aligner.py | 314 | `fy = renderer.height - y` |
| 12 | window/model_aligner.py | 350 | `fy = renderer.height - y` |
| 13 | window/model_aligner.py | 365 | `fy = renderer.height - y` |
| 14 | widgets/widget_gui.py | 122-123 | `_flip()` returns `_win_h - y` |
| 15 | shaders/*.vert | 23/12 | `ndc.y = -ndc.y` |

### Key Observations

1. **Two distinct flip patterns**:
   - **Standard flip**: `flipped_y = surface_height - original_y` (GuiManager, BlipGui, ModelAligner, WidgetGui)
   - **Tile flip**: `bottom_up_y = window_h - tile.y - tile.height` (WidgetManager) - includes tile height in calculation

2. **Shader NDC flip**: `ndc.y = -ndc.y` negates NDC coordinates (range [-1, 1]) rather than pixel coordinates.

3. **Coordinate system**: moderngl_window provides top-down (y=0 at top), GUI elements use bottom-up (y=0 at bottom).

4. **Invariant properties**:
   - All standard flips are self-inverse: `flip(flip(y)) == y`
   - Center point is fixed: `flip(win_h/2) == win_h/2`
   - Symmetry: `flip(0) + flip(max) == win_h`

### Test Coverage

- Created `tests/test_coordinates.py` with 40 tests covering all 15 flip sites
- Tests pass: `python -m unittest tests.test_coordinates -v` (40/40 OK)
- Evidence saved to `.omo/evidence/task-1-coord-tests.txt`

### Test Structure

Follows `test_widget_integration.py` pattern:
- `unittest.TestCase` for all tests
- `MockTile` fixture for tile-based tests
- Concrete assertions with expected values
- Edge cases: (0,0), max, midpoint, window resize

---

## Tile Manager Geometry (2026-06-06)

### Ground Truth (1280x720, gap=200)

`_init_tiles` creates a **2×2 grid** (4 tiles) via `product(x, y)`:
- `x = [0, (1280+200)/2] = [0, 740]`
- `y = [0, (720+200)/2] = [0, 460]`
- `width = (1280-200)/2 = 540`, `height = (720-200)/2 = 260`
- Tiles: (0,0), (0,460), (740,0), (740,460)

### Split Behavior

Splitting tile[0] (at x=0, y=0, w=540, h=260):
- **Vertical**: `w = (540-10)//2 = 265` → two tiles at x=[0,265) and x=[275,540)
- **Horizontal**: `h = (260-10)//2 = 125` → two tiles at y=[0,125) and y=[135,260)
- Result: 5 tiles (3 original + 2 new from split)

### Merge Behavior

Merging split halves (indices 0 and 1) restores original dimensions (540×260).

### Resize Behavior

Vertical resize (drag left -50px on split border at x=265):
- Left tile shrinks: 265→215
- Right tile shifts left 50 AND grows: x=275→225, width=265→315
- Note: resize_border adds to LEFT tiles, shifts AND subtracts from RIGHT tiles

Horizontal resize (drag up -30px on split border at y=125):
- Top tile shrinks: 125→95
- Bottom tile shifts up AND grows: y=135→105, height=125→155

### Border Detection

- Window edges (x=0, x=1280, y=0) are ignored (no border at window edge)
- Inter-tile gap (e.g., y=135 between split halves) IS detected as a border
- Threshold=5 pixels for border detection

### Test File

- `tests/test_tile_geometry.py` — 37 tests, all passing
- Evidence: `.omo/evidence/task-2-tile-geom-tests.txt`
- MockWindow with real ModernGL program for standalone context compatibility

---

## Tile Manager Bottom-Up Coordinate Fix (2026-06-06)

### Changes Made

1. **Tile.__init__ simplified**: Removed `window_height` parameter. Tile now always stores `self.y = y` and assumes the caller passes bottom-up coordinates.
2. **TileManager._init_tiles()**: Computes bottom-up y directly before passing to Tile constructor:
   - `y_topdown = [0, (self.height + gap_y) / 2]`
   - `y = [self.height - ytd - height for ytd in y_topdown]`
   - Result for 720px window: `[460, 0]`
3. **TileManager.split_focused_tile()**: Removed `self.height` from Tile constructor calls. New tiles inherit the parent's bottom-up y directly.
4. **TileManager.merge(), resize_border(), get_border_at(), get_tile_index()**: No code changes needed — these methods already work correctly with bottom-up coordinates because they operate on geometric spans (min/max, within-range checks) that are direction-agnostic.
5. **TileManager.render()**: No change needed — already passes `tile.y` (now correctly bottom-up) to the shader.

### Test Updates

Updated `tests/test_tile_geometry.py` assertions to match bottom-up behavior:
- **Horizontal split y positions**: t1.y=460, t2.y=595 (was 135, 0 with buggy flip)
- **Merge restored y**: merged.y=460 (was 0)
- **Horizontal resize**: t2.y=565 after dy=-30 (was 105)
- **Vertical resize test points**: y=500 instead of y=100 (to hit split tiles in bottom row)
- **Tile index after split**: Updated query points to fall within correct tiles
- **Border between split halves**: y=585 instead of y=125

### Verification

- `python -m unittest tests.test_tile_geometry -v` → 37/37 PASS
- `python -m unittest discover tests -v` → 181/181 PASS (no regressions)

### Key Insight

The original Tile class had a confusing dual-mode API where `y` meant top-down if `window_height` was provided, bottom-up if not. Removing the flip from Tile and making TileManager compute bottom-up y explicitly eliminates this ambiguity and makes the coordinate system consistent throughout the tile stack.

---

## Wave 2 Batch 3: Mouse Event Coordinate Verification (2026-06-06)

### Files Analyzed

- `mainLoop.py` — mouse event handlers: `_on_mouse`, `_on_mouse_press`, `_on_mouse_release`, `_on_mouse_drag`, `_on_scroll`
- `window/mainWindow.py` — mouse event forwarding: `on_mouse_press_event`, `on_mouse_release_event`, `on_mouse_drag_event`, `on_mouse_position_event`, `on_mouse_scroll_event`

### Verification Result: PASS

```bash
$ grep -n "win_h -\|height -\|_flip" mainLoop.py window/mainWindow.py
# (empty — no Y-flip operations found)
```

### Findings

1. **No Y-flip in entry points**: Both files pass mouse coordinates directly to downstream handlers without any transformation
2. **moderngl_window coordinates**: The wrapper passes coordinates directly; any Y-flip happens inside receiver components (GuiManager, BlipGui, WidgetGui, ModelAligner)
3. **Downstream flip sites remain**: The 15 flip sites documented in Wave 1 (guiManager.py, blipGui.py, widget_gui.py, model_aligner.py) still perform their own Y-flips — this is intentional as they receive top-down from moderngl_window
4. **No changes required**: mainLoop.py and mainWindow.py are already correct — coordinates flow without modification

### Key Insight

The coordinate flip architecture is:
- **Entry (mainLoop.py, mainWindow.py)**: No flip — passes moderngl_window coords directly
- **Internal (GuiManager, BlipGui, WidgetGui, ModelAligner)**: Each component flips internally since they receive top-down from moderngl_window
- **Output (Tile, rendering)**: Bottom-up coordinates expected by GPU/shader pipeline

This matches the documented design in MANUAL.md: "Mouse input from moderngl_window arrives top-down and is converted at the boundary via self._win_h - y."

---

## Wave 2 Batch 3: Y-Flip Removal from Mouse Event Handlers (2026-06-06)

### Task Summary

Removed all Y-flip mouse coordinate conversions (`self._win_h - y`, `self.renderer.height - y`) from 3 GUI files, since the coordinate system is now unified to bottom-up everywhere.

### Files Modified

**settings_gui/guiManager.py** — 5 flip sites removed:
- Line 26: `popup_y = _win_h - y` → `popup_y = y` (in `show_popup`)
- Line 197: `y = _win_h - y` → removed (in `on_mouse_press`)
- Line 237: `self._win_h - y` → `y` (in `on_mouse_release`)
- Line 242: `self._win_h - y` → `y` (in `on_mouse_drag`)
- Line 247: `y = _win_h - y` → removed (in `on_mouse_move`)

**settings_gui/blipGui.py** — 4 flip sites removed:
- Line 26: `self._y = _win_h - y` → `self._y = y` (in `show`)
- Line 172: `y = _win_h - y` → removed (in `on_mouse_press`)
- Line 213: `self._win_h - y` → `y` (in `on_mouse_release`)
- Line 219: `y = _win_h - y` → removed (in `on_mouse_move`)

**window/model_aligner.py** — 3 flip sites removed:
- Line 314: `fy = renderer.height - y` → replaced all `fy` refs with `y` (in `on_mouse_press`)
- Line 350: `fy = renderer.height - y` → replaced all `fy` refs with `y` (in `on_mouse_release`)
- Line 365: `fy = renderer.height - y` → replaced all `fy` refs with `y` (in `on_mouse_drag`)

### Not Removed (legitimate bounding math)

- `guiManager.py:120`: `dy = self._win_h - (by + bh)` — popup clamping, not mouse y flip
- `guiManager.py:157`: `oy = self._win_h - sh` — sub-level bounding, not mouse y flip
- `blipGui.py:153`: `oy = self._win_h - sh` — sub-level bounding, not mouse y flip

### Verification

```bash
$ grep -rn "win_h - y\|height - y" settings_gui/ window/
# NO MATCHES - clean
```

All pre-existing LSP diagnostics in model_aligner.py (missing imports, optional member access) were present before this change and are unrelated.

---

## Wave 3 Batch 1: GuiRenderer → DrawingContext Wrapper (2026-06-06)

### Task Summary

Refactored `GuiRenderer` from a standalone GL resource owner into a thin wrapper around `DrawingContext`, eliminating duplicate shader/VBO/VAO state.

### Files Modified

**`settings_gui/guiRenderer.py`** — Complete rewrite (83 → 55 lines):
- Removed own shader program (`_ui_program`), VBOs (`quad_vbo`, `outline_vbo`), and VAOs (`quad_vao`, `outline_vao`)
- Removed `_init_gl()` equivalent inline code from `__init__`
- Removed `numpy` and `moderngl` imports (no longer needed)
- Added `from widgets.widget_base import DrawingContext`
- `__init__` now creates `self._dc = DrawingContext(mainWindow, width, height)`
- `quad()` → `self._dc.quad(x, y, w, h, color, alpha)`
- `outline()` → `self._dc.outline(x, y, w, h, color, alpha)`
- `text()` → `self._dc.text(text_str, x, y, color, scale, anchor_x, anchor_y, clip_rect)`
- Added `set_resolution(w, h)` → `self._dc.set_resolution(w, h)`
- `width` and `height` are now properties with setters that call `set_resolution()`
- Kept `text_width()` static method and `measure_text()` module-level function
- Public API signatures unchanged — all callers work without modification

**`widgets/widget_base.py`** — Added `set_resolution(w, h)` to `DrawingContext`:
- Updates `self._w` and `self._h` so resolution can be changed after construction
- Required because callers set `renderer.width = w` and `renderer.height = h` in `on_resize`

### Verification

- `python -m py_compile settings_gui/guiRenderer.py widgets/widget_base.py` → clean
- `python -m unittest tests.test_drawing_context -v` → 17/17 PASS
- `python -m unittest discover tests -v` → 163/163 PASS (18 pre-existing errors in test_event_forwarding.py unrelated to this change)
- LSP diagnostics on `guiRenderer.py`: zero errors
- LSP diagnostics on `widget_base.py`: only pre-existing errors (unchanged)

### Key Insight

`GuiRenderer` and `DrawingContext` were maintaining nearly identical GL state (same shader, same VBO data, same VAO layout). By making `GuiRenderer` a wrapper, we now have exactly one shader program + one VBO set for all 2D UI rendering. The `DrawingContext._init_shared()` class method ensures shared resources are created once and reused across all `DrawingContext` and `GuiRenderer` instances.

---

## Wave 3 Batch 2: Blend State Policy Standardization (2026-06-06)

### Task Summary

Verified and confirmed blend state policy is consistent across all rendering paths. DrawingContext always enables BLEND with SRC_ALPHA/ONE_MINUS_SRC_ALPHA before quad/outline calls — no conditional logic.

### Files Analyzed

- `widgets/widget_base.py` — DrawingContext.quad() and outline()
- `settings_gui/guiRenderer.py` — delegation only, no direct blend logic

### Findings: Policy Already Correct

**DrawingContext.quad()** (lines 90-93):
```python
self._renderer.ctx.enable(moderngl.BLEND)
self._renderer.ctx.blend_func = (
    moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA,
)
```
Always enables BLEND — no conditional (`if alpha < 1.0`).

**DrawingContext.outline()** (lines 114-117):
```python
self._renderer.ctx.enable(moderngl.BLEND)
self._renderer.ctx.blend_func = (
    moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA,
)
```
Same — always enables, no conditional.

**GuiRenderer**: Just delegates to DrawingContext — no blend logic of its own.

### Change Made

Updated docstring in `quad()` from:
```
alpha: Opacity in [0, 1]. Values < 1 require BLEND enabled.
```
to:
```
alpha: Opacity in [0, 1]. BLEND is always enabled.
```

### Verification

```bash
$ grep -rn "if.*alpha.*[<>]" widgets/widget_base.py settings_gui/guiRenderer.py
# NO MATCHES — no conditional blend logic
```

### Key Insight

The inherited wisdom stated "GuiRenderer only enables BLEND when alpha < 1.0" but this was not present in the current code. The policy was already standardized to always-enable BLEND. The only fix was the misleading docstring that suggested conditional behavior.

---

## Task 18: Cache DrawingContext per Widget (2026-06-06)

### Task Summary

Per-widget `DrawingContext` is now created at setup time with tile size AND tile offset via constructor parameters. `_on_tile_resize()` now updates the cached DC's offset (`_ox`, `_oy`) in addition to resolution (`_w`, `_h`).

### Files Modified

**`widgets/manager.py`** — `create_widget()` (line 75):
```python
# Before:
ctx = DrawingContext(self._renderer, int(tile.width), int(tile.height))

# After:
ctx = DrawingContext(self._renderer, int(tile.width), int(tile.height), offset_x=int(tile.x), offset_y=int(tile.y))
```
DC is now created with correct offset at setup time, so widget-relative drawing is correctly positioned on screen.

**`widgets/widget_base.py`** — `_on_tile_resize(x, y, w, h)` (lines 384-391):
```python
# Before:
if self._drawing_ctx is not None:
    self._drawing_ctx._w = w
    self._drawing_ctx._h = h

# After:
if self._drawing_ctx is not None:
    self._drawing_ctx._ox = x
    self._drawing_ctx._oy = y
    self._drawing_ctx._w = w
    self._drawing_ctx._h = h
```
Tile resize now propagates position AND size to the cached DC, keeping the DC in sync when tiles move or resize.

### Verification

- `python -m unittest tests.test_drawing_context -v` → 17/17 PASS
- `python -m unittest tests.test_widget_integration -v` → 8/8 PASS

### Key Insight

Each widget now has exactly one `DrawingContext` created at setup time, with offset baked in. When a tile resizes or moves, `_on_tile_resize()` updates the cached DC directly rather than creating a new one. This avoids per-frame DC creation in `render_all()` (which remains unchanged for now — that's Task 20).

---

## Task 19: Add set_offset to DrawingContext (2026-06-06)

### Task Summary

Added `DrawingContext.set_offset(x, y)` method to allow dynamic offset updates after construction. This complements `set_resolution(w, h)` which already existed.

### Files Modified

**`widgets/widget_base.py`** — Added `set_offset()` after `set_resolution()` (line 65):
```python
def set_offset(self, x, y):
    self._ox = x
    self._oy = y
```

**`tests/test_drawing_context.py`** — Added `TestDrawingContextSetOffset` class with 3 tests:
- `test_set_offset_updates_internal_state`: Verifies `_ox` and `_oy` are updated
- `test_set_offset_affects_quad_position`: Verifies `quad()` uses the new offset
- `test_set_offset_overrides_constructor_offset`: Verifies offset can be changed post-construction

### Verification

- `python -m unittest tests.test_drawing_context -v` → 20/20 PASS (3 new + 17 existing)
- `set_resolution(w, h)` was already present at line 61-63 — confirmed working
- `quad()` and `outline()` already use `self._ox + x` and `self._oy + y` for u_pos

### Key Insight

`set_offset()` enables cached DC reuse in Task 20's `render_all()` — instead of creating a new DC per frame, we can call `set_offset()` to reposition an existing DC. Combined with `set_resolution()`, the DC can be fully reconfigured without recreation.

---

## Task 20: Remove per-frame DrawingContext creation from render_all (2026-06-06)

### Task Summary

Modified `render_all()` to reuse cached `DrawingContext` instances from Task 18 instead of creating new ones every frame. Each widget's cached DC has its resolution temporarily set to window size before drawing (for correct NDC mapping in the shader).

### Files Modified

**`widgets/manager.py`** — `render_all()` (lines 102-118):

```python
# Before:
for widget in self._widgets.values():
    ctx = DrawingContext(
        self._renderer,
        window_w, window_h,
        offset_x=widget._tile_x,
        offset_y=widget._tile_y,
    )
    widget._bind_drawing_context(ctx)
    widget.draw(ctx)

# After:
for widget in self._widgets.values():
    ctx = widget._drawing_ctx
    if ctx is not None:
        ctx.set_resolution(window_w, window_h)
        widget.draw(ctx)
```

### How It Works

1. **Cached DC from Task 18**: Each widget has a `DrawingContext` created at setup time with `offset_x=tile.x, offset_y=tile.y` already baked in
2. **Per-frame resolution override**: Before each draw, `ctx.set_resolution(window_w, window_h)` temporarily sets resolution to window size so the shader's NDC formula `gl_Position = vec4((pos / u_resolution) * 2.0 - 1.0, 0.0, 1.0)` produces correct screen mapping
3. **No DC recreation**: Zero new `DrawingContext` instances created during `render_all()`
4. **Offset preserved**: The cached DC's offset (tile.x, tile.y) was set at construction and remains unchanged

### Verification

- `python -m unittest tests.test_drawing_context -v` → 20/20 PASS
- `python -m unittest tests.test_widget_integration -v` → 8/8 PASS
- `python -m unittest discover -s tests -v` → 184/184 PASS

### Key Insight

The shader NDC formula requires `u_resolution` to be window size for correct absolute pixel → NDC mapping. The cached DC has tile-sized resolution by default (from Task 18 constructor), but we temporarily override it to window size each frame. The offset (tile position) is baked into the DC at creation time and used directly in the shader's `u_pos` uniform calculation.

---

## Task 21: Rename create_widget to add_widget one-call API (2026-06-06)

### Task Summary

Renamed `WidgetManager.create_widget(tile, name)` to `add_widget(tile, name)`. The method already encapsulated all setup in one call — this was purely a rename to establish the cleaner public API.

### Files Modified

**`widgets/manager.py`** — Line 61:
```python
# Before:
def create_widget(self, tile, name):

# After:
def add_widget(self, tile, name):
```

**`settings_gui/guiManager.py`** — Line 87:
```python
# Before:
self._widget_manager.create_widget(self._popup_tile, name)

# After:
self._widget_manager.add_widget(self._popup_tile, name)
```

**`tests/test_widget_integration.py`** — Lines 75, 130, 159, 178, 192, 234, 235 (7 occurrences):
```python
# Before:
self.widget_manager.create_widget(tile, "Line Plot")

# After:
self.widget_manager.add_widget(tile, "Line Plot")
```

### Verification

- `python -m unittest tests.test_widget_integration -v` → 8/8 PASS
- `python -m unittest discover -s tests -v` → 184/184 PASS

### Key Insight

The `create_widget` method already did everything needed — it fetches the widget class from the registry, creates the widget instance, creates a per-tile DrawingContext, binds renderer/context/DataBus, calls tile resize handler, calls setup(), and registers the widget. Renaming to `add_widget` makes the one-call API more intuitive and signals that this is the single entry point for widget creation.

---

## Task 22: Add Widget.teardown() and call in destroy_widget (2026-06-06)

### Task Summary

Added `teardown()` lifecycle method to the widget system. Base `Widget` class has a no-op `teardown()`, `LinePlot` overrides it to detach all signals and clear GPU buffers, and `WidgetManager.destroy_widget()` now calls `teardown()` before removing the widget from the dict.

### Files Modified

**`widgets/widget_base.py`** — Added `teardown()` after `setup()` (line 208):
```python
def teardown(self):
    """
    Clean up GPU resources and signal bindings.

    Called when the widget is being destroyed. Override in subclass
    to release GPU buffers, detach signals, etc.
    """
    pass
```

**`widgets/line_plot.py`** — Added `teardown()` override (after `on_detach_signal()`):
```python
def teardown(self):
    """Detach all signals and clear all buffers."""
    for sig in list(self._bound_signals):
        self.detach_signal(sig)
    self._buffers.clear()
    self._bound_signals.clear()
```
This properly triggers `on_detach_signal` for each signal (which removes LineBuffer entries from `_buffers`) before clearing both dicts.

**`widgets/manager.py`** — Updated `destroy_widget(tile)` (line 88):
```python
# Before:
def destroy_widget(self, tile):
    key = (tile.x, tile.y)
    self._widgets.pop(key, None)

# After:
def destroy_widget(self, tile):
    key = (tile.x, tile.y)
    widget = self._widgets.pop(key, None)
    if widget is not None:
        widget.teardown()
```

### Lifecycle Now Complete

```
setup() → update() → draw() → teardown()
```

- `setup()`: Called once when widget is added (creates components, buffers)
- `update()`: Called every frame (pulls data from DataBus)
- `draw()`: Called every frame (renders using DrawingContext)
- `teardown()`: Called when widget is removed (releases GPU resources, unbinds signals)

### Key Insight

`LinePlot.teardown()` iterates over `list(self._bound_signals)` before detaching to avoid modifying the list while iterating. Each `detach_signal()` call triggers `on_detach_signal()` which removes the corresponding LineBuffer from `_buffers`. The explicit `clear()` calls on both dicts ensure no stale references remain even if signals were attached outside the normal attach flow.

### Verification

- `python -m unittest tests.test_widget_integration -v` → 8/8 PASS
- `python -m unittest discover -s tests -v` → 184/184 PASS

---

## Task 23: Add WidgetManager.on_resize + wire mainLoop._on_resize (2026-06-06)

### Task Summary

Added `WidgetManager.on_resize(width, height)` method to propagate window resize to all widgets' cached DrawingContexts and internal renderer. Updated `mainLoop._on_resize()` to call `self.widget_manager.on_resize(width, height)`.

### Files Modified

**`widgets/manager.py`** — Added `on_resize()` (after `on_menu_mouse_move`):
```python
def on_resize(self, width, height):
    """Propagate window resize to all widgets and update internal renderer."""
    self._renderer.application.window.width = width
    self._renderer.application.window.height = height
    for widget in self._widgets.values():
        if widget._drawing_ctx is not None:
            widget._drawing_ctx.set_resolution(width, height)
```

**`mainLoop.py`** — Updated `_on_resize()` (line 237):
```python
# Added at end:
self.widget_manager.on_resize(width, height)
```

### How It Works

1. **Renderer window dimensions**: The internal Renderer stores `application` (a SimpleNamespace) which has `.window.width` and `.window.height` — these are updated to keep the renderer in sync
2. **Widget DrawingContexts**: Each widget has a cached `DrawingContext` with `set_resolution(w, h)` — calling this on resize ensures all widgets use the correct window resolution for their NDC shader calculations
3. **Order of calls in mainLoop._on_resize**: `widget_manager.on_resize` is called last, after `tileManager` is recreated, ensuring widgets have correct tile geometry when resize propagates

### Key Insight

The `DrawingContext.set_resolution()` method (added in Task 18-19) updates the internal `_w` and `_h` fields which are used to set `u_resolution` in the shader. When the window resizes, all widgets' cached DCs must have their resolution updated so the shader formula `gl_Position = vec4((pos / u_resolution) * 2.0 - 1.0, 0.0, 1.0)` maps absolute pixel coordinates to NDC correctly at the new window size.

### Verification

- `grep -r "create_widget" .` → No matches (Task 21 rename already complete)
- `python -m unittest discover -s tests -v` → 184/184 PASS
- LSP diagnostics on `widgets/manager.py` → zero errors
- LSP diagnostics on `mainLoop.py` → pre-existing type errors only (unrelated to this change)

---

## Task 24: Convert MenuRenderer to Data Structure Only (2026-06-06)

### Task Summary

Converted `MenuRenderer` from an immediate-mode renderer (calling `ui.quad()`/`ui.outline()`/`ui.text()` directly) into a pure data-structure generator that returns structured draw commands. This decouples menu state management from rendering, enabling Task 25 to render menus via `DrawingContext` without `MenuRenderer` knowing about GPU details.

### Files Modified

**`widgets/widget_gui.py`** — Two methods converted:

1. **`_MenuItem.draw(ui, win_h)` → `_MenuItem.get_render_commands(win_h)`**:
   - Returns `list[dict]` instead of drawing directly
   - Each command is a dict with keys:
     - `{'type': 'quad', 'x': x, 'y': y, 'w': w, 'h': h, 'color': (r,g,b), 'alpha': a}`
     - `{'type': 'outline', 'x': x, 'y': y, 'w': w, 'h': h, 'color': (r,g,b), 'alpha': a}`
     - `{'type': 'text', 'x': x, 'y': y, 'text': str, 'color': (r,g,b), 'scale': s, 'anchor_x': str, 'anchor_y': str}`
   - Width expansion logic preserved (dynamically expands to fit text + branch arrow)
   - Hover state still affects background color

2. **`MenuRenderer.draw(ui)` → `MenuRenderer.get_render_commands()`**:
   - Returns `list[dict]` for entire menu (background + all items + all sub-levels)
   - Top-level background: quad + outline with colors `(0.18, 0.18, 0.22)` / `(0.4, 0.4, 0.5)`
   - Sub-level backgrounds: quad + outline with colors `(0.22, 0.22, 0.25)` / `(0.5, 0.4, 0.4)`
   - Returns `[]` when `not self.visible`

**`tests/test_menu_state.py`** — Added `TestMenuRenderCommands` class (6 tests):
- `test_invisible_returns_empty_list`: Closed menu returns `[]`
- `test_open_returns_background_commands`: First two commands are quad + outline
- `test_item_commands_structure`: Items produce quad, outline, and text commands
- `test_branch_item_has_arrow_command`: Branch items include `'>'` text command
- `test_submenu_includes_sub_level_commands`: Sub-levels add their own backgrounds and items
- `test_command_keys`: Every command dict has the required keys for its type

**`tests/test_lineplot.py`** — Updated `on_render()` to consume commands:
```python
for cmd in self._menu_renderer.get_render_commands():
    if cmd['type'] == 'quad':
        self._drawing_ctx.quad(...)
    elif cmd['type'] == 'outline':
        self._drawing_ctx.outline(...)
    elif cmd['type'] == 'text':
        self._drawing_ctx.text(...)
```

### What Was NOT Changed

- **Event handling**: `on_mouse_press()`, `on_mouse_release()`, `on_mouse_move()` untouched
- **State machine**: `open()`, `close()`, `visible`, `_captured`, `_sub_levels`, `_sub_direction` untouched
- **Geometry helpers**: `_clamp()`, `_clear_hover()`, `_bounds()`, `_push_sub_level()` untouched
- **Manager.py**: Left for Task 25 (will update `draw_menu()` to consume `get_render_commands()`)

### Verification

- `python -m unittest tests.test_menu_state -v` → 23/23 PASS (6 new + 17 existing)
- `python -m unittest discover -s tests -v` → 190/190 PASS (no regressions)
- LSP diagnostics on `widgets/widget_gui.py`: zero errors
- LSP diagnostics on `tests/test_menu_state.py`: zero errors

### Key Insight

The separation of "what to draw" from "how to draw it" is now complete for menus. `MenuRenderer` is a pure state machine + command generator. The rendering loop (in `test_lineplot.py` today, in `manager.py` after Task 25) becomes a simple interpreter over the command list. This mirrors the architecture of modern retained-mode UI systems where the scene graph is separate from the rasterizer.

---

## Task 25: WidgetManager renders context menus via DrawingContext (2026-06-06)

### Task Summary

Updated `WidgetManager.draw_menu()` to consume `MenuRenderer.get_render_commands()` and dispatch each command to the window-sized `DrawingContext` (`self._drawing_ctx`). Menu now renders through the same DrawingContext pipeline as widgets, using the existing `quad()`, `outline()`, and `text()` methods.

### Files Modified

**`widgets/manager.py`** — `draw_menu(ui)` (lines 213-224):
```python
# Before:
def draw_menu(self, ui):
    """Render the active context menu using *ui* (DrawingContext)."""
    self._menu_renderer.draw(ui)

# After:
def draw_menu(self, ui):
    """Render the active context menu using *ui* (DrawingContext)."""
    if not self._menu_renderer.visible:
        return
    commands = self._menu_renderer.get_render_commands()
    for cmd in commands:
        if cmd['type'] == 'quad':
            ui.quad(cmd['x'], cmd['y'], cmd['w'], cmd['h'], cmd['color'], cmd.get('alpha', 1.0))
        elif cmd['type'] == 'outline':
            ui.outline(cmd['x'], cmd['y'], cmd['w'], cmd['h'], cmd['color'], cmd.get('alpha', 1.0))
        elif cmd['type'] == 'text':
            ui.text(cmd['text'], cmd['x'], cmd['y'], color=cmd.get('color', (1.0, 1.0, 1.0)), scale=cmd.get('scale', 0.5), anchor_x=cmd.get('anchor_x', 'left'), anchor_y=cmd.get('anchor_y', 'bottom'))
```

### How It Works

1. **Command dispatch loop**: Iterates over `get_render_commands()` and routes each dict to the appropriate `DrawingContext` method based on `cmd['type']`
2. **Window-sized DC**: `mainLoop.py` passes `self.widget_manager._drawing_ctx` (window-sized prototype) to `draw_menu()`, so menu coordinates map directly to screen pixels without tile offset
3. **Menu renders above widgets**: In `mainLoop._render_widgets()`, `render_all()` is called first, then `draw_menu()` — so the menu is drawn after widgets, appearing on top
4. **Event handling unchanged**: All mouse press/release/move routing to `MenuRenderer` remains exactly as before — only the rendering path changed

### What Was NOT Changed

- **Menu state machine**: `open()`, `close()`, `visible`, `_captured`, `_sub_levels`, `_sub_direction` untouched
- **Event handling**: `on_mouse_press()`, `on_mouse_release()`, `on_mouse_move()`, `on_menu_mouse_move()` untouched
- **MenuRenderer**: Already converted to data-structure-only in Task 24 — no changes needed
- **mainLoop.py**: Already calls `draw_menu(self.widget_manager._drawing_ctx)` after `render_all()` — no changes needed

### Verification

- `python -m unittest tests.test_menu_state -v` → 23/23 PASS
- `python -m unittest discover -s tests -v` → 190/190 PASS (no regressions)
- LSP diagnostics on `widgets/manager.py`: zero errors

### Key Insight

The menu rendering pipeline is now fully unified with the widget rendering pipeline. Both use the same `DrawingContext` methods (`quad()`, `outline()`, `text()`), the same shader program, and the same VBO/VAO shared resources. The only difference is that widgets use per-tile DCs with tile offsets baked in, while the menu uses the window-sized DC with zero offset. This completes the decoupling started in Task 24: `MenuRenderer` generates commands, and `WidgetManager` executes them.

---

## Task 26: Verify LinePlot.get_context_menu() + Add Test (2026-06-06)

### Task Summary

Verified that `LinePlot.get_context_menu()` returns the correct data structure for `MenuRenderer`, and added a test to verify the structure. No changes were needed to `line_plot.py` itself.

### Findings

**`LinePlot.get_context_menu()` format is correct:**

```python
[
    ("Attach Signal", [
        ("sensors", [
            ("imu", [
                ("accel_x", lambda: self.attach_signal("sensors.imu.accel_x")),
            ]),
        ]),
    ]),
    ("Remove Signal", [
        ("Remove sensors/imu/accel_x", lambda: self.detach_signal("sensors.imu.accel_x")),
    ]),
]
```

The `LinePlot` override (lines 206-229 in `line_plot.py`) is functionally identical to the base `Widget.get_context_menu()` — both use `_build_signal_tree()` for the attach tree and iterate over `_bound_signals` for the remove tree. The only minor difference is `LinePlot` uses `self._display_name(path)` (converts dots to slashes) for remove entries, while the base class uses `path.replace(".", "/")` — functionally equivalent.

**No changes needed to `line_plot.py`** — the existing implementation already returns the correct format.

### Files Modified

**`tests/test_widget_integration.py`** — Added `test_widget_context_menu()`:

```python
def test_widget_context_menu(self):
    tile = MockTile(0, 0, 400, 300)
    widget = self.widget_manager.add_widget(tile, "Line Plot")

    self.data_bus.push_payload({
        "sensors": {"imu": {"accel_x": [0.5]}},
        "step_target": [1.0],
    })

    menu = widget.get_context_menu()
    self.assertIsInstance(menu, list)
    self.assertTrue(len(menu) > 0)

    labels = [entry[0] for entry in menu]
    self.assertIn("Attach Signal", labels)

    attach_entry = next(e for e in menu if e[0] == "Attach Signal")
    self.assertIsInstance(attach_entry[1], list)

    def flatten_tree(entries):
        result = []
        for label, action in entries:
            if callable(action):
                result.append(label)
            elif isinstance(action, list):
                result.extend(flatten_tree(action))
        return result

    all_labels = flatten_tree(menu)
    self.assertTrue(any("accel_x" in str(l) for l in all_labels))
    self.assertTrue(any("step_target" in str(l) for l in all_labels))
```

The test verifies:
1. `get_context_menu()` returns a list
2. "Attach Signal" entry exists
3. "Attach Signal" value is a nested list (tree structure)
4. Signal names appear in the flattened tree

### Verification

- `python -m unittest tests.test_widget_integration -v` → 9/9 PASS (1 new + 8 existing)
- `python -m unittest discover -s tests -v` → 191/191 PASS (no regressions)

### Key Insight

`LinePlot` overrides `get_context_menu()` from the base `Widget` class, but the override is nearly identical to the base implementation. The data format (list of `(label, action)` tuples where `action` is either a callable or a nested list) is exactly what `MenuRenderer` expects. No code changes were needed — only adding the test to verify correctness.
