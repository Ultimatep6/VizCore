"""
Regression tests for MenuRenderer state machine.

Tests open/close/click/branch/clamp behavior BEFORE refactoring.
These tests characterize current MenuRenderer behavior to serve as
regression guards during the GUI simplification refactoring.

Since we mock DrawingContext, we test only state machine logic:
open/close, mouse event handling, clamping, and submenu placement.
"""

import sys
import os
import unittest
from unittest.mock import MagicMock

# ------------------------------------------------------------------
# Path setup (same pattern as test_widget_integration.py)
# ------------------------------------------------------------------
_WORKSPACE_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_TEST_FOLDER = os.path.join(_WORKSPACE_ROOT, "test_folder")

if _WORKSPACE_ROOT not in sys.path:
    sys.path.insert(0, _WORKSPACE_ROOT)
if _TEST_FOLDER not in sys.path:
    sys.path.insert(0, _TEST_FOLDER)

from widgets.widget_gui import MenuRenderer


class MockDrawingContext:
    """Mock DrawingContext - no real GPU needed for state machine tests."""
    def quad(self, *args, **kwargs): pass
    def outline(self, *args, **kwargs): pass
    def text(self, *args, **kwargs): pass


class TestMenuOpenClose(unittest.TestCase):
    """Test open/close state transitions and position correctness."""

    def setUp(self):
        self.menu = MenuRenderer(window_height=720, window_width=1280)

    def test_menu_starts_invisible(self):
        """Menu is invisible before any open() call."""
        self.assertFalse(self.menu.visible)

    def test_open_sets_visible_true(self):
        """open() sets visible to True."""
        entries = [("Cut", lambda: None)]
        self.menu.open(entries, 100, 100)
        self.assertTrue(self.menu.visible)

    def test_close_sets_visible_false(self):
        """close() sets visible to False."""
        entries = [("Cut", lambda: None)]
        self.menu.open(entries, 100, 100)
        self.menu.close()
        self.assertFalse(self.menu.visible)

    def test_open_positions_item_correctly(self):
        """open() creates _MenuItem at bottom-up coordinates (no flip)."""
        # screen_y=100 is now passed directly as bottom-up y
        # Item height=28, gap=7, so gap_step=35
        entries = [("Cut", lambda: None)]
        self.menu.open(entries, 100, 100)

        self.assertEqual(len(self.menu._top_items), 1)
        item = self.menu._top_items[0]
        self.assertEqual(item.x, 110)  # screen_x + 10
        self.assertEqual(item.y, 100)   # bottom-up y passed directly
        self.assertEqual(item.label, "Cut")
        self.assertFalse(item.is_branch)

    def test_open_positions_multiple_items_vertically(self):
        """open() stacks multiple items vertically (bottom-up)."""
        # ITEM_H=28, ITEM_GAP=7, so gap_step=35
        # In bottom-up, items stack upward (decreasing y):
        # Item 0: y = 100 (screen_y=100)
        # Item 1: y = 65  (100 - 35)
        # Item 2: y = 30  (100 - 70)
        entries = [("Cut", None), ("Copy", None), ("Paste", None)]
        self.menu.open(entries, 100, 100)

        self.assertEqual(len(self.menu._top_items), 3)
        self.assertEqual(self.menu._top_items[0].y, 100)
        self.assertEqual(self.menu._top_items[1].y, 65)
        self.assertEqual(self.menu._top_items[2].y, 30)
        self.assertEqual(self.menu._top_items[0].label, "Cut")
        self.assertEqual(self.menu._top_items[1].label, "Copy")
        self.assertEqual(self.menu._top_items[2].label, "Paste")

    def test_close_clears_all_items(self):
        """close() empties _top_items and _sub_levels."""
        entries = [("Cut", None), ("Copy", None)]
        self.menu.open(entries, 100, 100)
        self.assertEqual(len(self.menu._top_items), 2)
        self.assertEqual(len(self.menu._sub_levels), 0)

        self.menu.close()

        self.assertEqual(len(self.menu._top_items), 0)
        self.assertEqual(len(self.menu._sub_levels), 0)
        self.assertIsNone(self.menu._captured)
        self.assertIsNone(self.menu._sub_direction)


