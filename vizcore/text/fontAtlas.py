import freetype
from PIL import Image
import numpy as np
from rectpack import newPacker, MaxRectsBssf
import moderngl
import pyglet

class FontAtlas:
    def __init__(self, font_path, font_size=48, atlas_size=2048):

        self.font_path = font_path
        self.font_size = font_size
        self.atlas_size = atlas_size
        self.characters = {}

        self.create_atlas()

    def create_atlas(self):
        # Load the font face
        face = freetype.Face(self.font_path)
        face.set_char_size(self.font_size * 64)  # FreeType uses 1/64th pixels
        
        # Simple grid-based packing (guaranteed to work)
        atlas_image = Image.new('L', (self.atlas_size, self.atlas_size), color=0)
        characters = {}

        x_offset = 0
        y_offset = 0
        row_height = 0

        for char_code in range(0, 0x10FFFF):
            character = chr(char_code)
            glyph_index = face.get_char_index(character)
            if glyph_index == 0:
                continue
            
            glyph_image, metrics = render_with_freetype(character, face)
            w, h = metrics['size']
            
            # Check if we need to wrap to next row
            if x_offset + w > self.atlas_size:
                x_offset = 0
                y_offset += row_height
                row_height = 0
            
            # Check if we're out of vertical space
            if y_offset + h > self.atlas_size:
                break
            
            # Paste glyph
            atlas_image.paste(glyph_image, (x_offset, y_offset))
            
            # Store character info
            characters[character] = {
                'uv': (x_offset/self.atlas_size, y_offset/self.atlas_size, 
                    (x_offset+w)/self.atlas_size, (y_offset+h)/self.atlas_size),
                'size': metrics['size'],
                'bearing': metrics['bearing'],
                'advance': metrics['advance']
            }
            
            x_offset += w
            row_height = max(row_height, h)
        
        self.atlas_image = atlas_image
        self.characters = characters


class TextRenderer:
    def __init__(self, window, atlas):
        self.window = window
        self.atlas = atlas

        self.program = None

        self.upload_to_gpu()
        self.load_shader()

    def upload_to_gpu(self):
        """
        Upload a PIL Image to GPU as a ModernGL texture.
        """
        # Convert PIL Image to numpy array
        atlas_image = self.atlas.atlas_image
        image_data = np.array(self.atlas.atlas_image, dtype=np.uint8)
        
        # Create texture
        self.window.texture = self.window.ctx.texture(
            size=atlas_image.size,  
            components=1,
            data=image_data.tobytes()
        )

    def load_shader(self):
        # Loads the text.frag and text.vert shaders and creates a ModernGL program
        with open("vizcore/shaders/text.vert", "r") as vert_file:
            vert_shader = vert_file.read()
        with open("vizcore/shaders/text.frag", "r") as frag_file:
            frag_shader = frag_file.read()

        self._prog = self.window.ctx.program(
            vertex_shader=vert_shader,
            fragment_shader=frag_shader
        )


    def render_text(self, text, x, y, color=(1.0, 1.0, 1.0, 1.0), scale=1.0):
        # Build vertex data for all characters
        verts = []
        cursor_x = x
        ctx = self.window.ctx

        prog = self._prog
        characters = self.atlas.characters
        texture = self.window.texture
        
        for ch in text:
            if ch not in characters:
                continue
            
            char_info = characters[ch]
            u0, v0, u1, v1 = char_info['uv']
            gw, gh = char_info['size']
            ox, oy = char_info['bearing']
            
            # Apply scale to geometry
            gw, gh = gw * scale, gh * scale
            ox, oy = ox * scale, oy * scale
            
            # Calculate quad position
            x0 = cursor_x + ox
            y0 = y - oy  # Subtract bearing to position relative to baseline
            x1 = x0 + gw
            y1 = y0 + gh
            
            # Add two triangles (quad)
            verts += [
                x0, y0, u0, v0,
                x1, y0, u1, v0,
                x0, y1, u0, v1,
                x1, y0, u1, v0,
                x1, y1, u1, v1,
                x0, y1, u0, v1,
            ]
            
            cursor_x += char_info['advance'] * scale
        
            if not verts:
                return
        
        # Upload vertex data
        verts_array = np.array(verts, dtype='f4')
        vbo = ctx.buffer(verts_array.tobytes())
        vao = ctx.vertex_array(prog, [(vbo, '2f 2f', 'in_vert', 'in_uv')])

        # Get dynamic window dimensions from active viewport instead of static wrapper
        _, _, width, height = ctx.viewport
        
        mvp = np.array([
            [2.0/width,  0.0,         0.0, -1.0],
            [0.0,       -2.0/height,  0.0,  1.0],  # Negative to flip Y
            [0.0,        0.0,        -1.0,  0.0],
            [0.0,        0.0,         0.0,  1.0]
        ], dtype='f4').T

        
        # Set uniforms
        if len(color) == 4:
            prog['u_color'].value = color  # White color
        elif len(color) == 3:
            prog['u_color'].value = (*color, 1.0)  # Add alpha if not provided
        else:
            raise ValueError("Color must be a tuple of 3 (RGB) or 4 (RGBA) floats in range [0, 1]")
        
        prog['mvp'].write(mvp.astype('f4').tobytes())

        
        # Bind texture to texture unit 0
        texture.use(location=0)
        prog['u_atlas'].value = 0  # Tell shader to use texture unit 0
        
        # Enable blending for proper alpha rendering
        ctx.enable(moderngl.BLEND)
        ctx.blend_func = moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA
        
        # Render
        vao.render(moderngl.TRIANGLES)
        
        # Clean up
        ctx.disable(moderngl.BLEND)
        vbo.release()

    @staticmethod
    def _billboard_mvp(world_pos, view, projection, scale=0.05):
        """
        Build a billboard MVP for a label at `world_pos`.

        Extracts right/up axes from the VIEW matrix (inverse rotation columns)
        so the quad always faces the camera regardless of orientation.

        scale: world-space size of one atlas pixel (tune to taste)
        """
        # View matrix upper-left 3x3 is R (rotation). Its rows are camera axes
        # expressed in world space. We need columns of R^T = rows of R.
        right = view[0, :3]   # camera right in world space
        up    = -view[1, :3]   # camera up in world space

        # Build billboard model matrix
        # Columns: right, up, forward(unused for flat quad), translation
        m = np.eye(4, dtype=np.float32)
        m[:3, 0] = right  * scale
        m[:3, 1] = up     * scale
        m[:3, 3] = world_pos

        return projection @ view @ m
    
    def render_label(self, text, world_pos, view, projection,
                     color=(1.0, 1.0, 1.0, 1.0), scale=0.05):
        """
        Render `text` as a billboard at `world_pos` (3-element array/list).

        view, projection: 4x4 numpy arrays (row-major, same convention as OrientationFrame)
        scale: world-space size per atlas pixel — controls physical text size
        """
        ctx = self.window.ctx

        characters = self.atlas.characters
        verts = []
        cursor_x = 0.0   # local X offset in atlas-pixel units

        for ch in text:
            if ch not in characters:
                continue

            char_info = characters[ch]
            u0, v0, u1, v1 = char_info['uv']
            gw, gh = char_info['size']
            ox, oy = char_info['bearing']

            # Local quad corners (in atlas-pixel units; billboard matrix applies scale)
            x0 = cursor_x + ox
            y0 = oy          # bearing flips Y (same logic as your 2D renderer)
            x1 = x0 + gw
            y1 = y0 + gh

            # 3D position: X and Y are local billboard axes, Z=0 (flat quad)
            verts += [
                x0, y0, 0.0,  u0, v0,
                x1, y0, 0.0,  u1, v0,
                x0, y1, 0.0,  u0, v1,
                x1, y0, 0.0,  u1, v0,
                x1, y1, 0.0,  u1, v1,
                x0, y1, 0.0,  u0, v1,
            ]

            cursor_x += char_info['advance']

        if not verts:
            return

        mvp = self._billboard_mvp(np.array(world_pos, dtype=np.float32),
                                  view, projection, scale)

        verts_array = np.array(verts, dtype='f4')
        vbo = ctx.buffer(verts_array.tobytes())
        vao = ctx.vertex_array(
            self._prog,
            [(vbo, '3f 2f', 'in_vert', 'in_uv')],
        )

        self._prog['mvp'].write(mvp.astype('f4').T.tobytes())
        self._prog['u_color'].value = color if len(color) == 4 else (*color, 1.0)
        self.window.texture.use(location=0)
        self._prog['u_atlas'].value = 0

        ctx.enable(moderngl.BLEND)
        ctx.blend_func = moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA

        vao.render(moderngl.TRIANGLES)

        ctx.disable(moderngl.BLEND)
        vbo.release()



