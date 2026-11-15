"""
Regression tests for WidgetManager event forwarding.

Verifies that mouse events (press/release/drag/scroll) are correctly routed
to the appropriate widget based on screen coordinates, and that coordinates
are translated from screen-space to widget-local space.

These tests characterize the CURRENT behavior BEFORE any refactoring.
"""

import sys
import os
import unittest
from unittest.mock import MagicMock, patch, call
from types import SimpleNamespace

# ------------------------------------------------------------------
# Path setup (same pattern as test_widget_integration.py)
# ------------------------------------------------------------------
_WORKSPACE_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_TEST_FOLDER = os.path.join(_WORKSPACE_ROOT, "test_folder")

if _WORKSPACE_ROOT not in sys.path:
    sys.path.insert(0, _WORKSPACE_ROOT)
if _TEST_FOLDER not in sys.path:
    sys.path.insert(0, _TEST_FOLDER)

import moderngl

from core.data_bus import DataBus
from widgets.manager import WidgetManager
from widgets.registry import default_registry


class MockTile:
    """Minimal tile stand-in for widget lifecycle testing."""

    def __init__(self, x, y, width, height):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.widget = None


class MockWidget:
    """Mock widget that tracks received mouse events."""

    def __init__(self, tile_x=0, tile_y=0, tile_w=100, tile_h=100):
        self._tile_x = tile_x
        self._tile_y = tile_y
        self._tile_w = tile_w
        self._tile_h = tile_h
        self._received_events = []

    def on_mouse_press(self, x, y, button):
        self._received_events.append(
            ("press", x, y, button)
        )

    def on_mouse_release(self, x, y, button):
        self._received_events.append(
            ("release", x, y, button)
        )

    def on_mouse_drag(self, x, y, dx, dy, buttons):
        self._received_events.append(
            ("drag", x, y, dx, dy, buttons)
        )

    def on_mouse_scroll(self, x, y, scroll_x, scroll_y):
        self._received_events.append(
            ("scroll", x, y, scroll_x, scroll_y)
        )

    def clear_events(self):
        self._received_events.clear()


