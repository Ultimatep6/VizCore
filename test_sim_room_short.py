import numpy as np
import moderngl
import pyglet


def get_translation_matrix(tx=0, ty=0, tz=0) -> np.ndarray:
    return np.array(
        [
            [1, 0, 0, 0],
            [0, 1, 0, 0],
            [0, 0, 1, 0],
            [tx, ty, tz, 1],
        ],
        dtype=np.float32,
    )


def get_scale_matrix(sx=1, sy=1, sz=1) -> np.ndarray:
    return np.array(
        [
            [sx, 0, 0, 0],
            [0, sy, 0, 0],
            [0, 0, sz, 0],
            [0, 0, 0, 1],
        ],
        dtype=np.float32,
    )


def get_rot_matrix(angle=0.0) -> np.ndarray:
    c, s = np.cos(angle), np.sin(angle)
    return np.array(
        [
            [c, 0, s, 0],
            [0, 1, 0, 0],
            [-s, 0, c, 0],
            [0, 0, 0, 1],
        ],
        dtype=np.float32,
    )


def get_model_matrix(tx=0, ty=0, tz=0, scale=1, angle=0.0):
    T = get_translation_matrix(tx, ty, tz)
    R = get_rot_matrix(angle)
    S = get_scale_matrix(scale, scale, scale)
    return T @ R @ S


def normalize(v):
    return v / np.linalg.norm(v) if np.linalg.norm(v) > 1e-8 else v


def normalize_mesh_vertices(vertices: np.ndarray) -> np.ndarray:
    if len(vertices) == 0:
        return vertices

    min_corner = vertices.min(axis=0)
    max_corner = vertices.max(axis=0)
    center = (min_corner + max_corner) * 0.5
    extents = max_corner - min_corner
    max_extent = float(np.max(extents))

    if max_extent <= 1e-8:
        return vertices - center

    # Fit largest side to length 2.0 => model roughly inside [-1, 1]
    scale = 2.0 / max_extent
    return (vertices - center) * scale


def get_view_matrix(eye, target, up=np.array([0, 1, 0], dtype=np.float32)):
    f = normalize(target - eye)
    r = normalize(np.cross(f, up))
    u = np.cross(r, f)
    view = np.array(
        [
            [r[0], u[0], -f[0], -np.dot(r, eye)],
            [r[1], u[1], -f[1], -np.dot(u, eye)],
            [r[2], u[2], -f[2], np.dot(f, eye)],
            [0, 0, 0, 1],
        ],
        dtype=np.float32,
    )
    return view


def get_perspective_matrix(fov_y, aspect, near, far):
    f = 1.0 / np.tan(fov_y / 2.0)
    return np.array(
        [
            [f / aspect, 0, 0, 0],
            [0, f, 0, 0],
            [0, 0, (far + near) / (near - far), (2 * far * near) / (near - far)],
            [0, 0, -1, 0],
        ],
        dtype=np.float32,
    )


width, height = 1024, 768
window = pyglet.window.Window(width, height, "Grid Viewer")

ctx = moderngl.create_context()
ctx.enable(moderngl.DEPTH_TEST)
ctx.enable(moderngl.BLEND)
ctx.blend_func = (moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA)
ctx.viewport = (0, 0, width, height)

# Load shaders
with open("vizcore/widget/shaders/grid.vert", "r") as f:
    grid_vert_src = f.read()
with open("vizcore/widget/shaders/grid.frag", "r") as f:
    grid_frag_src = f.read()

grid_program = ctx.program(vertex_shader=grid_vert_src, fragment_shader=grid_frag_src)

grid_quad = np.array(
    [
        -1.0, -1.0,
         1.0, -1.0,
        -1.0,  1.0,
         1.0, -1.0,
         1.0,  1.0,
        -1.0,  1.0,
    ],
    dtype="f4",
)
grid_vbo = ctx.buffer(grid_quad.tobytes())
grid_vao = ctx.vertex_array(grid_program, [(grid_vbo, "2f", "in_pos")])

# Camera setup for clear grid visibility (not edge-on)
eye = np.array([5, 3, 5], dtype=np.float32)
target = np.array([0, 0, 0], dtype=np.float32)
view = get_view_matrix(eye, target)
proj = get_perspective_matrix(
    fov_y=np.radians(80), aspect=width / height, near=0.01, far=1000.0
)


@window.event
def on_resize(w, h):
    global proj
    ctx.viewport = (0, 0, w, h)
    proj = get_perspective_matrix(
        fov_y=np.radians(60),
        aspect=w / h,
        near=0.1,
        far=100.0,
    )

    grid_program["u_proj_mat"].write(proj.T.tobytes())


@window.event
def on_draw():
    ctx.clear(0.1, 0.1, 0.1, 1.0)

    grid_program["u_view_mat"].write(view.T.tobytes())
    grid_program["u_proj_mat"].write(proj.T.tobytes())
    grid_program["u_camera_pos"].value = tuple(float(v) for v in eye)
    grid_vao.render(moderngl.TRIANGLES)


pyglet.app.run()