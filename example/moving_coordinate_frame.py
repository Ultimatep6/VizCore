from vizcore.widget.orientationFrame import OrientationFrame
from vizcore.text.text import TextAtlas, TextRenderer

import numpy as np
import pyglet
import moderngl

width, height = 800, 600
    
# Create pyglet window FIRST (this creates the OpenGL context)
window = pyglet.window.Window(width, height, "Text Test")

# Get the ModernGL context from pyglet's context
ctx = moderngl.create_context()

# Create a simple window wrapper object
window_wrapper = type('Window', (), {
    'ctx': ctx, 
    'size': (width, height),
    'texture': None  # Will be set by TextRenderer
})()

# Create font atlas
atlas = TextAtlas(window=window_wrapper, font_path="vizcore/text/data/cmunbi.ttf", font_size=48)

# Save atlas for debugging
atlas.atlas_image.save("font_atlas_debug.png")

# Create text renderer
text_renderer = TextRenderer(window=window_wrapper, atlas=atlas)

x,y = 50, 0
vx, vy = 5, 10
dt = 1/60

@window.event
def on_draw():
    global x, y
    window.clear()
    ctx.clear(0.0, 0.0, 0.0, 1.0)
    text_renderer.render_text("X", x=x, y=y, color=(1.0, 0.0, 0.0, 1.0))  # Render red "X"

    x += vx*dt
    y += vy*dt

pyglet.app.run()


