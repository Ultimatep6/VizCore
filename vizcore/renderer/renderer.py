import os
import moderngl
from vizcore.renderer.shader_manager import ShaderManager
from vizcore.text.font_atlas import FontAtlas
from vizcore.text.text_renderer import TextRenderer
from vizcore.utils.config import find_system_font
import numpy as np


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

        font_atlas_body = FontAtlas(font_path=find_system_font(), font_size=18)
        font_atlas_title = FontAtlas(font_path=find_system_font(), font_size=42)

        self.text       = TextRenderer(ctx, font_atlas_body, window_size)
        self.text_title = TextRenderer(ctx, font_atlas_title, window_size)

    def _gl_to_pixel_y(self, gl_y):
        """Convert OpenGL y-coordinate (bottom=0) to pixel y-coordinate (top=0).
        
        Note: y in TextRenderer represents the TOP edge of the text bounding box,
        so we don't need to adjust for font height here.
        """
        return self.window_size[1] - gl_y

    def draw_text(self, text, x, y, color=(1.0, 1.0, 1.0, 1.0), rotation_deg=0.0):
        """Draw text at position (x,y) in OpenGL coordinates with optional rotation."""
        pixel_y = self._gl_to_pixel_y(y)
        self.text.draw(text, x, pixel_y, color, rotation_deg=rotation_deg)
    
    def draw_title(self, text, cx, y, color=(1.0, 1.0, 1.0, 1.0)):
        """Draw title text centered at cx, at y position in OpenGL coordinates."""
        w, _ = self.text_title.measure(text)
        pixel_y = self._gl_to_pixel_y(y)
        self.text_title.draw(text, cx - w // 2, pixel_y, color)

    def draw_text_centered(self, text, cx, y, color=(1.0, 1.0, 1.0, 1.0)):
        """Draw text horizontally centered around pixel x=cx."""
        w, _ = self.text.measure(text)
        self.draw_text(text, cx - w // 2, y, color)
    
    def draw_axis_label_y(self, text, x, cy, color=(1.0, 1.0, 1.0, 1.0)):
        """Draw Y-axis label rotated 90 degrees counterclockwise, vertically centered at cy."""
        # Convert GL y-coordinate to pixel coordinate
        pixel_cy = self._gl_to_pixel_y(cy)
        
        # For vertical text, we want to center it vertically
        # After rotation, the text height becomes the horizontal extent
        w, h = self.text.measure(text)
        # Adjust y position to center the rotated text
        # When rotated 90°, the text's "width" becomes its vertical extent
        adjusted_y = pixel_cy - w // 2
        
        # Rotate 90 degrees counterclockwise for vertical text
        self.text.draw(text, x, adjusted_y, color, rotation_deg=90.0)

    def measure_text(self, text):
        return self.text.measure(text)
    
    def draw_rect(self, x, y, w, h, color=(0.1, 0.1, 0.1, 1.0)):
        """Draw a filled rectangle in OpenGL coordinates (y=0 at bottom)."""
        # Convert OpenGL coords to NDC
        nx = (x / self.window_size[0]) * 2 - 1
        # y is bottom edge in GL coords; convert to NDC
        ny = (1 - (y + h) / self.window_size[1]) * 2 - 1
        nw = (w / self.window_size[0]) * 2
        nh = (h / self.window_size[1]) * 2
        
        verts = np.array([
            nx,      ny,
            nx + nw, ny,
            nx,      ny + nh,
            nx + nw, ny,
            nx + nw, ny + nh,
            nx,      ny + nh,
        ], dtype='f4')
        
        prog = self.shader_manager.get_shader('line_plot')
        vbo = self.ctx.buffer(verts.tobytes())
        vao = self.ctx.simple_vertex_array(prog, vbo, 'in_vert')
        prog['u_color'].value = color
        vao.render(moderngl.TRIANGLES)
        vbo.release()

    def _draw_line_plot_internal(self, vbo, n_points, rect=None, color=(0,200,255,255), margin=10):
        """Internal method for line plot rendering (eliminates duplication)."""
        prog = self.shader_manager.get_shader('line_plot')
        if prog is None:
            return
        
        if rect is not None:
            self.ctx.viewport = (
                int(rect.x + margin), int(rect.y + margin),
                int(rect.width - 2 * margin), int(rect.height - 2 * margin)
            )
        
        vao = self.ctx.simple_vertex_array(prog, vbo, 'in_vert')
        prog['u_color'].value = tuple(c / 255.0 for c in color)
        vao.render(moderngl.LINE_STRIP, vertices=n_points)
        
        # Restore full viewport
        self.ctx.viewport = (0, 0, self.window_size[0], self.window_size[1])

    def draw_line_plot_vbo(self, vbo, n_points, rect=None, color=(0,200,255,255), margin=10):
        """Draw line plot using pre-allocated VBO."""
        self._draw_line_plot_internal(vbo, n_points, rect, color, margin)

    def draw_line_plot(self, points, rect=None, color=(0, 200, 255, 255), margin=10):
        """Draw line plot from point array."""
        if len(points) < 4:
            return
        vbo = self.ctx.buffer(points.astype('f4').tobytes())
        self._draw_line_plot_internal(vbo, len(points) // 2, rect, color, margin)
        vbo.release()

    def begin_frame(self):
        self.ctx.clear(0.1, 0.1, 0.1)

    def end_frame(self):
        pass