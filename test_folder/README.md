# GUI / Widget System — Architecture & Usage Guide

> **Canonical reference for all agents working on this project.**
> Consult this file before modifying any file in `widgets/`, `settings_gui/`, `tile_management/`, or `window/`.

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Coordinate System (Bottom-Up Everywhere)](#coordinate-system)
3. [Rendering Pipeline](#rendering-pipeline)
4. [Widget Lifecycle](#widget-lifecycle)
5. [WidgetManager API](#widgetmanager-api)
6. [Writing a Custom Widget](#writing-a-custom-widget)
7. [Context Menus](#context-menus)
8. [Key Design Decisions](#key-design-decisions)
9. [What NOT to Change](#what-not-to-change)
10. [File Map](#file-map)

---

## Architecture Overview

The GUI/widget system is composed of four layers:

```
┌─────────────────────────────────────────────────────────────┐
│  Layer 4: Application (mainLoop.py)                         │
│  - Owns TileManager, WidgetManager, GuiManager, BlipGui    │
│  - Forwards input events to the correct layer              │
│  - Manages window resize propagation                       │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│  Layer 3: Widget System (widgets/)                          │
│  - WidgetManager: bridges tile strings → Widget instances  │
│  - Widget: base class for user-contributed visualisations  │
│  - MenuRenderer: right-click context menus (data only)     │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│  Layer 2: Settings GUI (settings_gui/)                     │
│  - GuiManager: tile popup editor (bottom-up coords)        │
│  - BlipGui: draggable popup annotations                    │
│  - GuiRenderer: thin wrapper around DrawingContext         │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│  Layer 1: Tile Management (tile_management/)               │
│  - TileManager: 2×2 grid, split/merge/resize              │
│  - Tile: stores geometry (bottom-up coordinates)           │
└─────────────────────────────────────────────────────────────┘
```

**Input flow:**
```
moderngl_window (top-down) → mainLoop.py (passes through)
                                    │
                    ┌───────────────┼───────────────┐
                    ▼               ▼               ▼
              GuiManager      WidgetManager    ModelAligner
              (bottom-up)     (bottom-up)     (bottom-up)
```

---

## Coordinate System

### Rule: Bottom-Up Everywhere

**y = 0 is at the BOTTOM of the window/tile.** No exceptions.

```
Window (1280×720)
┌──────────────────────┐  ← y = 720 (top edge)
│                      │
│                      │
│                      │
│                      │
│                      │
└──────────────────────┘  ← y = 0   (bottom edge)
```

### Where coordinates are flipped

| Source | System | Direction |
|--------|--------|-----------|
| `moderngl_window` | Mouse events | Top-down (y=0 at top) |
| **Our code** | All GUI / Widgets / Tiles | **Bottom-up** (y=0 at bottom) |

The flip happens **at the boundary** in `mainLoop.py` and `window/mainWindow.py` — everything downstream receives bottom-up coordinates. There are **no Y-flip conversions** inside `settings_gui/`, `widgets/`, `window/model_aligner.py`, or `tile_management/`.

### Tile coordinates

Tiles store their position in **bottom-up** coordinates:

```python
class Tile:
    x: int      # left edge, screen space
    y: int      # bottom edge, screen space
    width: int
    height: int
```

The TileManager computes bottom-up y before passing to the Tile constructor:

```python
y_topdown = [0, (height + gap) / 2]
y_bottomup = [height - ytd - height for ytd in y_topdown]
```

### Widget local coordinates

Widgets receive **local coordinates** where `(0, 0)` is the tile's bottom-left corner:

```python
# In WidgetManager
widget.on_mouse_press(x - widget._tile_x, y - widget._tile_y, button)
```

So inside a widget, `(0, 0)` is always the bottom-left of its tile.

---

## Rendering Pipeline

### Single DrawingContext for All 2D UI

There is **exactly one shader program** and **one set of VBOs/VAOs** for all 2D UI rendering:

```
widgets/shaders/ui.vert
widgets/shaders/ui.frag     ← canonical location, only copies
```

`DrawingContext` manages these GPU resources as **class-level singletons** (`_init_shared()`). Every `DrawingContext` instance and `GuiRenderer` wrapper shares the same shader + buffers.

### Rendering flow per frame

```python
# In WidgetManager.render_all()
for widget in self._widgets.values():
    ctx = widget._drawing_ctx          # cached at setup
    ctx.set_resolution(window_w, window_h)  # temporarily override for NDC
    widget.draw(ctx)

# In mainLoop.py (after widgets)
if widget_manager.is_menu_open():
    widget_manager.draw_menu(widget_manager._drawing_ctx)
```

The cached DrawingContext already has the tile offset baked in. `set_resolution()` temporarily overrides resolution to window size so the vertex shader (`pos / resolution * 2 - 1`) maps to correct screen NDC.

### GuiRenderer is a wrapper

`settings_gui/guiRenderer.py` delegates all drawing to `DrawingContext`:

```python
class GuiRenderer:
    def __init__(self, mainWindow, width, height):
        self._dc = DrawingContext(mainWindow, width, height)

    def quad(self, x, y, w, h, color, alpha=1.0):
        self._dc.quad(x, y, w, h, color, alpha)

    def outline(self, x, y, w, h, color, alpha=1.0):
        self._dc.outline(x, y, w, h, color, alpha)

    def text(self, text_str, x, y, color, scale, anchor_x, anchor_y, clip_rect):
        self._dc.text(text_str, x, y, color, scale, anchor_x, anchor_y, clip_rect)
```

This eliminates duplicate shader/VBO/VAO state that previously existed between `GuiRenderer` and `DrawingContext`.

---

## Widget Lifecycle

### Full lifecycle

```
add_widget(tile, "Line Plot")
    │
    ├── Registry lookup → LinePlot class
    ├── Instantiate widget
    ├── Create DrawingContext(tile.width, tile.height, offset_x=tile.x, offset_y=tile.y)
    ├── Bind renderer → widget._renderer
    ├── Bind drawing context → widget._drawing_ctx
    ├── Bind data_bus → widget._data_bus
    ├── _on_tile_resize(x, y, w, h)  → stores tile geometry + updates DC offset
    ├── setup()                         → one-time init (create LineBuffers, etc.)
    └── Store in _widgets[(tile.x, tile.y)]

Every frame:
    ├── update_all() → widget.update() for each widget
    └── render_all() → widget.draw(ctx) for each widget (reuses cached DC)

destroy_widget(tile)
    ├── Pop widget from _widgets
    └── widget.teardown() → cleanup (detach signals, clear buffers)
```

### Cached DrawingContext

Each widget owns **one** `DrawingContext` created at `add_widget()` time. It is **reused every frame** — no per-frame allocation.

The DC stores:
- `_ox`, `_oy` = tile position (screen space, bottom-up)
- `_w`, `_h` = tile dimensions

At render time, `render_all()` temporarily overrides `_w`, `_h` to window size for correct NDC mapping. The next frame resets it again.

---

## WidgetManager API

```python
from widgets.manager import WidgetManager

# Create
wm = WidgetManager(mainWindow, data_bus)

# Add a widget (ONE call — all setup encapsulated)
widget = wm.add_widget(tile, "Line Plot")

# Update all widgets per frame
wm.update_all()

# Render all widgets per frame
wm.render_all()

# Resize propagation (call on window resize)
wm.on_resize(width, height)

# Destroy a widget
wm.destroy_widget(tile)

# Context menus
wm.open_context_menu(tile, screen_x, screen_y)
wm.close_context_menu()
wm.is_menu_open()

# Input forwarding (already in local coords)
wm.on_mouse_press(x, y, button)
wm.on_mouse_release(x, y, button)
wm.on_mouse_drag(x, y, dx, dy, buttons)
wm.on_mouse_scroll(x, y, scroll_x, scroll_y)
wm.on_menu_mouse_move(x, y)
```

---

## Writing a Custom Widget

### Minimal example

```python
from widgets.widget_base import Widget, DrawingContext

class MyWidget(Widget):
    title = "My Widget"
    transparent = False          # Draws a solid background
    required_shape = [(1,)]    # Accepts scalar signals only

    def setup(self):
        """Called once after assignment to a tile."""
        self._value = 0.0

    def update(self):
        """Called every frame. Pull DataBus data."""
        val = self.read("sensor.temperature")
        if val is not None:
            self._value = val

    def draw(self, ui: DrawingContext):
        """Called every frame. Render with DrawingContext."""
        w, h = self.size
        ui.quad(10, 10, w - 20, h - 20, (0.2, 0.2, 0.3))
        ui.text(f"{self._value:.2f}", 20, h - 30, scale=0.8)
```

### Custom context menu

```python
    def get_context_menu(self):
        entries = super().get_context_menu()  # Attach/Remove Signal branches
        entries.append(("Custom Action", lambda: self.do_thing()))
        entries.append(("Sub Menu", [
            ("Sub 1", lambda: self.sub_1()),
            ("Sub 2", lambda: self.sub_2()),
        ]))
        return entries
```

### Input events (optional)

```python
    def on_mouse_press(self, x, y, button):
        """x, y are LOCAL to the tile (0,0 = bottom-left)."""
        pass

    def on_mouse_release(self, x, y, button):
        pass

    def on_mouse_drag(self, x, y, dx, dy, buttons):
        pass

    def on_mouse_scroll(self, x, y, scroll_x, scroll_y):
        pass
```

### GPU resources

```python
    def setup(self):
        # Create a GPU-backed ring buffer for streaming data
        self._buffer = self.create_line_buffer(max_points=1000)
```

### Cleanup

```python
    def teardown(self):
        """Called when the widget is destroyed."""
        # Detach signals, clear buffers, release GPU resources
        super().teardown()
```

---

## Context Menus

### How they work

1. **Widget produces data** — `get_context_menu()` returns `[(label, action), ...]`
2. **MenuRenderer tracks state** — open, hover, click, nested sub-menus
3. **WidgetManager renders** — `draw_menu()` calls `get_render_commands()` then executes via `DrawingContext`

### MenuRenderer data structure

```python
class MenuRenderer:
    def get_render_commands(self) -> list[dict]:
        """Returns draw commands for the entire menu."""
        # Commands are dicts:
        # {'type': 'quad',   'x': x, 'y': y, 'w': w, 'h': h, 'color': (r,g,b), 'alpha': a}
        # {'type': 'outline', 'x': x, 'y': y, 'w': w, 'h': h, 'color': (r,g,b), 'alpha': a}
        # {'type': 'text',   'x': x, 'y': y, 'text': str, 'color': (r,g,b), 'scale': s, 'anchor_x': ..., 'anchor_y': ...}
```

### Sub-menu direction

Nested sub-menus maintain a **consistent left/right direction** across all levels:
- First sub-menu prefers right, falls back to left if it would overflow
- Once a direction is chosen, all subsequent sub-menus follow it
- Resets to `None` when all sub-levels are closed

---

## Key Design Decisions

### 1. Bottom-Up Coordinates Everywhere

**Decision:** All internal code uses bottom-up (y=0 at bottom). The only top-down coordinates come from `moderngl_window` mouse events, which are passed through without modification.

**Rationale:** Eliminates the bug-prone `win_h - y` conversions scattered across 15+ sites. The GPU/shader pipeline already expected bottom-up; now the CPU code matches.

**Consequence:** If you see `win_h - y` or `height - y` in new code, it is almost certainly a bug.

### 2. Single DrawingContext / Single Shader Set

**Decision:** `GuiRenderer` wraps `DrawingContext`. Both share one shader program and one VBO set via class-level `_init_shared()`.

**Rationale:** Eliminates duplicate GL state (previously two identical shader programs, two sets of VBOs/VAOs).

**Consequence:** Do not create new shader programs for UI rendering. Use `DrawingContext` or `GuiRenderer`.

### 3. Cached DrawingContext Per Widget

**Decision:** Each widget gets one `DrawingContext` at `add_widget()` time. `render_all()` reuses it every frame.

**Rationale:** Eliminates per-frame GPU resource allocation (`__init__` calls `create_standalone_context()` for shader compilation).

**Consequence:** `_on_tile_resize()` must update the cached DC's offset and resolution.

### 4. One-Call Widget Creation

**Decision:** `widget_manager.add_widget(tile, "Name")` encapsulates all setup.

**Rationale:** Previously 7 manual steps (registry lookup, instantiate, create DC, bind renderer, bind DC, bind DataBus, call setup).

**Consequence:** Do not call `_bind_renderer()`, `_bind_drawing_context()`, `_bind_data_bus()`, or `_on_tile_resize()` manually.

### 5. MenuRenderer Returns Data, Not Draws

**Decision:** `MenuRenderer` has no `draw()` method. It returns `get_render_commands()`, and `WidgetManager.draw_menu()` executes them via `DrawingContext`.

**Rationale:** Unifies menu rendering into the same pipeline as widgets and tile popups.

**Consequence:** If adding new menu visual elements, add new command dict types to `get_render_commands()` and handle them in `draw_menu()`.

### 6. Widgets Receive Local Coordinates

**Decision:** `WidgetManager` converts screen→local before forwarding mouse events. Inside a widget, `(0, 0)` is always the tile's bottom-left.

**Rationale:** Widgets don't need to know their screen position to handle input.

**Consequence:** Widget event handlers should never reference `self._tile_x` or `self._tile_y` for input math.

---

## What NOT to Change

### Forbidden modifications

| Guardrail | Reason |
|-----------|--------|
| **Do NOT modify `core/data_bus.py`** | DataBus and SignalSchema are stable APIs |
| **Do NOT modify `vizcore/`** | Legacy package, separate migration effort |
| **Do NOT add new features during refactors** | Scope control — new features need their own plan |
| **Do NOT introduce top-down coordinates** | Would reintroduce the Y-flip bug |
| **Do NOT create duplicate shader programs** | Violates the single-pipeline design |
| **Do NOT make per-frame DrawingContext allocations** | Violates the caching design |

### Files to avoid touching

```
vizcore/                    ← legacy, off-limits
core/data_bus.py            ← stable API
core/signal_schema.py       ← stable API
examples/exampleSim.py      ← example data source (ok to read, not modify)
```

---

## File Map

### Core widget system

| File | Purpose |
|------|---------|
| `widgets/widget_base.py` | `Widget` base class + `DrawingContext` |
| `widgets/widget_gui.py` | `MenuRenderer` + `_MenuItem` classes |
| `widgets/manager.py` | `WidgetManager` — lifecycle, rendering, events |
| `widgets/line_plot.py` | Example widget: `LinePlot` |
| `widgets/registry.py` | `WidgetRegistry` — name → class mapping |

### Settings GUI

| File | Purpose |
|------|---------|
| `settings_gui/guiManager.py` | Tile popup editor (bottom-up coords) |
| `settings_gui/blipGui.py` | Draggable popup annotations |
| `settings_gui/guiRenderer.py` | Thin wrapper around `DrawingContext` |
| `settings_gui/elements/` | Button, Branch, Slider, Toggle |

### Tile management

| File | Purpose |
|------|---------|
| `tile_management/manager.py` | `TileManager` — 2×2 grid, split/merge/resize |
| `tile_management/tile.py` | `Tile` — stores geometry (bottom-up) |

### Window / rendering

| File | Purpose |
|------|---------|
| `window/mainWindow.py` | Window class + render callbacks |
| `window/model_aligner.py` | 3D model alignment tool (bottom-up) |
| `window/render_pipeline.py` | Depth-test toggle wrappers |

### Entry point

| File | Purpose |
|------|---------|
| `mainLoop.py` | Application loop — owns all managers, forwards events |

### Shaders (canonical location)

```
widgets/shaders/ui.vert     ← single vertex shader for all 2D UI
widgets/shaders/ui.frag     ← single fragment shader for all 2D UI
```

---

## Testing

All changes must pass the full test suite:

```bash
python -m unittest discover -s tests -v
```

Current status: **191 tests pass**.

Key test files:
- `tests/test_coordinates.py` — Y-flip regression (40 tests)
- `tests/test_tile_geometry.py` — TileManager geometry (37 tests)
- `tests/test_event_forwarding.py` — Event routing (21 tests)
- `tests/test_menu_state.py` — Menu state machine (23 tests)
- `tests/test_drawing_context.py` — DC lifecycle (20 tests)
- `tests/test_widget_integration.py` — End-to-end lifecycle (9 tests)

---

## Historical Context

This system was refactored in **June 2026** from a fragmented state:
- **Before:** 15 Y-flip sites, 2 rendering pipelines, 7-step widget setup, duplicate shaders
- **After:** Zero Y-flips, single DrawingContext pipeline, 1-call `add_widget()`, unified shader set

See `.omo/plans/gui-simplification.md` for the full 26-task plan and `.omo/notepads/gui-simplification/learnings.md` for detailed findings per wave.
