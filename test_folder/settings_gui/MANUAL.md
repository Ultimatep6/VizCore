# settings_gui — GUI Overlay System

Popup menus and UI elements for in-app controls.

## Files

| File | Purpose |
|---|---|
| `guiRenderer.py` | Universal renderer: GPU quads/outlines + `pyglet.text.Label` text via `renderer.text()` + `measure_text()` helper |
| `guiManager.py` | Right-click context menus for tiles (add/remove widgets, signal lists) |
| `blipGui.py` | Popup for 3D model blip nodes (load/edit/remove models) |
| `guiElement.py` | Abstract base: `hit_test()`, resize grip |
| `elements/button.py` | Clickable button (normal/hover/press colors) |
| `elements/toggle.py` | On/off toggle with label |
| `elements/slider.py` | Draggable slider with configurable range |
| `elements/branch.py` | Sub-menu pivot (opens child menu on click) |

## Quick Start

```python
from guiRenderer import GuiRenderer
from guiManager import GuiManager
from elements import Button, Toggle, Slider, Branch

mgr = GuiManager(window)

# Right-click at screen (x, y):
mgr.show_popup(x, y, tile=some_tile)

# In render loop:
mgr.render()

# Forward mouse events:
mgr.on_mouse_press(x, y, button)
mgr.on_mouse_release(x, y, button)
mgr.on_mouse_move(x, y, dx, dy)
```

## Creating Custom Elements

Subclass `GUIElement` and implement `draw(renderer)`. Use `renderer.text()` — no need to create `pyglet.text.Label` yourself:

```python
class MyElement(GUIElement):
    def draw(self, renderer):
        renderer.quad(self.x, self.y, self.w, self.h, color)
        renderer.outline(self.x, self.y, self.w, self.h, (0.5, 0.5, 0.5))
        renderer.text("label", self.x + self.w // 2, self.y + self.h // 2,
                      anchor_x="center", anchor_y="center")
```

## Auto-Sizing

Built-in elements (`Button`, `Branch`, `Toggle`, `Slider`) auto-expand their width at construction time to fit their label text. The `measure_text()` helper in `guiRenderer.py` measures text width via `pyglet.text.Label.content_width`.

| Element | Padding | Notes |
|---|---|---|
| Button | `text + 20` | Centered, 10px each side |
| Branch | `text + 24` | Centered label + `">"` indicator |
| Toggle | `text + 60` | Left label + gap + centered state text + right area |
| Slider | `text + 20` | Measured from widest value format `f"{label}: {max(abs(min), abs(max)):.1f}"` |

For custom elements, call `measure_text()` in your constructor:

```python
from guiRenderer import measure_text

class MyElement(GUIElement):
    def __init__(self, x, y, w, h, label):
        tw = measure_text(label) + 20
        if tw > w:
            w = tw
        super().__init__(x, y, w, h)
```

## Coordinate System

All positions are **bottom-up** (y=0 = bottom of window). Mouse input from moderngl_window is flipped at the input boundary — you do not need to flip coordinates yourself.

## GuiRenderer API

| Method | Description |
|---|---|
| `quad(x, y, w, h, color, alpha=1.0)` | Filled rectangle |
| `outline(x, y, w, h, color, alpha=1.0)` | Rectangle outline (LINE_LOOP) |
| `text(str, x, y, color, scale, anchor_x, anchor_y)` | Text via pyglet.text.Label (supports `"left"`, `"center"`, `"right"`, `"bottom"`, `"top"` anchors) |
| `measure_text(str, font_size=10)` | Returns pixel width (uses `pyglet.text.Label.content_width`) |

## GuiManager Flow

1. Right-click → `show_popup(x, y, tile)`
2. Popup elements built in `_build_tile_popup()`
3. Clicking a `Branch` opens sub-level via `_push_sub_level()`
4. Clicking outside closes popup

## BlipGui Flow

1. `show(x, y, node_name, has_model, repo_entries)`
2. Renders name label + action buttons (Print, Edit, Remove, Load Model)
3. Same event handling pattern as GuiManager