class TestMouseEventForwarding(unittest.TestCase):
    """Regression tests for WidgetManager event forwarding."""

    @classmethod
    def setUpClass(cls):
        """Create a single headless ModernGL context shared across tests."""
        cls._headless_ctx = moderngl.create_standalone_context()

    def setUp(self):
        """Fresh WidgetManager and mock widgets for each test."""
        self.data_bus = DataBus()

        # Mock window with headless context
        self.mock_window = SimpleNamespace(
            ctx=self._headless_ctx,
            wnd=SimpleNamespace(size=(1280, 720), width=1280, height=720),
        )

        self.widget_manager = WidgetManager(
            self.mock_window, self.data_bus, registry=default_registry
        )

        # Create mock widgets on specific tiles
        self.widget_a = self._create_mock_widget(tile=MockTile(0, 0, 200, 150))
        self.widget_b = self._create_mock_widget(tile=MockTile(500, 300, 200, 150))
        self.widget_c = self._create_mock_widget(tile=MockTile(0, 500, 200, 150))

    def _create_mock_widget(self, tile):
        """Create a mock widget registered at the given tile position."""
        # We'll patch the registry to return our mock widget class
        widget = MockWidget(tile.x, tile.y, tile.width, tile.height)
        # Manually register in WidgetManager's _widgets dict
        key = (tile.x, tile.y)
        self.widget_manager._widgets[key] = widget
        return widget

    # ==================================================================
    # Test: on_mouse_press forwards to correct widget
    # ==================================================================

    def test_press_forwards_to_widget_inside(self):
        """Click inside widget A (at 0,0) should forward to widget_a."""
        # Click at center of widget_a
        self.widget_manager.on_mouse_press(100, 75, button=1)

        self.assertEqual(len(self.widget_a._received_events), 1)
        event = self.widget_a._received_events[0]
        self.assertEqual(event[0], "press")
        # Coordinates should be translated to widget-local
        self.assertEqual(event[1], 100)  # local x
        self.assertEqual(event[2], 75)   # local y
        self.assertEqual(event[3], 1)     # button

    def test_press_forwards_to_correct_widget_when_multiple(self):
        """Click should forward to the correct widget among multiple."""
        # Click at center of widget_b (tile at 500, 300)
        self.widget_manager.on_mouse_press(600, 375, button=1)

        self.assertEqual(len(self.widget_b._received_events), 1)
        self.assertEqual(len(self.widget_a._received_events), 0)
        self.assertEqual(len(self.widget_c._received_events), 0)

        # Verify coordinates translated correctly
        event = self.widget_b._received_events[0]
        self.assertEqual(event[1], 100)  # 600 - 500 = 100 (local x)
        self.assertEqual(event[2], 75)   # 375 - 300 = 75 (local y)

    def test_press_no_forward_outside_all_widgets(self):
        """Click outside all widgets should not forward to any widget."""
        # Click in empty space (250, 250) - between widget_a and widget_b
        self.widget_manager.on_mouse_press(250, 250, button=1)

        self.assertEqual(len(self.widget_a._received_events), 0)
        self.assertEqual(len(self.widget_b._received_events), 0)
        self.assertEqual(len(self.widget_c._received_events), 0)

    def test_press_on_widget_border(self):
        """Click on widget border should still forward to that widget."""
        # Click on left edge of widget_a (x=0, y=75)
        self.widget_manager.on_mouse_press(0, 75, button=1)
        self.assertEqual(len(self.widget_a._received_events), 1)

        # Click on right edge of widget_a (x=200, y=75)
        self.widget_manager.on_mouse_press(200, 75, button=1)
        self.assertEqual(len(self.widget_a._received_events), 2)

        # Click on bottom edge (x=100, y=0)
        self.widget_manager.on_mouse_press(100, 0, button=1)
        self.assertEqual(len(self.widget_a._received_events), 3)

    def test_press_outside_bottom_boundary(self):
        """Click below widget's bottom edge should not forward."""
        # widget_a spans y=0 to y=150 (tile_y + tile_h)
        # Click at y=-1 (just below)
        self.widget_manager.on_mouse_press(100, -1, button=1)
        self.assertEqual(len(self.widget_a._received_events), 0)

    def test_press_outside_right_boundary(self):
        """Click to the right of widget should not forward."""
        # widget_a spans x=0 to x=200
        # Click at x=201
        self.widget_manager.on_mouse_press(201, 75, button=1)
        self.assertEqual(len(self.widget_a._received_events), 0)

    # ==================================================================
    # Test: on_mouse_release forwards correctly
    # ==================================================================

    def test_release_forwards_to_widget_inside(self):
        """Release inside widget should forward to that widget."""
        self.widget_manager.on_mouse_release(100, 75, button=1)

        self.assertEqual(len(self.widget_a._received_events), 1)
        event = self.widget_a._received_events[0]
        self.assertEqual(event[0], "release")
        self.assertEqual(event[1], 100)  # local x
        self.assertEqual(event[2], 75)   # local y

    def test_release_no_forward_outside(self):
        """Release outside all widgets should not forward."""
        self.widget_manager.on_mouse_release(250, 250, button=1)

        self.assertEqual(len(self.widget_a._received_events), 0)
        self.assertEqual(len(self.widget_b._received_events), 0)

    # ==================================================================
    # Test: on_mouse_drag forwards correctly
    # ==================================================================

    def test_drag_forwards_to_widget_inside(self):
        """Drag inside widget should forward to that widget."""
        self.widget_manager.on_mouse_drag(
            100, 75, dx=10, dy=5, buttons=1
        )

        self.assertEqual(len(self.widget_a._received_events), 1)
        event = self.widget_a._received_events[0]
        self.assertEqual(event[0], "drag")
        self.assertEqual(event[1], 100)  # local x
        self.assertEqual(event[2], 75)   # local y
        self.assertEqual(event[3], 10)    # dx
        self.assertEqual(event[4], 5)     # dy

    def test_drag_no_forward_outside(self):
        """Drag outside all widgets should not forward."""
        self.widget_manager.on_mouse_drag(
            250, 250, dx=10, dy=5, buttons=1
        )

        self.assertEqual(len(self.widget_a._received_events), 0)
        self.assertEqual(len(self.widget_b._received_events), 0)

    # ==================================================================
    # Test: on_mouse_scroll forwards correctly
    # ==================================================================

    def test_scroll_forwards_to_widget_inside(self):
        """Scroll inside widget should forward to that widget."""
        self.widget_manager.on_mouse_scroll(100, 75, scroll_x=0, scroll_y=1)

        self.assertEqual(len(self.widget_a._received_events), 1)
        event = self.widget_a._received_events[0]
        self.assertEqual(event[0], "scroll")
        self.assertEqual(event[1], 100)  # local x
        self.assertEqual(event[2], 75)   # local y
        self.assertEqual(event[3], 0)    # scroll_x
        self.assertEqual(event[4], 1)    # scroll_y

    def test_scroll_no_forward_outside(self):
        """Scroll outside all widgets should not forward."""
        self.widget_manager.on_mouse_scroll(250, 250, scroll_x=0, scroll_y=1)

        self.assertEqual(len(self.widget_a._received_events), 0)
        self.assertEqual(len(self.widget_b._received_events), 0)

    # ==================================================================
    # Test: Coordinate translation
    # ==================================================================

    def test_coordinate_translation_preserves_offset(self):
        """Widget should receive screen-to-local coordinate translation."""
        # widget_b is at tile (500, 300) with size (200, 150)
        # Screen click at (550, 350) should become local (50, 50)

        self.widget_manager.on_mouse_press(550, 350, button=1)

        self.assertEqual(len(self.widget_b._received_events), 1)
        event = self.widget_b._received_events[0]
        # local x = 550 - 500 = 50
        self.assertEqual(event[1], 50)
        # local y = 350 - 300 = 50
        self.assertEqual(event[2], 50)

    def test_coordinate_translation_corner_cases(self):
        """Test translation at widget corners."""
        # widget_c at (0, 500) size (200, 150), spans x=[0,200], y=[500,650]
        # Top-left corner: (0, 500) -> local (0, 0)
        self.widget_manager.on_mouse_press(0, 500, button=1)
        self.assertEqual(len(self.widget_c._received_events), 1)
        self.assertEqual(self.widget_c._received_events[0][1], 0)  # local x
        self.assertEqual(self.widget_c._received_events[0][2], 0)  # local y

    # ==================================================================
    # Test: Menu priority (ctrl-mode routing is handled in mainLoop,
    # but WidgetManager handles menu visibility internally)
    # ==================================================================

    def test_menu_visible_blocks_widget_events(self):
        """When menu is visible, events go to menu, not widget."""
        # Make menu visible
        self.widget_manager._menu_renderer.visible = True

        # Mock the menu's on_mouse_press
        with unittest.mock.patch.object(
            self.widget_manager._menu_renderer, "on_mouse_press"
        ) as mock_menu_press:
            # Click on widget_a's area
            self.widget_manager.on_mouse_press(100, 75, button=1)

            # Menu should have received the event
            mock_menu_press.assert_called_once_with(100, 75, 1)
            # Widget should NOT have received it
            self.assertEqual(len(self.widget_a._received_events), 0)

    def test_menu_hidden_allows_widget_events(self):
        """When menu is not visible, events go to widget."""
        # Ensure menu is NOT visible (default)
        self.widget_manager._menu_renderer.visible = False

        # Click on widget_a
        self.widget_manager.on_mouse_press(100, 75, button=1)

        # Widget should have received the event
        self.assertEqual(len(self.widget_a._received_events), 1)
        # Menu should NOT have received (no mock needed since it won't be called)

    # ==================================================================
    # Test: Multiple widgets - verify correct routing
    # ==================================================================

    def test_rapid_clicks_route_correctly(self):
        """Multiple rapid clicks should route to correct widgets each time."""
        clicks = [
            (100, 75, self.widget_a),   # widget_a
            (600, 375, self.widget_b),  # widget_b
            (100, 575, self.widget_c),  # widget_c
            (100, 75, self.widget_a),   # back to widget_a
        ]

        for x, y, expected_widget in clicks:
            self.widget_manager.on_mouse_press(x, y, button=1)
            self.assertEqual(len(expected_widget._received_events), 1)
            # Clear for next iteration
            for w in [self.widget_a, self.widget_b, self.widget_c]:
                w.clear_events()


