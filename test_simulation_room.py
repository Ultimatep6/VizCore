#!/usr/bin/env python3
"""Test script for VizCore Simulation Room - loads cube and shows controls."""

import moderngl
import pyglet
import numpy as np
from vizcore.window.window import Window
from vizcore.bus.data_bus import DataBus
from vizcore.widget.simulation_room import SimulationRoom
from vizcore.meshes import load_mesh

# Set up Pyglet window
width, height = 1024, 768
window = pyglet.window.Window(width, height, "VizCore Simulation Room", resizable=True)


@window.event
def on_mouse_press(x, y, button, modifiers):
    print(f"TEST: on_mouse_press button={button}")


# Create ModernGL context
ctx = moderngl.create_context()
ctx.enable(moderngl.DEPTH_TEST | moderngl.CULL_FACE)
ctx.viewport = (0, 0, width, height)

# Create application wrapper
app = type("App", (object,), {"ctx": ctx, "window": window})()

# Create VizCore window
viz_window = Window(app, width, height)

# Create SimulationRoom widget - with grid and axes off for cleaner test
sim_room = SimulationRoom(show_grid=False, show_axes=False)

# Load and add the test cube as an object
cube_mesh = load_mesh("test_models/test_cube.obj")
sim_room.objects["cube"] = {
    "mesh": cube_mesh,
    "position": np.array([0.0, 0.0, 0.0], dtype="f4"),
    "rotation": np.array([0.0, 0.0, 0.0], dtype="f4"),
    "color": np.array([0.9, 0.7, 0.2], dtype="f4"),  # Gold/Yellow
    "scale": np.array([0.5, 0.5, 0.5], dtype="f4"),
}

# Bind widget to tile 0
viz_window.bind_widget_to_tile(0, sim_room)

# Start playing
viz_window.is_playing = True

# Schedule the update loop
pyglet.clock.schedule_interval(viz_window.update, 1 / 60.0)

print("=" * 60)
print("VizCore Simulation Room")
print("=" * 60)
print("Controls:")
print("  A: Orbit camera left")
print("  D: Orbit camera right")
print("  Mouse Wheel: Zoom in/out")
print("  Space: Toggle simulation")
print("  V/H: Split tile vertically/horizontally")
print("  Right Click: Open menu to add widgets")
print("")
print("Scene:")
print("  - Gray grid on XZ plane")
print("  - Red X-axis (right), Green Y-axis (up), Blue Z-axis (forward)")
print("  - Gold cube at origin")
print("=" * 60)

try:
    pyglet.app.run()
except Exception as e:
    print(f"Error: {e}")
    import traceback

    traceback.print_exc()

