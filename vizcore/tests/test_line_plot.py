import unittest
from unittest.mock import MagicMock
import numpy as np
import moderngl

from vizcore.widget.linePlot import LinePlot
from vizcore.bus.data_bus import DataBus

class TestLinePlot(unittest.TestCase):
    """Test suite for the LinePlot widget."""

    def setUp(self):
        """Set up test fixtures."""
        self.plot = LinePlot(channels=2)
        
        # Mock DataBus
        self.data_bus = MagicMock(spec=DataBus)
        
        # Mock Camera
        self.camera = MagicMock()
        self.camera.width = 800
        self.camera.height = 600
        self.plot.bind_camera(self.camera)
        
        # Mock Renderer & Context
        self.renderer = MagicMock()
        self.renderer.ctx = MagicMock()
        self.renderer.text_renderer = MagicMock()
        
        # Mock Shader Manager
        self.shader_manager = MagicMock()
        self.renderer.shader_manager = self.shader_manager

    def test_initialization(self):
        """Test that the LinePlot initializes with correct defaults."""
        self.assertEqual(self.plot.channels, 2)
        self.assertEqual(self.plot.points_per_channel, 1000)
        self.assertEqual(self.plot.signal_names, [])
        self.assertIsNone(self.plot._renderer)

    def test_accepts_signal(self):
        """Test that LinePlot only accepts 1D signals."""
        # Setup mock valid 1D signal
        self.data_bus.latest.return_value = np.array([5.0])
        self.assertTrue(self.plot.accepts_signal(self.data_bus, "valid_signal"))
        
        # Setup mock invalid 2D signal
        self.data_bus.latest.return_value = np.array([[5.0, 1.0], [2.0, 3.0]])
        self.assertFalse(self.plot.accepts_signal(self.data_bus, "invalid_signal"))

    def test_bind_external_signal(self):
        """Test binding an external signal to the LinePlot."""
        self.data_bus.latest.return_value = np.array([0.0]) # Valid 1D return
        
        # We need to bind to the renderer first so VBO buffers can be instantiated
        self.plot.bind_renderer(self.renderer)
        self.plot.bind_external_signal(self.data_bus, ["test_signal_1", "test_signal_2"])
        
        self.assertIn("test_signal_1", self.plot.signal_names)
        self.assertIn("test_signal_2", self.plot.signal_names)
        self.assertEqual(len(self.plot._local), 2)
        self.assertEqual(self.plot._local["test_signal_1"].size, self.plot.points_per_channel)
        
    def test_update_limits(self):
        """Test that data updating successfully tracks min/max limits over time."""
        self.data_bus.latest.return_value = np.array([10.0])
        self.plot.bind_renderer(self.renderer)
        self.plot.bind_external_signal(self.data_bus, ["test_signal_1"])
        
        # Update tick 1
        self.plot.update()
        
        # Limits should now jump dynamically
        self.assertIsNotNone(getattr(self.plot, 'data_max', None))
        self.assertIsNotNone(getattr(self.plot, 'data_min', None))
        self.assertEqual(self.plot.data_max, 10.0)

    def test_draw_depth_test_toggle(self):
        """Test that draw disables Context DEPTH_TEST initially and enables it back at the end."""
        self.plot.bind_renderer(self.renderer)
        self.plot.draw(self.renderer)
        
        self.renderer.ctx.disable.assert_called_with(moderngl.DEPTH_TEST)
        self.renderer.ctx.enable.assert_called_with(moderngl.DEPTH_TEST)

    def test_draw_renders_signals(self):
        """Test drawing calls correct uniforms and renderer commands when signals are populated."""
        self.data_bus.latest.return_value = np.array([0.0])
        self.plot.bind_renderer(self.renderer)
        self.plot.bind_external_signal(self.data_bus, ["test_signal"])
        
        # Clear mock calls initiated from binding
        self.renderer.draw.reset_mock()
        
        self.plot.draw(self.renderer)
        
        # Check that uniform was set for standard lines
        self.renderer.set_uniform.assert_any_call("line_plot", "u_max", self.plot.y_max)
        
        # Ensure that line_plot was commanded to draw
        draw_calls = [call for call in self.renderer.draw.call_args_list if call[0][0] == "line_plot"]
        self.assertGreater(len(draw_calls), 0, "LinePlot failed to dispatch draw command for signal tracking.")

    def test_draw_renders_text(self):
        """Test that typography is dispatched when text_renderer exists."""
        self.data_bus.latest.return_value = np.array([0.0])
        self.plot.bind_renderer(self.renderer)
        self.plot.bind_external_signal(self.data_bus, ["test_signal_text"])
        
        self.plot.data_max = 1.0
        self.plot.data_min = -1.0
        
        self.plot.draw(self.renderer)
        
        # Asserts text renderer made at least one pass
        self.assertGreater(self.renderer.text_renderer.render_text.call_count, 0)
        
        # Look for the legend label drawing specifically
        legend_label_drawn = any(
            "test_signal_text" in call.args[0] for call in self.renderer.text_renderer.render_text.call_args_list
        )
        self.assertTrue(legend_label_drawn, "Legend label text was not rendered.")

if __name__ == '__main__':
    unittest.main()
