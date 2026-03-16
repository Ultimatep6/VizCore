import os
import moderngl
from vizcore.renderer.shader_manager import ShaderManager

class Renderer:
    def __init__(self, ctx: moderngl.Context):
        self.ctx = ctx
        self.shader_manager = ShaderManager(ctx)

        # Load shaders relative to this file's location
        shader_dir = os.path.join(os.path.dirname(__file__), '..', 'shaders')
        self.shader_manager.load_shader(
            'line_plot',
            os.path.join(shader_dir, 'line_plot.vert'),
            os.path.join(shader_dir, 'line_plot.frag'),
        )

    def draw_line_plot(self, points, rect=None, color=(0, 200, 255, 255), margin=10):
        if len(points) < 4:
            return
        prog = self.shader_manager.get_shader('line_plot')
        if prog is None:
            return

        if rect is not None:
            self.ctx.viewport = (
                int(rect.x + margin),
                int(rect.y + margin),
                int(rect.width - 2 * margin),
                int(rect.height - 2 * margin),
            )

        vbo = self.ctx.buffer(points.astype('f4').tobytes())
        vao = self.ctx.simple_vertex_array(prog, vbo, 'in_vert')
        prog['u_color'].value = tuple(c / 255.0 for c in color)
        vao.render(moderngl.LINE_STRIP)
        vbo.release()

        if rect is not None:
            w, h = self.ctx.viewport[2:]
            self.ctx.viewport = (0, 0, w, h)

    def begin_frame(self):
        self.ctx.clear(0.1, 0.1, 0.1)

    def end_frame(self):
        pass