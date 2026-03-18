# vizcore/text/text_renderer.py
import numpy as np
import moderngl
from vizcore.text.font_atlas import FontAtlas

class TextRenderer:
    """
    Renders text strings using a GPU font atlas.

    Responsibilities:
        - Draw characters using atlas UV coordinates
        - Manage glyph vertex buffers
    """
    VERT = """
    #version 330
    in vec2 in_vert;
    in vec2 in_uv;
    uniform vec2 u_resolution;
    out vec2 v_uv;
    void main() {
        // Convert pixel coords to NDC
        vec2 ndc = (in_vert / u_resolution) * 2.0 - 1.0;
        gl_Position = vec4(ndc.x, -ndc.y, 0.0, 1.0);
        v_uv = in_uv;
    }
    """
    FRAG = """
    #version 330
    uniform sampler2D u_atlas;
    uniform vec4 u_color;
    in vec2 v_uv;
    out vec4 f_color;
    void main() {
        float alpha = texture(u_atlas, v_uv).r;
        f_color = vec4(u_color.rgb, u_color.a * alpha);
    }
    """

    def __init__(self, ctx: moderngl.Context, font_atlas: FontAtlas, window_size):
        self.ctx = ctx
        self.atlas = font_atlas
        self.window_size = window_size  # (width, height) in pixels
        self.texture = font_atlas.upload(ctx)

        self.prog = ctx.program(
            vertex_shader=self.VERT,
            fragment_shader=self.FRAG,
        )
        # Pre-allocate a buffer large enough for 256 characters
        # Each char = 2 triangles = 6 vertices, each vertex = 4 floats (x,y,u,v)
        self._max_chars = 256
        self._vbo = ctx.buffer(
            np.zeros(self._max_chars * 6 * 4, dtype='f4').tobytes()
        )
        self._vao = ctx.vertex_array(
            self.prog,
            [(self._vbo, '2f 2f', 'in_vert', 'in_uv')]
        )

    def measure(self, text):
        """Return (width, height) in pixels for a given string."""
        w = sum(self.atlas.glyph_size[ch][0] for ch in text if ch in self.atlas.glyph_size)
        h = max((self.atlas.glyph_size[ch][1] for ch in text if ch in self.atlas.glyph_size), default=0)
        return w, h

    def draw(self, text, x, y, color=(1.0, 1.0, 1.0, 1.0)):
        """
        Draw text at pixel position (x, y) from top-left.
        color: (r, g, b, a) floats 0-1
        """
        verts = []
        cursor_x = x

        for ch in text:
            if ch not in self.atlas.uvs:
                continue
            u0, v0, u1, v1 = self.atlas.uvs[ch]
            gw, gh = self.atlas.glyph_size[ch]
            ox, oy = self.atlas.glyph_offset.get(ch, (0, 0))  # ← baseline offset

            x0, y0 = cursor_x,      y + oy   # ← shift quad down by oy
            x1, y1 = cursor_x + gw, y + oy + gh

            verts += [
                x0, y0, u0, v0,
                x1, y0, u1, v0,
                x0, y1, u0, v1,
                x1, y0, u1, v0,
                x1, y1, u1, v1,
                x0, y1, u0, v1,
            ]
            cursor_x += gw + ox  # ← also advance by full glyph width including left bearing
        if not verts:
            return

        data = np.array(verts, dtype='f4')
        n_quads = len(verts) // (6 * 4)   # each quad = 6 vertices × 4 floats
        self._vbo.write(data.tobytes())


        self.prog['u_resolution'].value = tuple(self.window_size)
        self.prog['u_color'].value = color
        self.texture.use(location=0)
        self.prog['u_atlas'].value = 0

        # Blend so text alpha works correctly
        self.ctx.enable(moderngl.BLEND)
        self.ctx.blend_func = moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA
        self._vao.render(moderngl.TRIANGLES, vertices=n_quads * 6)
        self.ctx.disable(moderngl.BLEND)