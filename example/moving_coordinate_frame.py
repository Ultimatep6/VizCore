from vizcore.widget.kinematicFrame import KinematicFrame
from vizcore.text.text import TextAtlas, TextRenderer
from vizcore.utils import rotation_x, rotation_y, translation, perspective

import numpy as np
import pyglet
import moderngl

if __name__ == "__main__":
    width, height = 800, 600

    window = pyglet.window.Window(width, height, "Orientation Frame")
    window.switch_to()

    ctx = moderngl.create_context()
    ctx.enable(moderngl.DEPTH_TEST)
    ctx.viewport = (0, 0, width, height)

    window_wrapper = type('Window', (), {
        'ctx': ctx, 
        'size': (width, height),
        'texture': None  # Will be set by TextRenderer
    })()

    # Build atlas + 3D text renderer (shared, no duplication)
    atlas = TextAtlas(font_path="vizcore/text/data/cmunbi.ttf", font_size=48)
    text_renderer = TextRenderer(window=window_wrapper, atlas=atlas)

    # Pass text_renderer into OrientationFrame — it owns the labels
    frame = KinematicFrame(
        ctx,
        shaft_radius=0.04, shaft_height=0.6,
        head_radius=0.10,  head_height=0.2,
        segments=32,
        text_renderer=text_renderer,
        label_scale=0.003,   # tune: smaller = smaller text in world space
    )

    vel = np.array([-4, 10, 0.0], dtype=np.float32)

    frame.signal_names = ["dynamic_signal"]
    
    frame.values = {"dynamic_signal": vel}  # initialize with zero velocity

    frame._build_verts()  # build geometry and upload to GPU

    camera_tilt  = rotation_x(np.radians(25))
    camera_trans = translation(0, -0.3, -3)
    view         = camera_trans @ camera_tilt
    projection   = perspective(np.radians(60), width / height, 0.1, 100)

    angle_x = 0.0
    angle_y = 1

    @window.event
    def on_draw():
        global angle_x, angle_y
        ctx.clear(0.1, 0.1, 0.1)

        angle_y += 0.01
        angle_x += 0.004

        model = rotation_y(angle_y) @ rotation_x(angle_x)

        # Pass model/view/projection separately — frame handles both arrows + labels
        frame.render(model, view, projection)

    @window.event
    def on_resize(w, h):
        ctx.viewport = (0, 0, w, h)

    pyglet.app.run()


