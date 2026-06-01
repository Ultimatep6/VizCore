# tile_management — Window Tile Layout

Split a window into rectangular tiles, each containing a widget.

## Files

| File | Purpose |
|---|---|
| `tile.py` | `Tile` (position, size, widget ref) + `TileManager` (layout, split/merge, border rendering) |
| `settings.py` | Constants: max tiles, gaps, border thickness/color/glow |

## Quick Start

```python
from tile_management.tile import TileManager

mgr = TileManager(window)
# (window needs .wnd.width, .wnd.height, .load_program(), .ctx)
```

## TileManager API

| Method | Description |
|---|---|
| `get_tile_index(x, y)` | Find tile at pixel position. Returns index or `None`. |
| `set_focus(index)` | Set focused tile by index. |
| `split_focused_tile(direction)` | Split focused tile `"vertical"` or `"horizontal"`. |
| `can_merge(i, j)` | Check if two tiles can be merged (share full edge). |
| `merge(i, j)` | Merge two tiles into one. Cleans up focus index. |
| `get_border_at(x, y, threshold)` | Detect if cursor is on a tile border. Returns `(type, pos)` or `None`. |
| `resize_border(x, y, dx, dy, threshold)` | Drag a border to resize adjacent tiles. Returns `(dx, dy)` actually moved. |
| `render()` | Draw hovered tile border glow via GPU shader. |

## Tile Object

```python
t = Tile(x, y, width, height)
t.widget = my_widget_instance  # Any object — TileManager doesn't inspect it
```

## Layout Behavior

- Initial layout: 4 tiles (2×2 grid)
- Split: replaces one tile with two along the split axis
- Merge: combines two adjacent tiles that share a full edge
- Border drag: resizes adjacent tiles bidirectionally, clamped to `min_size`

## Coordinate System

Tile positions use **bottom-up** (y=0 at window bottom), matching the GUI rendering convention.
