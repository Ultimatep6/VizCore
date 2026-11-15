# LinePlot Integration Learnings

## Wave 1a: WidgetRegistry (2026-06-06)

### Decision: Simple dict-based registry

Chose a plain `dict` over any fancy pattern (e.g. entry points, pluggy-style discovery) because:
- This is Wave 1a — foundation only, no dynamic discovery
- `WidgetManager` (Wave 4) needs a direct, importable registry
- No plugin discovery or filesystem scanning needed yet

### Implementation

- `WidgetRegistry` class with `register(name, widget_class)`, `get(name)`, `list_names()`
- `default_registry` module-level instance
- LinePlot registered with name `"Line Plot"` (matches `LinePlot.title`)

### File created

- `widgets/registry.py`

### Verification

```bash
python -c "from widgets.registry import default_registry; from widgets.line_plot import LinePlot; assert default_registry.get('Line Plot') is LinePlot; print('PASS')"
# PASS
```

## Wave 4: WidgetManager (2026-06-06)

### Decision: Manager owns widget lifecycle and bridges GUI tiles to instances

- Widgets are **not** stored on `Tile` objects (`Tile.widget` remains a string name)
- `WidgetManager` tracks active widgets in an internal `dict` keyed by `(tile.x, tile.y)`
- One widget per tile only — no multi-widget-per-tile support

### Implementation

- `WidgetManager.__init__(mainWindow, data_bus, registry=None)`:
  - Creates internal `Renderer` from `vizcore.renderer.renderer.Renderer`
  - Creates a window-sized `DrawingContext` prototype
  - Instantiates `MenuRenderer` for context menus
- `create_widget(tile, name)`:
  - Looks up widget class via `registry.get(name)`
  - Follows exact test harness wiring: `_bind_renderer` -> `_bind_drawing_context` -> `_bind_data_bus` -> `_on_tile_resize` -> `setup()`
  - Creates a dedicated `DrawingContext` sized to the tile
- `render_all()`:
  - Iterates active widgets
  - Creates a fresh `DrawingContext` per tile (sized to current `widget.size`)
  - Re-binds context and calls `widget.draw(ctx)`
- Input forwarding (`on_mouse_press`, `on_mouse_release`, `on_mouse_drag`, `on_mouse_scroll`):
  - Menu gets first priority when visible
  - Otherwise finds widget under cursor and forwards tile-local coordinates
- Context menus:
  - `open_context_menu(tile, screen_x, screen_y)` uses `widget.get_context_menu()` and `MenuRenderer.open()`
  - `close_context_menu()` delegates to `MenuRenderer.close()`
  - `draw_menu(ui)` renders the active menu overlay

### File created

- `widgets/manager.py`

### Verification

```bash
python -c "from widgets.manager import WidgetManager; print(dir(WidgetManager))"
# Shows: create_widget, destroy_widget, update_all, render_all, on_mouse_press,
#        on_mouse_release, on_mouse_drag, on_mouse_scroll, open_context_menu,
#        close_context_menu, is_menu_open, draw_menu, on_menu_mouse_move
# PASS
```

### Next steps

- `GuiManager` can now delegate widget lifecycle to `WidgetManager`
- Right-click on a tile -> `widget_manager.open_context_menu(tile, x, y)`
- Render loop -> `widget_manager.update_all()` then `widget_manager.render_all()` then `widget_manager.draw_menu(ui)`

## Wave 2a-1: render_widgets Callback Integration (2026-06-06)

### Decision: Insert render_widgets between render_nodes and render_tileManager

The render pipeline order is:
1. `render_nodes` - 3D scene with depth test enabled
2. `depth_mask = False` + `DEPTH_TEST disabled` - enter 2D overlay mode
3. `render_widgets` - widget overlay rendering (new)
4. `render_tileManager` - tile borders
5. `render_guiManager` - GUI elements

### Implementation

- `window/mainWindow.py`: Added callback invocation at line 471, inside the depth-mask block
- `mainLoop.py`: Added `rc.render_widgets = self._render_widgets` binding at line 76
- `_render_widgets(self)` stub created at line 197 (to be filled in Task 10)

