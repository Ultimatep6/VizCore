# vizcore/text/font_atlas.py
import numpy as np
from PIL import Image, ImageDraw, ImageFont

class FontAtlas:
    """
    Generates a texture atlas for ASCII glyphs.

    Responsibilities:
        - Rasterize glyphs from a font file
        - Pack glyphs into a single texture
        - Provide UV coordinates per character
    """
    CHARS = ''.join(chr(i) for i in range(32, 127))  # printable ASCII

    def __init__(self, font_path=None, font_size=14, atlas_size=512):
        self.font_size = font_size
        self.atlas_size = atlas_size
        self.uvs = {}        # char -> (u0, v0, u1, v1)
        self.glyph_size = {} # char -> (pixel_w, pixel_h)

        font = ImageFont.truetype(font_path, font_size) if font_path \
               else ImageFont.load_default()

        self._image, self.uvs, self.glyph_size, self.glyph_offset = self._pack(font, atlas_size)
        self.texture_data = np.array(self._image, dtype=np.uint8)

    def _pack(self, font, atlas_size):
        image = Image.new('L', (atlas_size, atlas_size), 0)
        draw = ImageDraw.Draw(image)
        uvs = {}
        glyph_size = {}
        glyph_offset = {}

        x, y = 0, 0
        row_height = 0

        for ch in self.CHARS:
            bbox = font.getbbox(ch)
            offset_x = bbox[0]
            offset_y = bbox[1]
            glyph_offset[ch] = (offset_x, offset_y)
            w = bbox[2] - bbox[0]
            h = bbox[3] - bbox[1]
            w = max(w, 1)
            h = max(h, 1)

            # ← wrap check BEFORE draw
            if x + w > atlas_size:
                x = 0
                y += row_height
                row_height = 0

            # ← single draw call with offset applied
            draw.text((x - offset_x, y - offset_y), ch, font=font, fill=255)

            uvs[ch] = (
                x / atlas_size,
                y / atlas_size,
                (x + w) / atlas_size,
                (y + h) / atlas_size,
            )
            glyph_size[ch] = (w, h)
            x += w
            row_height = max(row_height, h)

        return image, uvs, glyph_size, glyph_offset



    def upload(self, ctx):
        """Upload atlas texture to GPU, returns moderngl Texture."""
        tex = ctx.texture(
            (self.atlas_size, self.atlas_size),
            1,                          # single channel (greyscale)
            self.texture_data.tobytes(),
        )
        tex.filter = (ctx.LINEAR, ctx.LINEAR)
        return tex