class TestMenuClickBehavior(unittest.TestCase):
    """Test on_mouse_press and on_mouse_release behavior."""

    def setUp(self):
        self.menu = MenuRenderer(window_height=720, window_width=1280)
        self.ui = MockDrawingContext()

    def test_click_on_item_closes_menu_after_callback(self):
        """Click on a button item triggers callback then closes menu."""
        callback_invoked = []

        def my_callback():
            callback_invoked.append(True)

        entries = [("Cut", my_callback)]
        self.menu.open(entries, 100, 100)

        # Press on the item (item at x=110, y=620, w=170, h=28)
        # hit_test uses bottom-up coords
        self.menu.on_mouse_press(150, 100, 1)  # click center of item

        self.assertEqual(len(callback_invoked), 0)  # press doesn't invoke

        self.menu.on_mouse_release(150, 100, 1)  # release

        self.assertEqual(len(callback_invoked), 1)  # callback invoked
        self.assertFalse(self.menu.visible)  # menu closed

    def test_click_on_branch_opens_submenu(self):
        """Click on a branch item (is_branch=True) opens submenu."""
        sub_entries = [("SubItem1", None), ("SubItem2", None)]
        entries = [("Edit", sub_entries)]  # Edit is a branch

        self.menu.open(entries, 100, 100)

        # Press on the branch item
        self.menu.on_mouse_press(150, 100, 1)

        # Branch should have opened submenu
        self.assertEqual(len(self.menu._sub_levels), 1)
        self.assertEqual(self.menu._sub_direction, "right")

        # Release (branch items don't trigger callback on release)
        self.menu.on_mouse_release(150, 100, 1)
        self.assertTrue(self.menu.visible)  # menu stays open for branch

    def test_click_outside_menu_closes_menu(self):
        """Click outside menu bounds closes menu without callback."""
        callback_invoked = []

        def never_called():
            callback_invoked.append(True)

        entries = [("Cut", never_called)]
        self.menu.open(entries, 100, 100)

        # Click far outside menu bounds
        self.menu.on_mouse_press(500, 500, 1)

        self.assertEqual(len(callback_invoked), 0)  # no callback
        self.assertFalse(self.menu.visible)  # menu closed


class TestMenuClamp(unittest.TestCase):
    """Test _clamp() keeps menu within window bounds."""

    def setUp(self):
        self.menu = MenuRenderer(window_height=720, window_width=1280)

    def test_clamp_shifts_menu_up_when_off_bottom(self):
        """When menu extends below window bottom, _clamp shifts it up."""
        # Open menu at bottom of window (screen_y=700)
        # bottom-up y = 720 - 700 = 20
        # Items: y=20, y=-15, y=-50 (below window in bottom-up)
        entries = [("A", None), ("B", None), ("C", None)]
        self.menu.open(entries, 100, 700)  # near bottom of 720px window

        for item in self.menu._top_items:
            self.assertGreaterEqual(item.y, 0)
            self.assertLessEqual(item.y, 720)

    def test_clamp_shifts_menu_left_when_off_right_edge(self):
        """When menu extends beyond right edge, _clamp shifts it left."""
        # Open menu near right edge of 1280px window
        entries = [("Long Option Name That Exceeds Width", None)]
        self.menu.open(entries, 1200, 100)  # near right edge

        # After clamping, all items should be within [0, 1280]
        for item in self.menu._top_items:
            self.assertGreaterEqual(item.x, 0)
            self.assertLessEqual(item.x + item.w, 1280)

    def test_clamp_does_nothing_when_menu_fits(self):
        """When menu fits entirely within bounds, no shift occurs."""
        # Open menu well within bounds
        entries = [("Normal", None)]
        self.menu.open(entries, 400, 360)  # center of 720x1280 window

        item = self.menu._top_items[0]
        # x should be 410 (400 + 10), y should be 360 (flip of 360)
        self.assertEqual(item.x, 410)
        self.assertEqual(item.y, 360)  # _flip(360) = 360


