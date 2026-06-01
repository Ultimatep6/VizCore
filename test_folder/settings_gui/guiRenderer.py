import os
import numpy as np
import moderngl
import pyglet

SHADER_DIR = os.path.join(os.path.dirname(__file__), "shaders")


def measure_text(text_str, font_size=10):
    if not text_str:
        return 0
    lbl = pyglet.text.Label(text_str, font_size=font_size)
    return lbl.content_width


class GuiRenderer:
    def __init__(self, mainWindow):
        self.width = mainWindow.wnd.width
        self.height = mainWindow.wnd.height
        self.ctx = mainWindow.ctx

        self._ui_program = mainWindow.load_program(
            vertex_shader=os.path.join(SHADER_DIR, "ui.vert"),
            fragment_shader=os.path.join(SHADER_DIR, "ui.frag"),
        )

        quad_verts = np.array([0.0, 0.0, 1.0, 0.0, 0.0, 1.0, 1.0, 1.0], dtype="f4")
        self.quad_vbo = self.ctx.buffer(quad_verts.tobytes())
        self.quad_vao = self.ctx.vertex_array(
            self._ui_program, [(self.quad_vbo, "2f", "in_vert")]
        )

        outline_verts = np.array([0.0, 0.0, 1.0, 0.0, 1.0, 1.0, 0.0, 1.0], dtype="f4")
        self.outline_vbo = self.ctx.buffer(outline_verts.tobytes())
        self.outline_vao = self.ctx.vertex_array(
            self._ui_program, [(self.outline_vbo, "2f", "in_vert")]
        )

    def quad(self, x, y, w, h, color, alpha=1.0):
        r, g, b = color[:3]
        self._ui_program["u_resolution"] = (self.width, self.height)
        self._ui_program["u_pos"] = (x, y)
        self._ui_program["u_size"] = (w, h)
        self._ui_program["u_color"] = (r, g, b, alpha)
        if alpha < 1.0:
            self.ctx.enable(moderngl.BLEND)
        self.quad_vao.render(moderngl.TRIANGLE_STRIP)
        if alpha < 1.0:
            self.ctx.disable(moderngl.BLEND)

    def outline(self, x, y, w, h, color, alpha=1.0):
        r, g, b = color[:3]
        self._ui_program["u_resolution"] = (self.width, self.height)
        self._ui_program["u_pos"] = (x, y)
        self._ui_program["u_size"] = (w, h)
        self._ui_program["u_color"] = (r, g, b, alpha)
        self.outline_vao.render(moderngl.LINE_LOOP)

    def text(self, text_str, x, y, color=(1.0, 1.0, 1.0), scale=0.5,
             anchor_x="left", anchor_y="bottom", clip_rect=None):
        if not text_str:
            return
        r, g, b = color[:3]
        ir, ig, ib = int(r * 255), int(g * 255), int(b * 255)
        font_size = max(1, int(scale * 20))
        lbl = pyglet.text.Label(
            text_str,
            color=(ir, ig, ib, 255),
            font_size=font_size,
            anchor_x=anchor_x,
            anchor_y=anchor_y,
            x=int(x),
            y=int(y),
        )
        lbl.draw()

    @staticmethod
    def text_width(text_str, scale=0.5):
        """Return the pixel width of *text_str* at the given scale."""
        if not text_str:
            return 0
        font_size = max(1, int(scale * 20))
        return pyglet.text.Label(text_str, font_size=font_size).content_width
