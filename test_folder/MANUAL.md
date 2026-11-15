# VizCore — test_folder Manual

GUI and widget utilities for building real-time 3D visualization dashboards.

## Modules

| Module | Use Case |
|---|---|
| `settings_gui/` | In-app GUI overlays — popup menus, buttons, sliders, toggles, branches. Built on ModernGL + pyglet. See `settings_gui/MANUAL.md`. |
| `widget_gui.py` → `widget_gui.MANUAL.md` | Self-contained context-menu system for widget right-click menus. No dependency on `settings_gui/`. |
| `widget_base.py` → `widget_base.MANUAL.md` | Widget base class + `DrawingContext` — build tile widgets with a 2D drawing API (rects, text, lines). |
| `tile_management/` → `tile_management/MANUAL.md` | Split/merge/resize window into rectangular tiles. Each tile holds one widget. |
| `render_pipeline.py` → `render_pipeline.MANUAL.md` | Depth-toggle helpers for `render_tiles()` / `render_gui()`. All actual rendering delegates to `GuiRenderer`. |
| `core/` → `core/MANUAL.md` | `DataBus` with ring buffers, `SignalSchema`, `Simulation` thread. |

## Entry Points

| File | What it does |
|---|---|
| `mainLoop.py` | Main application — wires together tile management, widgets, GUI popups, 3D room, model loading |
| `settings_gui/gui_playground.py` | Standalone GUI element test (buttons, sliders, toggles, sub-menus) |
| `simRoom.py` | 3D simulation room viewer (5-face grid, camera switching) |
| `infinite_grid.py` | Infinite LOD grid with XYZ axis arrows |
| `test_lineplot.py` | End-to-end line-chart widget test with signal binding |
| `main.py` | App entry point |

## Coordinate Convention

All GUI coordinates use **bottom-up** (y=0 at screen bottom, y=win_h at top). Mouse input from `moderngl_window` arrives top-down and is converted at the boundary via `self._win_h - y`. Both `GuiRenderer` and `DrawingContext` accept bottom-up coords and pass them directly to `pyglet.text.Label` (which natively uses bottom-up).
