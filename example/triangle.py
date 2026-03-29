import moderngl
from PIL import Image
import numpy as np
import math

ctx = moderngl.create_context(standalone=True)

# Parameters
n_triangles = 4
L = 0.5
y = 0.5
scale = 0.2
c = L * np.sqrt(3)
dANGLE = np.deg2rad(60)
s = math.sqrt(2)

# ----------------------------
# 1. Vertex coordinates for a single triangle
# ----------------------------
triangle_verts = np.array([
    [-L, -y],   # adjust y as needed
    [ L, -1.0],
    [ 0.0, c]
], dtype='f4')

# Normalize each row
triangle_verts /= np.linalg.norm(triangle_verts, axis=1, keepdims=True)
triangle_verts *= scale  # scale to desired size
print(triangle_verts)



# Repeat for n_triangles (flattened for all vertices)
vbo_verts = np.tile(triangle_verts, (n_triangles, 1))  # shape = (n_triangles*3, 2)

# ----------------------------
# 2. Colors per triangle (normalized 0–1)
# ----------------------------
vbo_colors = np.zeros((n_triangles*3, 3), dtype='f4')
vbo_colors[0:3, :] = 1.0  # center triangle white
for i in range(1, n_triangles):
    color = np.random.rand(3)  # 0–1
    vbo_colors[i*3:(i+1)*3, :] = color

# ----------------------------
# 3. Translation vectors per triangle
# ----------------------------
translations = np.zeros((n_triangles, 2), dtype='f4')
translations[0, :] = [0.0, 0.0]  # center
radius = 2 * L * np.sin(np.deg2rad(30))
for i in range(1, n_triangles):
    angle = (i - 1) * dANGLE*2
    translations[i, :] = [-radius * np.sin(angle), radius * np.cos(angle)]
print(translations)

# Repeat translations for each vertex in the triangle
vbo_translate = np.repeat(translations, 3, axis=0)  # shape = (n_triangles*3, 2)

# ----------------------------
# 4. Rotation matrices per triangle (2x2)
# ----------------------------
def rot2d_matrix(theta):
    return np.array([[np.cos(theta), -np.sin(theta)],
                     [np.sin(theta),  np.cos(theta)]], dtype='f4')

vbo_rot = np.zeros((n_triangles*3, 4), dtype='f4')  # flattened 2x2 matrix
rotation_angles = [0, dANGLE, 2*dANGLE, 3*dANGLE]  # example angles
for i in range(n_triangles):
    rot_mat = rot2d_matrix(rotation_angles[i])
    vbo_rot[i*3:(i+1)*3, :] = np.tile(rot_mat.flatten(), (3, 1))

# ----------------------------
# 5. Create buffers
# ----------------------------
vbo_verts = ctx.buffer(vbo_verts.tobytes())
vbo_colors = ctx.buffer(vbo_colors.tobytes())
vbo_translate = ctx.buffer(vbo_translate.tobytes())
vbo_rot = ctx.buffer(vbo_rot.tobytes())

# ----------------------------
# 6. Shader program
# ----------------------------
shader_program = ctx.program(
    vertex_shader="""
    #version 330
    in vec2 in_vert;
    in vec3 in_color;
    in vec2 translate;
    in mat2 vert_rotate;

    out vec3 out_color;

    void main() {
        out_color = in_color;
        vec2 point = vert_rotate * in_vert + translate;
        gl_Position = vec4(point, 0.0, 1.0);
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

# ----------------------------
# 7. VAO setup
# ----------------------------
vao = ctx.vertex_array(
    shader_program,
    [
        (vbo_verts, "2f", "in_vert"),
        (vbo_colors, "3f", "in_color"),
        (vbo_translate, "2f", "translate"),
        (vbo_rot, "4f", "vert_rotate"),
    ]
)

# ----------------------------
# 8. Render to framebuffer
# ----------------------------
fbo = ctx.simple_framebuffer((512, 512))
fbo.use()
fbo.clear(0.0, 0.0, 0.0, 1.0)
vao.render(mode=moderngl.TRIANGLES)

# Read to CPU and display
img = Image.frombytes('RGB', fbo.size, fbo.read(), 'raw', 'RGB', 0, -1)
img.show()