"""
Regression tests for TileManager geometry math (bottom-up coordinate system).

These tests characterize the current behavior AFTER the coordinate flip to
bottom-up (y=0 at bottom of window).

Test framework: unittest (stdlib)
Window size: 1280 x 720
DASHBOARD_CENTER_GAP_X = 200 / DASHBOARD_CENTER_GAP_Y = 200
TILE_MARGIN_X = 10 / TILE_MARGIN_Y = 10

Ground truth (1280x720, gap=200):
  x = [0, 740], y = [0, 460] (top-down)
  Bottom-up y = [720-0-260, 720-460-260] = [460, 0]
  4 tiles: (0,460), (0,0), (740,460), (740,0) in bottom-up
"""

import sys
import os
import unittest
from types import SimpleNamespace

_WORKSPACE_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_TEST_FOLDER = os.path.join(_WORKSPACE_ROOT, "test_folder")

if _WORKSPACE_ROOT not in sys.path:
    sys.path.insert(0, _WORKSPACE_ROOT)
if _TEST_FOLDER not in sys.path:
    sys.path.insert(0, _TEST_FOLDER)

import moderngl

from tile_management.tile import TileManager, Tile

_VERT = "#version 330\nin vec3 position;\nvoid main() { gl_Position = vec4(position, 1.0); }"
_FRAG = "#version 330\nout vec4 color;\nvoid main() { color = vec4(1.0); }"


class MockWindow:
    def __init__(self, width=1280, height=720):
        self._ctx = moderngl.create_standalone_context()
        self.ctx = self._ctx
        self.wnd = SimpleNamespace(width=width, height=height, size=(width, height))

    def load_program(self, **kw):
        return self._ctx.program(vertex_shader=_VERT, fragment_shader=_FRAG)


def make_tm(width=1280, height=720):
    return TileManager(MockWindow(width, height))


# ==================================================================
# 1. _init_tiles
# ==================================================================

class TestInitTiles(unittest.TestCase):
    def test_tile_count_and_focus(self):
        tm = make_tm(1280, 720)
        self.assertEqual(len(tm.tiles), 4)
        self.assertEqual(tm.focus_index, 0)

    def test_tile_dimensions(self):
        tm = make_tm(1280, 720)
        for tile in tm.tiles:
            self.assertEqual(tile.width, 540)
            self.assertEqual(tile.height, 260)

    def test_tile_positions_2x2_grid(self):
        tm = make_tm(1280, 720)
        self.assertEqual(tm.tiles[0].x, 0)
        self.assertEqual(tm.tiles[0].y, 460)
        self.assertEqual(tm.tiles[1].x, 0)
        self.assertEqual(tm.tiles[1].y, 0)
        self.assertEqual(tm.tiles[2].x, 740)
        self.assertEqual(tm.tiles[2].y, 460)
        self.assertEqual(tm.tiles[3].x, 740)
        self.assertEqual(tm.tiles[3].y, 0)

    def test_tile_y_bottom_up(self):
        tm = make_tm(1280, 720)
        for tile in tm.tiles:
            self.assertIn(tile.y, (0, 460))


# ==================================================================
# 2. split_focused_tile
# ==================================================================

class TestSplitFocusedTile(unittest.TestCase):
    def test_vertical_split_count(self):
        tm = make_tm(1280, 720)
        tm.split_focused_tile(direction="vertical")
        self.assertEqual(len(tm.tiles), 5)

    def test_vertical_split_dimensions(self):
        tm = make_tm(1280, 720)
        tm.split_focused_tile(direction="vertical")
        t1, t2 = tm.tiles[0], tm.tiles[1]
        self.assertEqual(t1.width, 265)
        self.assertEqual(t1.height, 260)
        self.assertEqual(t2.width, 265)
        self.assertEqual(t2.height, 260)

    def test_vertical_split_x_positions(self):
        tm = make_tm(1280, 720)
        tm.split_focused_tile(direction="vertical")
        t1, t2 = tm.tiles[0], tm.tiles[1]
        self.assertEqual(t1.x, 0)
        self.assertEqual(t2.x, 275)

    def test_horizontal_split_count(self):
        tm = make_tm(1280, 720)
        tm.split_focused_tile(direction="horizontal")
        self.assertEqual(len(tm.tiles), 5)

    def test_horizontal_split_dimensions(self):
        tm = make_tm(1280, 720)
        tm.split_focused_tile(direction="horizontal")
        t1, t2 = tm.tiles[0], tm.tiles[1]
        self.assertEqual(t1.width, 540)
        self.assertEqual(t1.height, 125)
        self.assertEqual(t2.width, 540)
        self.assertEqual(t2.height, 125)

    def test_horizontal_split_y_positions(self):
        tm = make_tm(1280, 720)
        tm.split_focused_tile(direction="horizontal")
        t1, t2 = tm.tiles[0], tm.tiles[1]
        self.assertEqual(t1.y, 460)
        self.assertEqual(t2.y, 595)


