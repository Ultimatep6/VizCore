"""
Integration test — verify widget lifecycle end-to-end.

Creates and runs a minimal integration test that verifies the full widget
lifecycle: creation, DataBus data flow, update, and removal.

Since we cannot open a real GUI window in a headless environment, this test
uses a headless ModernGL context and focuses on programmatic verification
of the lifecycle.
"""

import sys
import os
import unittest
from types import SimpleNamespace

# ------------------------------------------------------------------
# Path setup
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
from widgets.line_plot import LinePlot
from widgets.registry import default_registry
from examples.exampleSim import ExampleSim


class MockTile:
    """Minimal tile stand-in for widget lifecycle testing."""

    def __init__(self, x, y, width, height):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.widget = None


class TestWidgetLifecycle(unittest.TestCase):
    """End-to-end widget lifecycle integration test."""

    @classmethod
    def setUpClass(cls):
        """Create a single headless ModernGL context shared across tests."""
        cls._headless_ctx = moderngl.create_standalone_context()

    def setUp(self):
        """Fresh DataBus and WidgetManager for each test case."""
        self.data_bus = DataBus()

        # Mock window with real headless context
        self.mock_window = SimpleNamespace(
            ctx=self._headless_ctx,
            wnd=SimpleNamespace(size=(1280, 720), width=1280, height=720),
        )

        self.widget_manager = WidgetManager(self.mock_window, self.data_bus)

    # ------------------------------------------------------------------
    # 1. Creation
    # ------------------------------------------------------------------

    def test_widget_creation(self):
        """Widget can be instantiated and registered in WidgetManager."""
        tile = MockTile(0, 0, 400, 300)
        widget = self.widget_manager.add_widget(tile, "Line Plot")

        self.assertIn((0, 0), self.widget_manager._widgets)
        self.assertIsInstance(widget, LinePlot)
        self.assertEqual(widget.size, (400, 300))

    # ------------------------------------------------------------------
    # 2. DataBus data flow
    # ------------------------------------------------------------------

    def test_databus_receives_simulation_data(self):
        """DataBus receives flattened state from ExampleSim."""
        sim = ExampleSim()
        sim.step(0.1)
        state = sim.get_state()
        self.assertIsNotNone(state)

        self.data_bus.push_payload(state)
        signals = self.data_bus.list_signals()
        self.assertTrue(len(signals) > 0)

        self.assertIn("static_nodes", signals)
        self.assertIn("particles", signals)

    def test_databus_scalar_data_for_lineplot(self):
        """DataBus can receive scalar data suitable for LinePlot."""
        self.data_bus.push_payload({
            "sensors": {
                "imu": {
                    "accel_x": [0.5],
                    "accel_y": [0.3],
                },
                "gps": {
                    "latitude": [42.0],
                },
            },
            "step_target": [1.0],
            "system_response": [0.8],
        })

        signals = self.data_bus.list_signals()
        self.assertIn("sensors.imu.accel_x", signals)
        self.assertIn("step_target", signals)

        latest = self.data_bus.latest("step_target")
        self.assertIsNotNone(latest)
        self.assertAlmostEqual(float(latest.flat[0]), 1.0, places=5)

    # ------------------------------------------------------------------
    # 3. Update
    # ------------------------------------------------------------------

    def test_widget_update_reads_data(self):
        """Widget.update() pulls latest data from DataBus."""
        tile = MockTile(10, 20, 400, 300)
        widget = self.widget_manager.add_widget(tile, "Line Plot")

        # Seed DataBus with scalar data
        self.data_bus.push_payload({
            "step_target": [1.5],
            "system_response": [0.75],
        })

        # Attach signal
        widget.attach_signal("step_target")
        self.assertIn("step_target", widget._bound_signals)
        self.assertIn("step_target", widget._buffers)

        # Update widget
        widget.update()

        # Verify widget read the data
        latest = widget.read("step_target")
        self.assertIsNotNone(latest)
        self.assertAlmostEqual(float(latest.flat[0]), 1.5, places=5)

        # Verify buffer received the value
        buf = widget._buffers["step_target"]
        self.assertEqual(buf._count, 1)
        self.assertAlmostEqual(float(buf._data[-1]), 1.5, places=5)

    def test_widget_update_multiple_ticks(self):
        """Simulate multiple ticks: DataBus receives data and widget updates."""
        tile = MockTile(0, 0, 400, 300)
        widget = self.widget_manager.add_widget(tile, "Line Plot")
        widget.attach_signal("step_target")

        values = [0.0, 0.5, 1.0, 1.5, 2.0]
        for v in values:
            self.data_bus.push_payload({"step_target": [v]})
            widget.update()

        buf = widget._buffers["step_target"]
        self.assertEqual(buf._count, len(values))
        self.assertAlmostEqual(float(buf._data[-1]), 2.0, places=5)

    # ------------------------------------------------------------------
    # 4. Removal
    # ------------------------------------------------------------------

    def test_widget_removal_cleans_up(self):
        """Removing a widget deletes it from WidgetManager."""
        tile = MockTile(5, 5, 400, 300)
        widget = self.widget_manager.add_widget(tile, "Line Plot")
        self.assertIn((5, 5), self.widget_manager._widgets)

        self.widget_manager.destroy_widget(tile)
        self.assertNotIn((5, 5), self.widget_manager._widgets)

    # ------------------------------------------------------------------
    # 5. Full lifecycle (combines all phases)
    # ------------------------------------------------------------------

    def test_full_lifecycle(self):
        """Complete lifecycle: create -> data flow -> update -> remove."""
        # 1. Create
        tile = MockTile(0, 0, 640, 480)
        widget = self.widget_manager.add_widget(tile, "Line Plot")
        self.assertIn((0, 0), self.widget_manager._widgets)
        self.assertIsInstance(widget, LinePlot)

        # 2. Attach simulation and push data
        sim = ExampleSim()
        sim.step(0.1)
        state = sim.get_state()
        self.data_bus.push_payload(state)
        self.assertTrue(len(self.data_bus.list_signals()) > 0)

        # 3. Also push scalar data so LinePlot can consume it
        self.data_bus.push_payload({
            "scalar_signal": [3.14],
        })
        widget.attach_signal("scalar_signal")
        self.assertIn("scalar_signal", widget._bound_signals)

        # 4. Run a few ticks
        for _ in range(5):
            sim.step(0.05)
            self.data_bus.push_payload(sim.get_state())
            self.data_bus.push_payload({"scalar_signal": [3.14 + _ * 0.1]})
            widget.update()

        # Verify widget has buffered data
        buf = widget._buffers["scalar_signal"]
        self.assertEqual(buf._count, 5)

        # 5. Remove widget
        self.widget_manager.destroy_widget(tile)
        self.assertNotIn((0, 0), self.widget_manager._widgets)

    # ------------------------------------------------------------------
    # 6. WidgetManager update_all / render_all smoke tests
    # ------------------------------------------------------------------

    def test_widget_manager_update_all(self):
        """WidgetManager.update_all() calls update() on every widget."""
        tile1 = MockTile(0, 0, 400, 300)
        tile2 = MockTile(400, 0, 400, 300)

        w1 = self.widget_manager.add_widget(tile1, "Line Plot")
        w2 = self.widget_manager.add_widget(tile2, "Line Plot")

        self.data_bus.push_payload({"sig_a": [1.0], "sig_b": [2.0]})
        w1.attach_signal("sig_a")
        w2.attach_signal("sig_b")

        # update_all should not raise
        self.widget_manager.update_all()

        # Both widgets should have read data
        self.assertEqual(w1._buffers["sig_a"]._count, 1)
        self.assertEqual(w2._buffers["sig_b"]._count, 1)

    def test_widget_context_menu(self):
        tile = MockTile(0, 0, 400, 300)
        widget = self.widget_manager.add_widget(tile, "Line Plot")

        self.data_bus.push_payload({
            "sensors": {"imu": {"accel_x": [0.5]}},
            "step_target": [1.0],
        })

        menu = widget.get_context_menu()
        self.assertIsInstance(menu, list)
        self.assertTrue(len(menu) > 0)

        labels = [entry[0] for entry in menu]
        self.assertIn("Attach Signal", labels)

        attach_entry = next(e for e in menu if e[0] == "Attach Signal")
        self.assertIsInstance(attach_entry[1], list)

        def flatten_tree(entries):
            result = []
            for label, action in entries:
                if callable(action):
                    result.append(label)
                elif isinstance(action, list):
                    result.extend(flatten_tree(action))
            return result

        all_labels = flatten_tree(menu)
        self.assertTrue(any("accel_x" in str(l) for l in all_labels))
        self.assertTrue(any("step_target" in str(l) for l in all_labels))


if __name__ == "__main__":
    unittest.main(verbosity=2)