### Verification

```bash
grep -n render_widgets window/mainWindow.py mainLoop.py
# mainWindow.py:471: if cb := getattr(self.render_callbacks, "render_widgets", None):
# mainLoop.py:76: rc.render_widgets = self._render_widgets
# mainLoop.py:197: def _render_widgets(self):
```

### Next steps

- Task 10 will implement `_render_widgets` to call `widget_manager.render_all()`
- Widgets render after 3D scene (nodes) but before tile borders - correct z-order for overlays

## Wave 5: GuiManager Integration (2026-06-06)

### Decision: GuiManager delegates widget lifecycle to WidgetManager when available

- `GuiManager.__init__` now accepts optional `widget_manager` parameter
- `_build_widget_list()` uses `widget_manager.list_names()` when `widget_manager` is set, otherwise falls back to `self._widgets`
- `_add_widget(name)` calls `widget_manager.create_widget(self._popup_tile, name)` before setting `tile.widget`
- `_remove_widget(tile)` calls `widget_manager.destroy_widget(tile)` before setting `tile.widget = None`
- Backward compatible: works without `widget_manager` (string-only mode)

### Implementation

- Import `default_registry` from `widgets.registry`
- New parameter: `widget_manager=None` in `__init__`
- New field: `self._widget_manager = widget_manager`

### File modified

- `settings_gui/guiManager.py`

### Verification

```bash
python -c "from settings_gui.guiManager import GuiManager; import inspect; print('widget_manager' in inspect.signature(GuiManager.__init__).parameters)"
# True
```

## Wave 7: MainLoop Infrastructure Setup (2026-06-06)

### Decision: Wire DataBus, WidgetManager, and GuiManager in MainLoopHandler

- `MainLoopHandler` now owns the `DataBus` and `WidgetManager` lifecycle
- `WidgetManager` is instantiated in `run()` after `dashboardInstance` and before `GuiManager`
- `GuiManager` receives `widget_manager` via constructor parameter
- `rc.render_widgets = self._render_widgets` already bound in Wave 2a-1

### Implementation

- Imports added: `DataBus`, `Renderer`, `WidgetManager`, `default_registry`
- `self.data_bus = DataBus()` created in `__init__`
- `self.widget_manager = WidgetManager(self.dashboardInstance, self.data_bus, default_registry)` created in `run()`
- `self.guiManager = GuiManager(self.dashboardInstance, widget_manager=self.widget_manager)` updated in `run()`

### File modified

- `mainLoop.py`

### Verification

```bash
python -c "from mainLoop import MainLoopHandler; m = MainLoopHandler(); print(type(m.data_bus))"
# <class 'core.data_bus.DataBus'>

python -m py_compile mainLoop.py
# PASS (no output)
```

## Wave 8: Mouse Event Forwarding and Widget Context Menus (2026-06-06)

### Decision: Forward mouse events to widgets when not pressing ctrl, and handle widget context menus on RMB

- Widget context menu and tile popup are mutually exclusive
- Ctrl closes widget menus and preserves existing tile popup behavior
- Blip picking is preserved when RMB is not on a widget tile

### Implementation

- `_on_key_press(ctrl_pressed)`:
  - If ctrl is pressed while widget menu is open, close it via `widget_manager.close_context_menu()`
- `_on_mouse_press(x, y, button)`:
  - RMB + ctrl: unchanged tile popup behavior, but closes any open widget menu first
  - RMB without ctrl: checks if cursor is inside a tile with `tile.widget` set
  - If yes: closes tile popup (`guiManager.close_popup()`) and opens widget context menu (`widget_manager.open_context_menu(tile, x, y)`)
  - If no: falls through to existing blip picking
- `_on_mouse_release(x, y, button)`:
  - If `widget_manager.is_menu_open()`: forwards to `widget_manager.on_mouse_release(x, y, button, 0)` and returns
  - Otherwise: existing behavior
