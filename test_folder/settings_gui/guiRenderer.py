import os
import numpy as np
import moderngl
import pyglet

SHADER_DIR = os.path.join(os.path.dirname(__file__), "shaders")


class GuiRenderer:
    def __init__(self, mainWindow):
        self.width = mainWindow.wnd.width
        self.height = mainWindow.wnd.height

        ctx = mainWindow.ctx

        self._ui_program = mainWindow.load_program(
            vertex_shader=os.path.join(SHADER_DIR, "ui.vert"),
            fragment_shader=os.path.join(SHADER_DIR, "ui.frag"),
        )

        quad_verts = np.array([0.0, 0.0, 1.0, 0.0, 0.0, 1.0, 1.0, 1.0], dtype="f4")
        self.quad_vbo = ctx.buffer(quad_verts.tobytes())
        self.quad_vao = ctx.vertex_array(
            self._ui_program, [(self.quad_vbo, "2f", "in_vert")]
        )

        outline_verts = np.array([0.0, 0.0, 1.0, 0.0, 1.0, 1.0, 0.0, 1.0], dtype="f4")
        self.outline_vbo = ctx.buffer(outline_verts.tobytes())
        self.outline_vao = ctx.vertex_array(
            self._ui_program, [(self.outline_vbo, "2f", "in_vert")]
        )

    def quad(self, x, y, w, h, color):
        self._ui_program["u_resolution"] = (self.width, self.height)
        self._ui_program["u_pos"] = (x, y)
        self._ui_program["u_size"] = (w, h)
        self._ui_program["u_color"] = color
        self.quad_vao.render(moderngl.TRIANGLE_STRIP)

    def outline(self, x, y, w, h, color):
        self._ui_program["u_resolution"] = (self.width, self.height)
        self._ui_program["u_pos"] = (x, y)
        self._ui_program["u_size"] = (w, h)
        self._ui_program["u_color"] = color
        self.outline_vao.render(moderngl.LINE_LOOP)
