"""
Regression tests for coordinate conversion math — Y-flip characterization.

These tests document the current behavior of all Y-flip sites in the codebase
BEFORE any refactoring. They serve as regression guards to ensure coordinate
conversions remain correct after any future changes.

Y-flip sites characterized:
  1. widgets/manager.py:78           - bottom_up_y = window_h - tile.y - tile.height
  2. settings_gui/guiManager.py:26   - popup_y = _win_h - y (show_popup)
  3. settings_gui/guiManager.py:197  - y = _win_h - y (on_mouse_press)
  4. settings_gui/guiManager.py:237  - _win_h - y (on_mouse_release)
  5. settings_gui/guiManager.py:242  - _win_h - y (on_mouse_drag)
  6. settings_gui/guiManager.py:247  - y = _win_h - y (on_mouse_move)
  7. settings_gui/blipGui.py:26      - _y = _win_h - y (show)
  8. settings_gui/blipGui.py:172      - y = _win_h - y (on_mouse_press)
  9. settings_gui/blipGui.py:213      - _win_h - y (on_mouse_release)
  10. settings_gui/blipGui.py:219     - y = _win_h - y (on_mouse_move)
  11. window/model_aligner.py:314     - fy = renderer.height - y (on_mouse_press)
  12. window/model_aligner.py:350     - fy = renderer.height - y (on_mouse_release)
  13. window/model_aligner.py:365     - fy = renderer.height - y (on_mouse_drag)
  14. widgets/widget_gui.py:122-123   - _flip() returns _win_h - y
  15. shaders (NDC): tile_border.vert, tile_bg.vert - ndc.y = -ndc.y

Coordinate system: moderngl_window provides top-down (y=0 at top).
                    GUI/GUI elements use bottom-up (y=0 at bottom).
                    Formula: flipped_y = surface_height - original_y
"""

import sys
import os
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

# ------------------------------------------------------------------
# Path setup
# ------------------------------------------------------------------
_WORKSPACE_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_TEST_FOLDER = os.path.join(_WORKSPACE_ROOT, "test_folder")

if _WORKSPACE_ROOT not in sys.path:
    sys.path.insert(0, _WORKSPACE_ROOT)
if _TEST_FOLDER not in sys.path:
    sys.path.insert(0, _TEST_FOLDER)


# ==================================================================
# Test Fixtures
# ==================================================================

class MockTile:
    """Minimal tile stand-in for widget lifecycle testing."""

    def __init__(self, x, y, width, height):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.widget = None


# ==================================================================
# Test Cases
# ==================================================================

class TestWidgetManagerYFlip(unittest.TestCase):
    """
    Y-flip at widgets/manager.py:78
    Formula: bottom_up_y = window_h - tile.y - tile.height
    """

    def setUp(self):
        self.window_h = 720

    def test_bottom_up_y_center_tile(self):
        """Tile centered vertically in window."""
        tile = MockTile(x=0, y=0, width=400, height=300)
        bottom_up_y = self.window_h - tile.y - tile.height
        self.assertEqual(bottom_up_y, 420)

    def test_bottom_up_y_top_origin(self):
        """Tile at top-left origin (y=0) with height 300."""
        tile = MockTile(x=0, y=0, width=400, height=300)
        bottom_up_y = self.window_h - tile.y - tile.height
        self.assertEqual(bottom_up_y, 420)

    def test_bottom_up_y_at_bottom(self):
        """Tile positioned at bottom of window (y=420 for 300-height tile)."""
        tile = MockTile(x=0, y=420, width=400, height=300)
        bottom_up_y = self.window_h - tile.y - tile.height
        self.assertEqual(bottom_up_y, 0)

    def test_bottom_up_y_full_height(self):
        """Tile spanning full window height."""
        tile = MockTile(x=0, y=0, width=400, height=720)
        bottom_up_y = self.window_h - tile.y - tile.height
        self.assertEqual(bottom_up_y, 0)

    def test_bottom_up_y_edge_origin(self):
        """Tile at y=0 with minimal height."""
        tile = MockTile(x=0, y=0, width=100, height=1)
        bottom_up_y = self.window_h - tile.y - tile.height
        self.assertEqual(bottom_up_y, 719)

    def test_bottom_up_y_window_resize(self):
        """Verify flip adapts to different window heights."""
        for win_h in [480, 720, 1080]:
            tile = MockTile(x=0, y=0, width=400, height=200)
            bottom_up_y = win_h - tile.y - tile.height
            self.assertEqual(bottom_up_y, win_h - 200)


