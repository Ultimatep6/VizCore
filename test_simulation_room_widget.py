#!/usr/bin/env python3
"""Test script for SimulationRoomWidget."""

import moderngl
import pyglet
import numpy as np
from vizcore.window.window import Window
from vizcore.widget.simulation_room import SimulationRoomWidget

width, height = 1024, 768
window = pyglet.window.Window(width, height, "VizCore - Simulation Room", resizable=True)

ctx = moderngl.create_context()
ctx.enable(moderngl.DEPTH_TEST | moderngl.CULL_FACE)
ctx.viewport = (0, 0, width, height)

app = type("App", (object,), {"ctx": ctx, "window": window})()

viz_window = Window(app, width, height)

sim_room = SimulationRoomWidget()
viz_window.bind_widget_to_tile(0, sim_room)

viz_window.is_playing = True

pyglet.clock.schedule_interval(viz_window.update, 1 / 60.0)

print("=" * 60)
print("VizCore - Simulation Room Widget")
print("=" * 60)
print("Controls:")
print("  A / D: Switch camera (when widget is focused)")
print("  Right Click: Open menu to add widgets")
print("  Select 'Simulation Room' from menu")
print("=" * 60)

try:
    pyglet.app.run()
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()