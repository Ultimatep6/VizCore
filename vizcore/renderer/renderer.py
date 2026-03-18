import os
import moderngl
from vizcore.renderer.shader_manager import ShaderManager
from vizcore.text.font_atlas import FontAtlas
from vizcore.text.text_renderer import TextRenderer
from vizcore.utils.config import find_system_font


class Renderer:
    def __init__(self, ctx, window_size):
        self.ctx = ctx
        self.window_size = window_size
        self.shader_manager = ShaderManager(ctx)

        shader_dir = os.path.join(os.path.dirname(__file__), '..', 'shaders')
        self.shader_manager.load_shader(
            'line_plot',
            os.path.join(shader_dir, 'line_plot.vert'),
            os.path.join(shader_dir, 'line_plot.frag'),
        )

        font_atlas = FontAtlas(font_path=find_system_font(), font_size=32)

        self.text = TextRenderer(ctx, font_atlas, window_size)

    def draw_text(self, text, x, y, color=(1.0, 1.0, 1.0, 1.0)):
        # Text is always in window space — ensure full viewport
        self.ctx.viewport = (0, 0, self.window_size[0], self.window_size[1])
        self.text.draw(text, x, y, color)



    def draw_line_plot_vbo(self, vbo, n_points, rect=None, color=(0,200,255,255), margin=10):
        prog = self.shader_manager.get_shader('line_plot')
        if prog is None:
            return
        vao = self.ctx.simple_vertex_array(prog, vbo, 'in_vert')
        prog['u_color'].value = tuple(c / 255.0 for c in color)
        if rect is not None:
            self.ctx.viewport = (
                int(rect.x + margin), int(rect.y + margin),
                int(rect.width - 2 * margin), int(rect.height - 2 * margin)
            )
        vao.render(moderngl.LINE_STRIP, vertices=n_points)
        # Restore to full window — NOT self.ctx.viewport[2:] which is now widget size
        self.ctx.viewport = (0, 0, self.window_size[0], self.window_size[1])

    def draw_line_plot(self, points, rect=None, color=(0, 200, 255, 255), margin=10):
        if len(points) < 4:
            return
        prog = self.shader_manager.get_shader('line_plot')
        if prog is None:
            return
        if rect is not None:
            self.ctx.viewport = (
                int(rect.x + margin), int(rect.y + margin),
                int(rect.width - 2 * margin), int(rect.height - 2 * margin)
            )
        vbo = self.ctx.buffer(points.astype('f4').tobytes())
        vao = self.ctx.simple_vertex_array(prog, vbo, 'in_vert')
        prog['u_color'].value = tuple(c / 255.0 for c in color)
        vao.render(moderngl.LINE_STRIP)
        vbo.release()
        self.ctx.viewport = (0, 0, self.window_size[0], self.window_size[1])


    def begin_frame(self):
        self.ctx.clear(0.1, 0.1, 0.1)

    def end_frame(self):
        pass