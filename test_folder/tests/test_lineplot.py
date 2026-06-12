"""
End-to-end test harness for the refactored LinePlot widget.

Demonstrates:
  - Hierarchical signal schema filtering
  - Context menu with signal tree navigation
  - Attach / remove signals at runtime
  - Transparent chart rendering with alpha-blended legend
  - Auto-scaling Y range with smooth tracking

Controls:
  RMB          Open context menu (Attach / Remove signals)
  SPACE        Toggle simulation on/off
  ESC          Close context menu
"""

import sys
import os
import math
import numpy as np
from types import SimpleNamespace

import moderngl
import moderngl_window as mglw

# Ensure test_folder root is on sys.path
_TEST_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _TEST_DIR not in sys.path:
    sys.path.insert(0, _TEST_DIR)

from widgets.widget_base import DrawingContext
from widgets.line_plot import LinePlot
from widgets.widget_gui import MenuRenderer

from vizcore.renderer.renderer import Renderer
from vizcore.bus.data_bus import DataBus


class SignalSimulation:
    """
    Generates hierarchic test signals compatible with LinePlot's schema.

    Signal tree registered via DataBus:
        sensors
          imu
            accel_x     (sine wave)
            accel_y     (cosine wave)
          gps
            latitude    (sawtooth)
        step_target     (square wave)
        system_response (damped step response)
    """

    def __init__(self, data_bus):
        self._data_bus = data_bus
        self._t = 0.0
        self._step_last_switch = 0.0
        self._step_target = 0.0
        self._response = 0.0
        self._vel = 0.0
        # Seed once to register signal metadata
        self.step(0.0)

    def step(self, dt):
        self._t += dt

        accel_x = math.sin(self._t * 2.0)
        accel_y = math.cos(self._t * 1.7)
        lat = 2.0 * (self._t % 3.0) / 3.0 - 1.0

        # Square wave every 4 s
        if self._t - self._step_last_switch > 4.0:
            self._step_target = 1.5 if self._step_target == 0.0 else 0.0
            self._step_last_switch = self._t

        kp, kd = 15.0, 2.5
        error = self._step_target - self._response
        acc = kp * error - kd * self._vel
        self._vel += acc * dt
        self._response += self._vel * dt

        self._data_bus.push_payload({
            "sensors": {
                "imu": {
                    "accel_x": [round(accel_x, 4)],
                    "accel_y": [round(accel_y, 4)],
                },
                "gps": {
                    "latitude": [round(lat, 4)],
                },
            },
            "step_target": [round(self._step_target, 4)],
            "system_response": [round(self._response, 4)],
        })


class LinePlotTest(mglw.WindowConfig):
    """Test harness for the refactored LinePlot widget."""

    gl_version = (3, 3)
    window_size = (1280, 720)
    title = "LinePlot Test  [RMB=menu  SPACE=toggle sim  ESC=close menu]"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        w, h = self.wnd.size

        self.ctx.enable(moderngl.BLEND)
        self.ctx.blend_func = (moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA)

        # 1. DataBus with hierarchical signals
        self.data_bus = DataBus()
        self.sim = SignalSimulation(self.data_bus)

        # 2. Renderer
        app = SimpleNamespace(
            ctx=self.ctx,
            window=SimpleNamespace(width=w, height=h),
        )
        self._renderer = Renderer(app, (w, h))

        # 3. DrawingContext (high-level 2D drawing)
        self._drawing_ctx = DrawingContext(self._renderer, w, h)

        # 4. LinePlot widget
        self.widget = LinePlot(max_points=500)
        self.widget._bind_renderer(self._renderer)
        self.widget._bind_drawing_context(self._drawing_ctx)
        self.widget._bind_data_bus(self.data_bus)
        self.widget._on_tile_resize(0, 0, w, h)
        self.widget.setup()

        # Attach one signal so something renders initially
        self.widget.attach_signal("step_target")

        # 5. Menu renderer for context menus
        self._menu_renderer = MenuRenderer(h, w)

        # Simulation state
        self.sim_playing = True

    # =================================================================
    # Simulation update (called each frame from on_render)
    # =================================================================

    def _update(self, dt):
        if self.sim_playing:
            self.sim.step(dt)
        self.widget.update()

    # =================================================================
    # Rendering
    # =================================================================

    def on_render(self, time, frame_time):
        self._update(frame_time)

        w, h = self.wnd.size
        self.ctx.clear(0.05, 0.05, 0.08, 1.0)
        self.ctx.disable(moderngl.DEPTH_TEST)

        # Draw the widget (full window = single tile)
        self.widget.draw(self._drawing_ctx)

        # Draw context menu overlay
        for cmd in self._menu_renderer.get_render_commands():
            if cmd['type'] == 'quad':
                self._drawing_ctx.quad(cmd['x'], cmd['y'], cmd['w'], cmd['h'], cmd['color'], cmd['alpha'])
            elif cmd['type'] == 'outline':
                self._drawing_ctx.outline(cmd['x'], cmd['y'], cmd['w'], cmd['h'], cmd['color'], cmd['alpha'])
            elif cmd['type'] == 'text':
                self._drawing_ctx.text(cmd['text'], cmd['x'], cmd['y'], cmd['color'], cmd['scale'], cmd['anchor_x'], cmd['anchor_y'])

    # =================================================================
    # Input handling
    # =================================================================

    def on_mouse_press_event(self, x, y, button):
        if self._menu_renderer.on_mouse_press(x, y, button):
            return

        if button == 2:  # Right click
            entries = self.widget.get_context_menu()
            if entries:
                self._menu_renderer.open(entries, x, y)

    def on_mouse_release_event(self, x, y, button):
        self._menu_renderer.on_mouse_release(x, y, button)

    def on_mouse_drag_event(self, x, y, dx, dy):
        pass  # No drag handling for now

    def on_mouse_position_event(self, x, y, dx, dy):
        self._menu_renderer.on_mouse_move(x, y)

    def on_key_event(self, key, action, modifiers):
        if action == self.wnd.keys.ACTION_PRESS:
            if key == self.wnd.keys.SPACE:
                self.sim_playing = not self.sim_playing
                print(f"Simulation {'PLAYING' if self.sim_playing else 'PAUSED'}")
            elif key == self.wnd.keys.ESCAPE:
                self._menu_renderer.close()

    def on_resize(self, width, height):
        self.ctx.viewport = (0, 0, width, height)
        self._menu_renderer._win_h = height
        self.widget._on_tile_resize(0, 0, width, height)
        if self._drawing_ctx is not None:
            self._drawing_ctx._w = width
            self._drawing_ctx._h = height


if __name__ == "__main__":
    LinePlotTest.run()