class TestCtrlModeRouting(unittest.TestCase):
    """
    Test ctrl-mode routing behavior.

    Note: Ctrl-mode routing is primarily handled in mainLoop.py, which
    decides whether to call WidgetManager or not based on ctrl state.
    These tests verify the WidgetManager behavior when called.
    """

    @classmethod
    def setUpClass(cls):
        cls._headless_ctx = moderngl.create_standalone_context()

    def setUp(self):
        self.data_bus = DataBus()
        self.mock_window = SimpleNamespace(
            ctx=self._headless_ctx,
            wnd=SimpleNamespace(size=(1280, 720), width=1280, height=720),
        )
        self.widget_manager = WidgetManager(
            self.mock_window, self.data_bus, registry=default_registry
        )

        # Create mock widget
        self.mock_widget = MockWidget(tile_x=100, tile_y=100, tile_w=200, tile_h=150)
        self.widget_manager._widgets[(100, 100)] = self.mock_widget

    def test_scroll_blocked_when_menu_visible(self):
        """Scroll should not forward to widget when menu is visible."""
        self.widget_manager._menu_renderer.visible = True

        self.widget_manager.on_mouse_scroll(150, 150, scroll_x=0, scroll_y=1)

        # Widget should NOT have received the event
        self.assertEqual(len(self.mock_widget._received_events), 0)

    def test_drag_blocked_when_menu_visible(self):
        """Drag should not forward to widget when menu is visible."""
        self.widget_manager._menu_renderer.visible = True

        self.widget_manager.on_mouse_drag(150, 150, dx=5, dy=5, buttons=1)

        # Widget should NOT have received the event
        self.assertEqual(len(self.mock_widget._received_events), 0)

    def test_press_routes_to_menu_when_visible(self):
        """Press should route to menu when visible."""
        self.widget_manager._menu_renderer.visible = True

        with unittest.mock.patch.object(
            self.widget_manager._menu_renderer, "on_mouse_press"
        ) as mock:
            self.widget_manager.on_mouse_press(150, 150, button=1)
            mock.assert_called_once_with(150, 150, 1)