- `_on_mouse_drag(x, y, dx, dy)`:
  - If not ctrl and `widget_manager._widgets` is non-empty: forwards to `widget_manager.on_mouse_drag(x, y, dx, dy, 0, 0)` and returns
  - Otherwise: existing behavior
- `_on_scroll(x_offset, y_offset)`:
  - If not ctrl: forwards to `widget_manager.on_mouse_scroll(self.input.x, self.input.y, x_offset, y_offset)`
  - Otherwise: existing behavior (pass)

### File modified

- `mainLoop.py`

### Verification

```bash
python -m py_compile mainLoop.py
# PASS (no output)

grep -n "widget_manager\." mainLoop.py
# 94:  if ctrl_pressed and self.widget_manager.is_menu_open():
# 95:      self.widget_manager.close_context_menu()
# 127:     self.widget_manager.close_context_menu()
# 139:     self.widget_manager.open_context_menu(tile, x, y)
# 164: if self.widget_manager.is_menu_open():
# 165:     self.widget_manager.on_mouse_release(x, y, button, 0)
# 174:     self.widget_manager.on_mouse_scroll(self.input.x, self.input.y, x_offset, y_offset)
# 181:     self.widget_manager.on_mouse_drag(x, y, dx, dy, 0, 0)
```

## Wave 10: _render_widgets Implementation (2026-06-06)

### Decision: Skip widget rendering when ctrl is pressed (tile border mode takes precedence)

- `_render_widgets()` calls `widget_manager.render_all()` only when `ctrl_pressed` is False
- Early return when ctrl is pressed allows tile borders to render without widget overlay
- Widget rendering happens in the 2D overlay phase (after depth-mask, before tileManager)

### Implementation

- `_render_widgets(self)` at line 203:
  ```python
  def _render_widgets(self):
      if self.input.ctrl_pressed:
          return  # Tile border mode; skip widget rendering
      if self.widget_manager:
          self.widget_manager.render_all()
  ```

### Verification

```bash
grep -n _render_widgets mainLoop.py
# 82:rc.render_widgets = self._render_widgets  (callback binding)
# 203:def _render_widgets(self):                 (implementation)

python -m py_compile mainLoop.py
# Syntax OK
```

### Next steps

- Render pipeline now complete: nodes -> widgets -> tileManager -> gui
- Tile borders render when ctrl pressed, widgets render otherwise

## Wave 11: _on_tick DataBus Bridge (2026-06-06)

### Decision: Push simulation state to DataBus and update widgets after each step

- `_on_tick()` now bridges simulation state to widgets via DataBus
- State is pushed only when simulation stepped (inside `if self._simulation is not None` block)
- `widget_manager.update_all()` called after state push to refresh all widgets

### Implementation

- `mainLoop.py:_on_tick()` at line 103-107:
  ```python
  self._simulation.step(frame_time)
  state = self._simulation.get_state()
  if state:
      self.data_bus.push_payload(state)
  self.widget_manager.update_all()
  ```

### Verification

```bash
grep -n push_payload mainLoop.py
# 106:self.data_bus.push_payload(state)

grep -n update_all mainLoop.py
# 107:self.widget_manager.update_all()

python -m py_compile mainLoop.py
# Syntax OK
```

### Next steps

- Simulation state now flows: simulation.step() -> DataBus.push_payload() -> WidgetManager.update_all()
- Widgets can subscribe to DataBus for real-time data updates

## Verification: Import and Syntax Check (2026-06-06)

### Files verified

All 7 modified files passed `python3 -m py_compile` with zero errors:

- `widgets/registry.py` ✓
- `widgets/manager.py` ✓
- `widgets/widget_base.py` ✓
- `widgets/line_plot.py` ✓
- `window/mainWindow.py` ✓
- `settings_gui/guiManager.py` ✓
- `mainLoop.py` ✓

### Import verification

```bash
python -c "from mainLoop import MainLoopHandler; print('OK')"
# OK
```

All imports resolve correctly. No syntax errors detected.
