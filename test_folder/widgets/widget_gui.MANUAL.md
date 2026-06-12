# widget_gui — Widget Context Menu System

Self-contained right-click menu renderer for tile widgets. Zero dependencies on `settings_gui/`.

## Files

| File | Purpose |
|---|---|
| `widget_gui.py` | Menu + renderer + item classes in one file |

## Text Rendering

Text is rendered exclusively via `pyglet.text.Label.draw()` — the `DrawingContext.text()` method in `widget_base.py` creates a label and draws it on every frame. This is a stateless zero-allocation approach (the label is created and discarded each frame, no caching).

No `FontAtlas`, `TextAtlas`, or `TextRenderer` classes remain in the project. The old PIL-based rasterisation (which silently failed due to missing imports) has been replaced with direct pyglet rendering.

### Dynamic element sizing

All GUI elements in `settings_gui/elements/` measure text width at draw time via `GuiRenderer.text_width(text, scale)`, which uses `pyglet.text.Label.content_width`. If the measured text is wider than the current element, `self.w` expands so the text always fits.

`_MenuItem` in `widget_gui.py` does the same via `_text_width()`, which also uses `pyglet.text.Label.content_width` (replacing the old `len(text) * 6` heuristic).

## Quick Start

```python
from widget_gui import MenuRenderer

renderer = MenuRenderer(win_h=768)

# In widget get_context_menu():
def get_context_menu(self, local_x, local_y):
    return [
        ("Action 1", lambda: print("do thing")),
        ("Sub Menu", [
            ("Sub 1", lambda: print("sub thing")),
        ]),
    ]

# In right-click handler:
entries = widget.get_context_menu(x - tile.x, y - tile.y)
if entries:
    renderer.open(entries, screen_x, screen_y)

# In render loop:
renderer.draw(ui_context)

# Forward events:
renderer.on_mouse_press(x, y, button)
renderer.on_mouse_move(x, y, dx, dy)
```

## Data Structure

Widgets return a list of `(label, action)` tuples:
- `action` is a **callable** → renders as a button
- `action` is a **list** of more `(label, action)` tuples → renders as a branch with sub-menu

## Branch Sub-Menu Direction

Nested sub-menus maintain a consistent left/right direction across all levels via a `_sub_direction` flag:

- **`None`** (no sub-levels open yet): first sub-menu prefers right. Falls back to left only if right overflows the window edge.
- **`"right"`**: all subsequent sub-menus go right. If a level overflows the right edge, it flips to left and the flag switches to `"left"`.
- **`"left"`**: all subsequent sub-menus go left. If a level would go negative on the left, it flips to right and the flag switches back.

This prevents the zigzag appearance where alternating sub-levels flip sides independently.

The flag resets to `None` when all sub-levels are closed (`close()` or popping the last level).

## Coordinate Convention

Bottom-up (y=0 = bottom). The `DrawingContext` provided as `ui` to `draw()` handles the flip internally.