# ==================================================================
# 3. merge
# ==================================================================

class TestMerge(unittest.TestCase):
    def test_merge_horizontal_split_tiles(self):
        tm = make_tm(1280, 720)
        tm.split_focused_tile(direction="vertical")
        result = tm.merge(0, 1)
        self.assertTrue(result)
        self.assertEqual(len(tm.tiles), 4)
        merged = tm.tiles[0]
        self.assertEqual(merged.width, 540)
        self.assertEqual(merged.height, 260)
        self.assertEqual(merged.x, 0)
        self.assertEqual(merged.y, 460)

    def test_merge_vertical_split_tiles(self):
        tm = make_tm(1280, 720)
        tm.split_focused_tile(direction="horizontal")
        result = tm.merge(0, 1)
        self.assertTrue(result)
        self.assertEqual(len(tm.tiles), 4)
        merged = tm.tiles[0]
        self.assertEqual(merged.width, 540)
        self.assertEqual(merged.height, 260)
        self.assertEqual(merged.x, 0)
        self.assertEqual(merged.y, 460)

    def test_merge_non_adjacent_returns_false(self):
        tm = make_tm(1280, 720)
        self.assertFalse(tm.merge(0, 1))


# ==================================================================
# 4. resize_border
# ==================================================================

class TestResizeBorder(unittest.TestCase):
    def test_vertical_resize_leftward(self):
        tm = make_tm(1280, 720)
        tm.split_focused_tile(direction="vertical")
        t1, t2 = tm.tiles[0], tm.tiles[1]
        border_x = t1.x + t1.width
        dx, dy = tm.resize_border(border_x, 500, dx=-50, dy=0)
        self.assertEqual(dx, -50)
        self.assertEqual(t1.width, 215)
        self.assertEqual(t2.x, 225)
        self.assertEqual(t2.width, 315)

    def test_vertical_resize_rightward(self):
        tm = make_tm(1280, 720)
        tm.split_focused_tile(direction="vertical")
        t1, t2 = tm.tiles[0], tm.tiles[1]
        border_x = t1.x + t1.width
        dx, dy = tm.resize_border(border_x, 500, dx=+50, dy=0)
        self.assertEqual(dx, 50)
        self.assertEqual(t1.width, 315)
        self.assertEqual(t2.x, 325)
        self.assertEqual(t2.width, 215)

    def test_horizontal_resize_upward(self):
        tm = make_tm(1280, 720)
        tm.split_focused_tile(direction="horizontal")
        t1, t2 = tm.tiles[0], tm.tiles[1]
        border_y = t1.y + t1.height
        dx, dy = tm.resize_border(300, border_y, dx=0, dy=-30)
        self.assertEqual(dy, -30)
        self.assertEqual(t1.height, 95)
        self.assertEqual(t2.y, 565)
        self.assertEqual(t2.height, 155)

    def test_resize_clamped_by_minimum(self):
        tm = make_tm(1280, 720)
        tm.split_focused_tile(direction="vertical")
        t1, t2 = tm.tiles[0], tm.tiles[1]
        border_x = t1.x + t1.width
        dx, dy = tm.resize_border(border_x, 100, dx=-500, dy=0)
        self.assertGreaterEqual(t1.width, 20)
        self.assertGreaterEqual(t2.width, 20)


# ==================================================================
# 5. get_border_at
# ==================================================================