class TestMenuSubmenuPositioning(unittest.TestCase):
    """Test _push_sub_level() submenu positioning logic."""

    def setUp(self):
        self.menu = MenuRenderer(window_height=720, window_width=1280)
        self.ui = MockDrawingContext()

    def test_submenu_opens_to_right_of_branch(self):
        """Submenu appears to the right of parent branch by default."""
        sub_entries = [("Alpha", None), ("Beta", None)]
        entries = [("Folder", sub_entries)]
        self.menu.open(entries, 200, 200)

        # Click on branch to open submenu
        self.menu.on_mouse_press(210, 200, 1)

        self.assertEqual(len(self.menu._sub_levels), 1)
        self.assertEqual(self.menu._sub_direction, "right")

        # Submenu items should be positioned to the right of branch
        branch = self.menu._top_items[0]
        sub_items = self.menu._sub_levels[0]["items"]
        for item in sub_items:
            self.assertGreater(item.x, branch.x)

    def test_submenu_opens_left_when_right_would_overflow(self):
        """Submenu flips to left side when it would overflow right edge."""
        # Open menu close to right edge so submenu would overflow
        sub_entries = [("Long Submenu Item", None)]
        entries = [("Folder", sub_entries)]
        # Position at x where submenu to the right would exceed 1280px
        self.menu.open(entries, 1150, 200)

        # Click on branch
        self.menu.on_mouse_press(1160, 200, 1)

        # Should have flipped to left direction
        self.assertEqual(self.menu._sub_direction, "left")

    def test_submenu_items_maintain_vertical_stack(self):
        """Submenu items are stacked vertically like top-level items."""
        sub_entries = [("SubA", None), ("SubB", None), ("SubC", None)]
        entries = [("Folder", sub_entries)]
        self.menu.open(entries, 200, 200)

        self.menu.on_mouse_press(210, 200, 1)

        sub_items = self.menu._sub_levels[0]["items"]
        self.assertEqual(len(sub_items), 3)

        # Items should be in vertical stack (higher y = higher on screen)
        self.assertGreater(sub_items[0].y, sub_items[1].y)
        self.assertGreater(sub_items[1].y, sub_items[2].y)


class TestMenuStateMachine(unittest.TestCase):
    """Integration tests for full state machine transitions."""

    def setUp(self):
        self.menu = MenuRenderer(window_height=720, window_width=1280)
        self.ui = MockDrawingContext()

    def test_open_close_open_sequence(self):
        """Multiple open/close cycles maintain correct state."""
        entries1 = [("One", None)]
        entries2 = [("First", None), ("Second", None)]

        # First open
        self.menu.open(entries1, 100, 100)
        self.assertTrue(self.menu.visible)
        self.assertEqual(len(self.menu._top_items), 1)

        # Close
        self.menu.close()
        self.assertFalse(self.menu.visible)

        # Open again with different entries
        self.menu.open(entries2, 200, 200)
        self.assertTrue(self.menu.visible)
        self.assertEqual(len(self.menu._top_items), 2)
        self.assertEqual(self.menu._top_items[0].label, "First")
        self.assertEqual(self.menu._top_items[1].label, "Second")

    def test_submenu_nesting_deeper(self):
        """Can open submenu then close it, returning to parent menu."""
        sub_sub_entries = [("Deep Item", None)]
        sub_entries = [("Intermediate", sub_sub_entries)]
        entries = [("Root", sub_entries)]

        self.menu.open(entries, 100, 100)

        # Open first level submenu
        self.menu.on_mouse_press(110, 100, 1)
        self.assertEqual(len(self.menu._sub_levels), 1)
        self.assertTrue(self.menu.visible)

        # Close menu entirely
        self.menu.close()
        self.assertEqual(len(self.menu._sub_levels), 0)
        self.assertFalse(self.menu.visible)