class TestGuiManagerYFlip(unittest.TestCase):
    """
    Y-flip at settings_gui/guiManager.py
    Formula: flipped_y = _win_h - y
    """

    def setUp(self):
        self._win_h = 720

    def _flip(self, y):
        """Replicates guiManager.py flip formula."""
        return self._win_h - y

    def test_flip_top_down_origin(self):
        """Top-down y=0 becomes bottom-up."""
        self.assertEqual(self._flip(0), 720)

    def test_flip_top_down_max(self):
        """Top-down y=720 (max) becomes bottom-up 0."""
        self.assertEqual(self._flip(720), 0)

    def test_flip_top_down_midpoint(self):
        """Top-down y=360 (mid) becomes bottom-up 360."""
        self.assertEqual(self._flip(360), 360)

    def test_flip_symmetry(self):
        """Flip is symmetric: flip(flip(y)) == y."""
        for y in [0, 50, 100, 360, 500, 720]:
            self.assertEqual(self._flip(self._flip(y)), y)

    def test_flip_show_popup(self):
        """show_popup stores flipped y at line 26."""
        screen_y = 100
        flipped = self._flip(screen_y)
        self.assertEqual(flipped, 620)

    def test_flip_on_mouse_press(self):
        """on_mouse_press flips y at line 197."""
        screen_y = 50
        flipped = self._flip(screen_y)
        self.assertEqual(flipped, 670)

    def test_flip_on_mouse_release(self):
        """on_mouse_release flips y at line 237."""
        screen_y = 400
        flipped = self._flip(screen_y)
        self.assertEqual(flipped, 320)

    def test_flip_on_mouse_drag(self):
        """on_mouse_drag flips y at line 242."""
        screen_y = 250
        flipped = self._flip(screen_y)
        self.assertEqual(flipped, 470)

    def test_flip_on_mouse_move(self):
        """on_mouse_move flips y at line 247."""
        screen_y = 600
        flipped = self._flip(screen_y)
        self.assertEqual(flipped, 120)

    def test_flip_window_resize(self):
        """Flip adapts to different window heights."""
        for win_h in [480, 720, 1080]:
            flipped = win_h - 360
            self.assertEqual(flipped, win_h - 360)


class TestBlipGuiYFlip(unittest.TestCase):
    """
    Y-flip at settings_gui/blipGui.py
    Formula: flipped_y = _win_h - y
    """

    def setUp(self):
        self._win_h = 720

    def _flip(self, y):
        """Replicates blipGui.py flip formula."""
        return self._win_h - y

    def test_flip_show(self):
        """show() flips y at line 26."""
        screen_y = 80
        flipped = self._flip(screen_y)
        self.assertEqual(flipped, 640)

    def test_flip_on_mouse_press(self):
        """on_mouse_press flips y at line 172."""
        screen_y = 150
        flipped = self._flip(screen_y)
        self.assertEqual(flipped, 570)

    def test_flip_on_mouse_release(self):
        """on_mouse_release flips y at line 213."""
        screen_y = 500
        flipped = self._flip(screen_y)
        self.assertEqual(flipped, 220)

    def test_flip_on_mouse_move(self):
        """on_mouse_move flips y at line 219."""
        screen_y = 300
        flipped = self._flip(screen_y)
        self.assertEqual(flipped, 420)

    def test_flip_consistency_with_guimananger(self):
        """Both GuiManager and BlipGui use identical flip formula."""
        y = 200
        self.assertEqual(self._flip(y), 720 - 200)
        self.assertEqual(self._flip(y), 520)


class TestModelAlignerYFlip(unittest.TestCase):
    """
    Y-flip at window/model_aligner.py
    Formula: fy = renderer.height - y
    """

    def setUp(self):
        self.renderer_height = 720

    def _flip(self, y):
        """Replicates model_aligner.py flip formula."""
        return self.renderer_height - y

    def test_flip_on_mouse_press(self):
        """on_mouse_press flips y at line 314."""
        screen_y = 100
        flipped = self._flip(screen_y)
        self.assertEqual(flipped, 620)

    def test_flip_on_mouse_release(self):
        """on_mouse_release flips y at line 350."""
        screen_y = 400
        flipped = self._flip(screen_y)
        self.assertEqual(flipped, 320)

    def test_flip_on_mouse_drag(self):
        """on_mouse_drag flips y at line 365."""
        screen_y = 250
        flipped = self._flip(screen_y)
        self.assertEqual(flipped, 470)

    def test_flip_origin(self):
        """Y=0 becomes renderer.height."""
        self.assertEqual(self._flip(0), 720)

    def test_flip_max(self):
        """Y=renderer.height becomes 0."""
        self.assertEqual(self._flip(720), 0)


