# widget_base — Widget Framework

Build reusable tile widgets with a high-level 2D drawing API.

## Files

| File | Purpose |
|---|---|
| `widget_base.py` | `Widget` base class + `DrawingContext` (rect, outline, text, line helpers) |

## Quick Start

```python
from widget_base import Widget, DrawingContext

class MyWidget(Widget):
    title = "My Widget"
    required_shape = [(1,)]  # Accepts scalar signals only
    transparent = False

    def setup(self):
        self._value = 0.0

    def update(self):
        val = self.read("sensor.temperature")
        if val is not None:
            self._value = val

    def draw(self, ui: DrawingContext):
        ui.quad(10, 10, self.size[0] - 20, self.size[1] - 20, (0.2, 0.2, 0.3))
        ui.text(f"{self._value:.2f}", 20, self.size[1] - 30, scale=0.8)
```

## Widget Lifecycle

```
TileManager binds widget → setup() called once
                         ↓
                    update()  ← every frame (pull DataBus)
                         ↓
                    draw(ui)  ← every frame (render)
```

## DrawingContext API

| Method | Description |
|---|---|
| `quad(x, y, w, h, color, alpha=1.0)` | Filled rectangle (bottom-left origin) |
| `outline(x, y, w, h, color, alpha=1.0)` | Rectangle outline |
| `h_line(y, x1, x2, color, alpha, thickness)` | Horizontal line |
| `v_line(x, y1, y2, color, alpha, thickness)` | Vertical line |
| `text(str, x, y, color, scale, anchor_x, anchor_y)` | Text via pyglet. Anchors: `"left"`/`"center"`/`"right"`, `"bottom"`/`"center"`/`"top"` |

All coordinates are relative to the widget's tile, bottom-up.

## Widget API

| Method / Property | Description |
|---|---|
| `setup()` | Create components (override) |
| `update()` | Pull data from DataBus (override) |
| `draw(ui)` | Render via DrawingContext (override) |
| `on_mouse_*()` | Input event handlers (optional override) |
| `size` | Tile dimensions `(width, height)` |
| `read(name)` | Latest DataBus signal value |
| `create_line_buffer(max_points)` | GPU ring buffer for chart data |
| `accepts_signal(name)` | Schema-filter check |
| `get_compatible_signals()` | List all schema-matching signals |
| `attach_signal(name)` / `detach_signal(name)` | Bind/unbind signals |
| `get_context_menu()` | Right-click menu entries (override for custom menus) |

## Context Menu Entries

`get_context_menu()` returns `[(label, action), ...]` where `action` is:
- A **callable** — renders as a clickable button
- A **list** of more `(label, action)` tuples — renders as a branch/submenu