class TestGetBorderAt(unittest.TestCase):
    def test_detects_left_border_of_right_column(self):
        result = make_tm().get_border_at(740, 100)
        if result is None:
            self.fail("Expected border at x=740")
        self.assertEqual(result[0], "vertical")
        self.assertEqual(result[1], 740)

    def test_detects_right_border_of_left_column(self):
        result = make_tm().get_border_at(540, 100)
        if result is None:
            self.fail("Expected border at x=540")
        self.assertEqual(result[0], "vertical")
        self.assertEqual(result[1], 540)

    def test_ignores_x0_window_edge(self):
        self.assertIsNone(make_tm().get_border_at(0, 100))

    def test_ignores_x1280_window_edge(self):
        self.assertIsNone(make_tm().get_border_at(1280, 100))

    def test_ignores_y0_window_edge(self):
        self.assertIsNone(make_tm().get_border_at(300, 0))

    def test_detects_horizontal_border_at_tile_bottom(self):
        result = make_tm().get_border_at(300, 260)
        if result is None:
            self.fail("Expected border at y=260")
        self.assertEqual(result[0], "horizontal")
        self.assertEqual(result[1], 260)

    def test_detects_horizontal_border_at_second_row(self):
        result = make_tm().get_border_at(300, 460)
        if result is None:
            self.fail("Expected border at y=460")
        self.assertEqual(result[0], "horizontal")
        self.assertEqual(result[1], 460)

    def test_returns_none_for_interior_point(self):
        self.assertIsNone(make_tm().get_border_at(300, 130))

    def test_detects_horizontal_border_between_split_halves(self):
        tm = make_tm(1280, 720)
        tm.split_focused_tile(direction="horizontal")
        result = tm.get_border_at(300, 585)
        if result is None:
            self.fail("Expected border at y=585 between split halves")
        self.assertEqual(result[0], "horizontal")
        self.assertEqual(result[1], 585)


# ==================================================================
# 6. get_tile_index
# ==================================================================

class TestGetTileIndex(unittest.TestCase):
    def test_finds_tile_0_at_origin(self):
        self.assertEqual(make_tm().get_tile_index(0, 720), 0)

    def test_finds_tile_0_at_center(self):
        self.assertEqual(make_tm().get_tile_index(200, 620), 0)

    def test_finds_tile_2_on_right_side(self):
        self.assertEqual(make_tm().get_tile_index(1000, 620), 2)

    def test_finds_tile_3_bottom_right(self):
        self.assertEqual(make_tm().get_tile_index(900, 220), 3)

    def test_returns_none_outside_all_tiles(self):
        self.assertIsNone(make_tm().get_tile_index(-10, 100))

    def test_tile_index_after_vertical_split(self):
        tm = make_tm(1280, 720)
        tm.split_focused_tile(direction="vertical")
        self.assertEqual(tm.get_tile_index(150, 500), 0)
        self.assertEqual(tm.get_tile_index(400, 500), 1)
        self.assertEqual(tm.get_tile_index(900, 100), 4)

    def test_tile_index_after_horizontal_split(self):
        tm = make_tm(1280, 720)
        tm.split_focused_tile(direction="horizontal")
        self.assertEqual(tm.get_tile_index(300, 500), 0)
        self.assertEqual(tm.get_tile_index(300, 650), 1)


# ==================================================================
# 7. can_merge
# ==================================================================

class TestCanMerge(unittest.TestCase):
    def test_adjacent_after_vertical_split(self):
        tm = make_tm(1280, 720)
        tm.split_focused_tile(direction="vertical")
        self.assertTrue(tm.can_merge(0, 1))

    def test_adjacent_after_horizontal_split(self):
        tm = make_tm(1280, 720)
        tm.split_focused_tile(direction="horizontal")
        self.assertTrue(tm.can_merge(0, 1))

    def test_non_adjacent_tiles(self):
        tm = make_tm(1280, 720)
        self.assertFalse(tm.can_merge(0, 1))
        self.assertFalse(tm.can_merge(1, 2))


# ==================================================================
# 8. Tile __repr__
# ==================================================================

class TestTileRepr(unittest.TestCase):
    def test_tile_repr_contains_geometry(self):
        tile = Tile(10, 20, 300, 200)
        r = repr(tile)
        self.assertIn("10", r)
        self.assertIn("20", r)
        self.assertIn("300", r)
        self.assertIn("200", r)


if __name__ == "__main__":
    unittest.main(verbosity=2)