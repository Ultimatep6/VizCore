import moderngl
from PIL import Image
import numpy as np
import math

ctx = moderngl.create_context(standalone=True)
# Parameters
L = 1.0

vert1 = np.array([0.0,L], dtype='f4')  # Bottom-left vertex


triangle_verts = np.array([
    [-L / 2, -y],   # Bottom-left vertex
    [ L / 2, -y],   # Bottom-right vertex
    [ 0.0, y]       # Top vertex (adjusted for equilateral height)
], dtype='f4')

triangle_verts *= scale  # scale to desired size

# # Calculate distance between triangle verts and assert
# for i in range(len(triangle_verts)):
#     for j in range(i + 1, len(triangle_verts)):
#         dist = np.linalg.norm(triangle_verts[i] - triangle_verts[j])
#         print(f"Distance between vert {i} and vert {j}: {dist}")
#         assert np.isclose(dist, s * scale), f"Distance between verts should be {s * scale}, got {dist}"


color = np.random.rand(3)  # 0–1
print(color)



shader_program = ctx.program(
    vertex_shader="""
    #version 330
    in vec2 in_vert;
    in vec3 in_color;
    
    out vec3 out_color;

    void main() {
        out_color = in_color;
        gl_Position = vec4(in_vert, 0.0, 1.0);
    }
    """,
    fragment_shader="""
    #version 330
    in vec3 out_color;
    out vec4 f_color;
    void main() {
        f_color = vec4(out_color, 1.0);
    }
    """
    
)

vbo_verts = ctx.buffer(triangle_verts.tobytes())
vbo_colors = ctx.buffer(color.tobytes())

# Prepare per-instance color buffer
instance_colors = np.random.rand(n_triangles, 3).astype('f4')
vbo_instance_colors = ctx.buffer(instance_colors.tobytes())

# ----------------------------
# 7. VAO setup
# ----------------------------
vao = ctx.vertex_array(
    shader_program,
    [
        (vbo_verts, "2f", "in_vert"),
        (vbo_instance_colors, "3f/i", "in_color"),
    ]  # Per-instance color
)

# Render with instancing
fbo = ctx.simple_framebuffer((512, 512))
fbo.use()
fbo.clear(0.0, 0.0, 0.0, 1.0)
vao.render(mode=moderngl.TRIANGLES, instances=n_triangles)

# Display the result
img = Image.frombytes('RGB', fbo.size, fbo.read(), 'raw', 'RGB', 0, -1)
img.show()