class TestCoordinateTranslation(unittest.TestCase):
    """Dedicated tests for screen-to-widget coordinate translation."""

    @classmethod
    def setUpClass(cls):
        cls._headless_ctx = moderngl.create_standalone_context()

    def setUp(self):
        self.data_bus = DataBus()
        self.mock_window = SimpleNamespace(
            ctx=self._headless_ctx,
            wnd=SimpleNamespace(size=(1280, 720), width=1280, height=720),
        )
        self.widget_manager = WidgetManager(
            self.mock_window, self.data_bus, registry=default_registry
        )

    def test_translation_all_four_events(self):
        """Verify translation works for all mouse event types."""
        # Widget at (100, 100) with size (200, 150)
        widget = MockWidget(tile_x=100, tile_y=100, tile_w=200, tile_h=150)
        self.widget_manager._widgets[(100, 100)] = widget

        screen_x, screen_y = 175, 125  # center-ish of widget
        local_x, local_y = screen_x - 100, screen_y - 100  # 75, 25

        # Test all event types
        self.widget_manager.on_mouse_press(screen_x, screen_y, button=1)
        self.assertEqual(widget._received_events[-1][1], local_x)
        self.assertEqual(widget._received_events[-1][2], local_y)

        self.widget_manager.on_mouse_release(screen_x, screen_y, button=1)
        self.assertEqual(widget._received_events[-1][1], local_x)
        self.assertEqual(widget._received_events[-1][2], local_y)

        self.widget_manager.on_mouse_drag(screen_x, screen_y, dx=1, dy=1, buttons=1)
        self.assertEqual(widget._received_events[-1][1], local_x)
        self.assertEqual(widget._received_events[-1][2], local_y)

        self.widget_manager.on_mouse_scroll(screen_x, screen_y, scroll_x=0, scroll_y=1)
        self.assertEqual(widget._received_events[-1][1], local_x)
        self.assertEqual(widget._received_events[-1][2], local_y)


if __name__ == "__main__":
    unittest.main(verbosity=2)