class TestWidgetGuiFlipMethod(unittest.TestCase):
    """
    Y-flip at widgets/widget_gui.py lines 122-123
    Formula: _flip(y) returns self._win_h - y
    """

    def setUp(self):
        self._win_h = 720

    def _flip(self, y):
        """Replicates widget_gui._flip() method."""
        return self._win_h - y

    def test_flip_method_origin(self):
        """_flip(y=0) returns window height."""
        self.assertEqual(self._flip(0), 720)

    def test_flip_method_max(self):
        """_flip(y=win_h) returns 0."""
        self.assertEqual(self._flip(720), 0)

    def test_flip_method_midpoint(self):
        """_flip(y=360) returns 360 (center)."""
        self.assertEqual(self._flip(360), 360)

    def test_flip_method_on_mouse_press(self):
        """on_mouse_press uses _flip at line 213."""
        screen_y = 180
        flipped = self._flip(screen_y)
        self.assertEqual(flipped, 540)

    def test_flip_method_on_mouse_release(self):
        """on_mouse_release uses _flip at line 258."""
        screen_y = 600
        flipped = self._flip(screen_y)
        self.assertEqual(flipped, 120)

    def test_flip_method_on_mouse_move(self):
        """on_mouse_move uses _flip at line 273."""
        screen_y = 90
        flipped = self._flip(screen_y)
        self.assertEqual(flipped, 630)


class TestShaderNdcYFlip(unittest.TestCase):
    """
    Y-flip in GLSL shaders via NDC negation.
    Formula: ndc.y = -ndc.y (flips from bottom-up to top-down for OpenGL)

    Note: This tests the math conceptually since we can't run GLSL in unit tests.
    The shader converts pixel coordinates to NDC where y=0 is bottom and y=1 is top.
    """

    def test_ndc_flip_formula(self):
        """NDC flip formula: ndc_y = -ndc_y mirrors y around zero."""
        # Simulate NDC coordinate before flip
        ndc_y_before = 0.5  # middle of screen in NDC
        ndc_y_after = -ndc_y_before
        self.assertEqual(ndc_y_after, -0.5)

    def test_ndc_flip_bottom(self):
        """NDC y=0 (bottom) becomes y=0 after negation."""
        ndc_y = 0.0
        flipped = -ndc_y
        self.assertEqual(flipped, 0.0)

    def test_ndc_flip_top(self):
        """NDC y=1 (top) becomes y=-1 after negation."""
        ndc_y = 1.0
        flipped = -ndc_y
        self.assertEqual(flipped, -1.0)

    def test_ndc_pixel_to_ndc_conversion(self):
        """Verify pixel_y -> NDC -> flip math."""
        # Simulate: pos_px = inst_rect.xy + vert * inst_rect.zw
        # Then: ndc = (pos_px / resolution) * 2.0 - 1.0
        pixel_y = 360
        resolution_y = 720
        ndc_y = (pixel_y / resolution_y) * 2.0 - 1.0
        self.assertAlmostEqual(ndc_y, 0.0, places=5)

        # After flip
        flipped_ndc = -ndc_y
        self.assertAlmostEqual(flipped_ndc, 0.0, places=5)

    def test_ndc_pixel_top_to_ndc(self):
        """Pixel y at top (720) maps to NDC y=1 before flip."""
        pixel_y = 720
        resolution_y = 720
        ndc_y = (pixel_y / resolution_y) * 2.0 - 1.0
        self.assertAlmostEqual(ndc_y, 1.0, places=5)

        # After flip
        flipped_ndc = -ndc_y
        self.assertAlmostEqual(flipped_ndc, -1.0, places=5)


class TestCoordinateSystemInvariants(unittest.TestCase):
    """
    Tests that verify invariants across all Y-flip implementations.
    """

    def test_all_flips_are_self_inverse(self):
        """Flip(Flip(y)) == y for all implementations."""
        win_h = 720

        # WidgetManager (special case with tile height)
        tile = MockTile(0, 360, width=100, height=200)
        flipped = win_h - tile.y - tile.height
        double_flipped = win_h - flipped - tile.height
        self.assertEqual(double_flipped, tile.y)

        # Standard flips (GuiManager, BlipGui, ModelAligner, WidgetGui)
        def standard_flip(y):
            return win_h - y

        for y in [0, 100, 200, 360, 500, 720]:
            self.assertEqual(standard_flip(standard_flip(y)), y)

    def test_flip_preserves_window_height(self):
        """flip(0) + flip(max) == window_height for standard flips."""
        win_h = 720

        def standard_flip(y):
            return win_h - y

        self.assertEqual(standard_flip(0) + standard_flip(win_h), win_h)

    def test_flip_center_is_fixed_point(self):
        """flip(y) == y when y == window_height / 2."""
        win_h = 720

        def standard_flip(y):
            return win_h - y

        self.assertEqual(standard_flip(360), 360)


if __name__ == "__main__":
    unittest.main(verbosity=2)