def render_with_freetype(char, face):
    """
    Render a single character glyph to a bitmap using FreeType.
    Returns a PIL Image and metrics.
    """
    # Load and render the character
    face.load_char(char, freetype.FT_LOAD_RENDER)
    glyph = face.glyph
    
    # Get bitmap data
    bitmap = glyph.bitmap
    width = bitmap.width
    rows = bitmap.rows
    
    if width == 0 or rows == 0:
        # Empty glyph (like space character)
        glyph_image = Image.new('L', (1, 1), 0)
        metrics = {
            'size': (width, rows),
            'bearing': (glyph.bitmap_left, -glyph.bitmap_top),  # CHANGED: negate bitmap_top
            'advance': glyph.advance.x >> 6
        }

        return glyph_image, metrics
    
    # Create numpy array from bitmap buffer
    bitmap_array = np.array(bitmap.buffer, dtype=np.uint8).reshape((rows, width))
    
    # Convert to PIL Image
    glyph_image = Image.fromarray(bitmap_array, mode='L')
    
    # Store metrics
    metrics = {
        'size': (width, rows),
        'bearing': (glyph.bitmap_left, glyph.bitmap_top),
        'advance': glyph.advance.x >> 6  # Convert from 1/64th pixels to pixels
    }
    
    return glyph_image, metrics


# Example usage
# if __name__ == "__main__":
#     width, height = 800, 600
    
#     # Create pyglet window FIRST (this creates the OpenGL context)
#     window = pyglet.window.Window(width, height, "Text Test")
    
#     # Get the ModernGL context from pyglet's context
#     ctx = moderngl.create_context()
    
#     # Create a simple window wrapper object
#     window_wrapper = type('Window', (), {
#         'ctx': ctx, 
#         'size': (width, height),
#         'texture': None  # Will be set by TextRenderer
#     })()
    
#     # Create font atlas
#     print("Creating font atlas...")
#     atlas = TextAtlas(window=window_wrapper, font_path="vizcore/text/data/cmunbi.ttf", font_size=48)
#     print(f"Atlas created with {len(atlas.characters)} characters")
    
#     # Save atlas for debugging
#     atlas.atlas_image.save("font_atlas_debug.png")
#     print("Atlas saved to font_atlas_debug.png")
    
#     # Create text renderer
#     text_renderer = TextRenderer(window=window_wrapper, atlas=atlas)
    
    

#     @window.event
#     def on_draw():
#         window.clear()
#         ctx.clear(0.0, 0.0, 0.0, 1.0)
#         text_renderer.render_text("X", x=50, y=300, color=(1.0, 0.0, 0.0, 1.0))  # Render red "X"
    
#     pyglet.app.run()


