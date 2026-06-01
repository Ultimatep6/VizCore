# render_pipeline — Frame Pipeline Helpers

Simple depth-test toggle functions for the render loop.

## Files

| File | Purpose |
|---|---|
| `render_pipeline.py` | `render_tiles()` and `render_gui()` — disable/enable `DEPTH_TEST` around a render call |

## Quick Start

```python
from render_pipeline import render_tiles, render_gui

render_tiles(ctx, tile_manager)   # disables depth, renders tiles, re-enables
render_gui(ctx, gui_manager)      # disables depth, renders GUI, re-enables
```

These are thin wrappers — they toggle `DEPTH_TEST` on/off and delegate to the manager's own render method. All actual rendering (geometry + text) is handled by `GuiRenderer` (`settings_gui/guiRenderer.py`) and `DrawingContext` (`widget_base.py`).

## Coordinate System

All GUI coordinates are **bottom-up** (y=0 at bottom). Mouse input from `moderngl_window` arrives top-down and is converted at the boundary.
