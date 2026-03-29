import freetype
from PIL import Image
import numpy as np
from rectpack import newPacker, MaxRectsBssf
import moderngl

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


def upload_to_gpu(atlas_image, ctx: moderngl.Context):
    """
    Upload a PIL Image to GPU as a ModernGL texture.
    """
    # Convert PIL Image to numpy array
    image_data = np.array(atlas_image, dtype=np.uint8)
    
    # Create texture
    texture = ctx.texture(
        size=atlas_image.size,  # (width, height)
        components=1,            # Grayscale = 1 component
        data=image_data.tobytes()  # Fixed: use data parameter
    )
    texture.filter = (moderngl.LINEAR, moderngl.LINEAR)  # Set filtering
    
    return texture


def create_atlas_with_freetype(font_path, font_size=48, atlas_size=2048):
    """
    Create a complete font atlas using FreeType.
    
    Returns:
        atlas_image: PIL Image of the atlas
        characters: Dictionary mapping char -> {uv, size, bearing, advance}
    """
    # Load the font face
    face = freetype.Face(font_path)
    face.set_char_size(font_size * 64)  # FreeType uses 1/64th pixels
    
    # Create packer
    packer = newPacker(rotation=False)
    
    # First pass: collect all valid glyphs and add to packer
    count = 0
    for char_code in range(0, 0x10FFFF):
        character = chr(char_code)
        glyph_index = face.get_char_index(character)
        if glyph_index == 0:
            continue
        
        # Load the glyph to get dimensions
        face.load_char(character)
        glyph = face.glyph
        bitmap = glyph.bitmap
        w, h = max(bitmap.width, 1), max(bitmap.rows, 1)  # Ensure minimum size
        
        packer.add_rect(w, h, rid=character)
        count += 1
    print(f"Added {count} characters to packer")
    
    # Pack all rectangles
    packer.add_bin(atlas_size, atlas_size)  # ADD THIS LINE - tell packer the bin size
    packer.pack()

    
    # Create atlas image
    atlas_image = Image.new('L', (atlas_size, atlas_size), color=0)

    
    # Second pass: render and place glyphs
    characters = {}
    for abin, x, y, w, h, char in packer.rect_list():

        # Render the glyph
        glyph_image, metrics = render_with_freetype(char, face)
        
        # Paste into atlas
        atlas_image.paste(glyph_image, (x, y))
        
        # Store character info
        characters[char] = {
            'uv': (x/atlas_size, y/atlas_size, (x+w)/atlas_size, (y+h)/atlas_size),
            'size': metrics['size'],
            'bearing': metrics['bearing'],
            'advance': metrics['advance']
        }
    
    return atlas_image, characters


def render_text(ctx, texture, characters, text, x, y, window_size):
    """
    Render text using the font atlas.
    
    Args:
        ctx: ModernGL context
        texture: Font atlas texture
        characters: Character metadata dictionary
        text: String to render
        x, y: Position in pixels (top left origin)
        window_size: (width, height) of window
    """
    # Shader program (same as in text_renderer.py)
    vert_shader = """
    #version 330
    in vec2 in_vert;
    in vec2 in_uv;
    uniform vec2 u_resolution;
    out vec2 v_uv;
    void main() {
        vec2 ndc = (in_vert / u_resolution) * 2.0 - 1.0;
        gl_Position = vec4(ndc.x, -ndc.y, 0.0, 1.0);
        v_uv = in_uv;
    }
    """
    
    frag_shader = """
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
    
    prog = ctx.program(vertex_shader=vert_shader, fragment_shader=frag_shader)
    
    # Build vertex data for all characters
    verts = []
    cursor_x = x
    
    for ch in text:
        if ch not in characters:
            continue
        
        char_info = characters[ch]
        u0, v0, u1, v1 = char_info['uv']
        gw, gh = char_info['size']
        ox, oy = char_info['bearing']
        
        # Calculate quad position
        x0 = cursor_x + ox
        y0 = y + oy 
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
        
        cursor_x += char_info['advance']
    
    if not verts:
        return
    
    # Upload vertex data
    verts_array = np.array(verts, dtype='f4')
    vbo = ctx.buffer(verts_array.tobytes())
    vao = ctx.vertex_array(prog, [(vbo, '2f 2f', 'in_vert', 'in_uv')])
    
    # Set uniforms
    prog['u_resolution'].value = window_size
    prog['u_color'].value = (1.0, 1.0, 1.0, 1.0)  # White color
    
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


# Example usage
if __name__ == "__main__":
    # Create context
    ctx = moderngl.create_context(standalone=True)
    
    # Create font atlas
    print("Creating font atlas...")
    atlas_image, characters = create_atlas_with_freetype(
        "vizcore/text/data/cmunbi.ttf",
        font_size=48,
        atlas_size=2048
    )
    
    print(f"Atlas created with {len(characters)} characters")
    
    # Upload to GPU
    atlas_texture = upload_to_gpu(atlas_image, ctx)
    
    # Save atlas for debugging
    atlas_image.save("font_atlas_debug.png")
    print("Atlas saved to font_atlas_debug.png")
    
    # Create framebuffer for rendering
    fbo = ctx.simple_framebuffer((800, 600))
    fbo.use()
    fbo.clear(0.0, 0.0, 0.0, 1.0)
    
    # Render some text
    render_text(
        ctx, 
        atlas_texture, 
        characters, 
        "Hello World!", 
        x=50, 
        y=100, 
        window_size=(800, 600)
    )
    
    # Save result
    from PIL import Image
    data = fbo.read(components=3)
    image = Image.frombytes('RGB', fbo.size, data)
    image = image.transpose(Image.FLIP_TOP_BOTTOM)  # OpenGL is upside down
    image.save("rendered_text.png")
    print("Rendered text saved to rendered_text.png")
    
    # Clean up
    atlas_texture.release()
    fbo.release()
    ctx.release()