class TestMenuRenderCommands(unittest.TestCase):
    """Test get_render_commands() returns structured draw data."""

    def setUp(self):
        self.menu = MenuRenderer(window_height=720, window_width=1280)

    def test_invisible_returns_empty_list(self):
        """get_render_commands() returns [] when menu is not visible."""
        self.assertEqual(self.menu.get_render_commands(), [])

    def test_open_returns_background_commands(self):
        """Open menu returns background quad and outline commands."""
        entries = [("Cut", lambda: None)]
        self.menu.open(entries, 100, 100)
        commands = self.menu.get_render_commands()
        self.assertTrue(len(commands) > 0)
        self.assertEqual(commands[0]['type'], 'quad')
        self.assertEqual(commands[1]['type'], 'outline')

    def test_item_commands_structure(self):
        """Item commands have correct keys and types."""
        entries = [("Copy", lambda: None)]
        self.menu.open(entries, 100, 100)
        commands = self.menu.get_render_commands()

        item_cmds = [c for c in commands[2:] if c['type'] in ('quad', 'outline', 'text')]
        self.assertTrue(len(item_cmds) >= 3)

        quad_cmds = [c for c in item_cmds if c['type'] == 'quad']
        outline_cmds = [c for c in item_cmds if c['type'] == 'outline']
        text_cmds = [c for c in item_cmds if c['type'] == 'text']

        self.assertTrue(len(quad_cmds) >= 1)
        self.assertTrue(len(outline_cmds) >= 1)
        self.assertTrue(len(text_cmds) >= 1)

        label_cmd = text_cmds[0]
        self.assertEqual(label_cmd['text'], "Copy")
        self.assertEqual(label_cmd['anchor_x'], 'left')
        self.assertEqual(label_cmd['anchor_y'], 'center')

    def test_branch_item_has_arrow_command(self):
        """Branch items include '>' arrow text command."""
        sub_entries = [("SubA", None)]
        entries = [("Folder", sub_entries)]
        self.menu.open(entries, 100, 100)
        commands = self.menu.get_render_commands()

        text_cmds = [c for c in commands if c['type'] == 'text']
        arrow_cmds = [c for c in text_cmds if c['text'] == '>']
        self.assertEqual(len(arrow_cmds), 1)
        self.assertEqual(arrow_cmds[0]['anchor_x'], 'center')
        self.assertEqual(arrow_cmds[0]['anchor_y'], 'center')

    def test_submenu_includes_sub_level_commands(self):
        """Submenu open includes sub-level background and items."""
        sub_entries = [("SubA", None), ("SubB", None)]
        entries = [("Folder", sub_entries)]
        self.menu.open(entries, 100, 100)
        self.menu.on_mouse_press(110, 100, 1)

        commands = self.menu.get_render_commands()

        quad_cmds = [c for c in commands if c['type'] == 'quad']
        outline_cmds = [c for c in commands if c['type'] == 'outline']
        text_cmds = [c for c in commands if c['type'] == 'text']

        self.assertTrue(len(quad_cmds) >= 4)
        self.assertTrue(len(outline_cmds) >= 4)
        self.assertTrue(len(text_cmds) >= 4)

    def test_command_keys(self):
        """All commands have required keys."""
        entries = [("Test", lambda: None)]
        self.menu.open(entries, 100, 100)
        commands = self.menu.get_render_commands()

        for cmd in commands:
            self.assertIn('type', cmd)
            if cmd['type'] in ('quad', 'outline'):
                self.assertIn('x', cmd)
                self.assertIn('y', cmd)
                self.assertIn('w', cmd)
                self.assertIn('h', cmd)
                self.assertIn('color', cmd)
                self.assertIn('alpha', cmd)
            elif cmd['type'] == 'text':
                self.assertIn('x', cmd)
                self.assertIn('y', cmd)
                self.assertIn('text', cmd)
                self.assertIn('color', cmd)
                self.assertIn('scale', cmd)
                self.assertIn('anchor_x', cmd)
                self.assertIn('anchor_y', cmd)


if __name__ == "__main__":
    unittest.main(verbosity=2)