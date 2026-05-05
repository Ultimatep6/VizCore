import numpy as np
import moderngl
import pyglet
import glm

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


def get_rot_matrix(angle_x=0.0, angle_y=0.0, angle_z=0.0) -> np.ndarray:
    cx, sx = np.cos(angle_x), np.sin(angle_x)
    cy, sy = np.cos(angle_y), np.sin(angle_y)
    cz, sz = np.cos(angle_z), np.sin(angle_z)

    rot_x = np.array(
        [
            [1, 0, 0, 0],
            [0, cx, -sx, 0],
            [0, sx, cx, 0],
            [0, 0, 0, 1],
        ],
        dtype=np.float32,
    )

    rot_y = np.array(
        [
            [cy, 0, sy, 0],
            [0, 1, 0, 0],
            [-sy, 0, cy, 0],
            [0, 0, 0, 1],
        ],
        dtype=np.float32,
    )

    rot_z = np.array(
        [
            [cz, -sz, 0, 0],
            [sz, cz, 0, 0],
            [0, 0, 1, 0],
            [0, 0, 0, 1],
        ],
        dtype=np.float32,
    )

    return rot_z @ rot_y @ rot_x

def get_model_matrix(tx=0, ty=0, tz=0, sx=1,sy=1,sz=1, rx = 0.0, ry = 0.0, rz = 0.0):
    T = get_translation_matrix(tx, ty, tz)
    R = get_rot_matrix(rx, ry, rz)
    S = get_scale_matrix(sx, sy, sz)
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
    # Prevent singularity when looking straight up or down
    if abs(np.dot(f, up)) > 0.999:
        up = np.array([0.0, 0.0, 1.0 if f[1] > 0 else -1.0], dtype=np.float32)
        
    r = normalize(np.cross(f, up))
    u = np.cross(r, f)
    
    # Corrected for row-major matrices (v' = v * M)
    # This is the inverse of the camera's transformation matrix
    view = np.array(
        [
            [r[0], u[0], -f[0], 0],
            [r[1], u[1], -f[1], 0],
            [r[2], u[2], -f[2], 0],
            [-np.dot(r, eye), -np.dot(u, eye), np.dot(f, eye), 1],
        ],
        dtype=np.float32,
    )
    return view


def get_perspective_matrix(fov_y, aspect, near, far):
    f = 1.0 / np.tan(fov_y / 2.0)
    # Transposed for row-major convention
    return np.array(
        [
            [f / aspect, 0, 0, 0],
            [0, f, 0, 0],
            [0, 0, (far + near) / (near - far), -1],
            [0, 0, (2 * far * near) / (near - far), 0],
        ],
        dtype=np.float32,
    )



width, height = 1024, 768
window = pyglet.window.Window(width, height, "Grid Viewer")

ctx = moderngl.create_context(standalone=False)
ctx.enable(moderngl.DEPTH_TEST)
ctx.enable(moderngl.BLEND)
ctx.blend_func = (moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA)
ctx.viewport = (0, 0, width, height)

grid_program = ctx.program(
vertex_shader=
'''
#version 330

out vec3 WorldPos;

const float scale = 1.0; // Increased scale slightly

// Lay the square flat on the XZ plane (y = 0.0)
const vec3 Pos[4] = vec3[4](
    scale*vec3(-1.0, 0.0, -1.0),      // bottom-left
    scale*vec3(1.0, 0.0, -1.0),       // bottom-right
    scale*vec3(1.0, 0.0, 1.0),        // top-right
    scale*vec3(-1.0, 0.0, 1.0)        // top-left
);

const int Indices[6] = int[6](
    0, 3, 1,
    2, 1, 3
);

uniform mat4 gVP;
uniform vec3 gCameraPos;

void main() {
    int idx = Indices[gl_VertexID];
    vec3 vPos3 = Pos[idx];
    
    // Follow the camera along the floor (X and Z)
    vPos3.x += gCameraPos.x;
    vPos3.z += gCameraPos.z;

    vec4 vPos = gVP * vec4(vPos3, 1.0);
    gl_Position = vPos;
    WorldPos = vPos3;
}
'''
                           ,
fragment_shader=
'''
#version 330
in vec3 WorldPos;

layout(location = 0) out vec4 f_color;

uniform float gGridCellSize = 0.025; // Size of each grid cell
uniform vec4 gGridColorThin = vec4(1.0, 1.0, 1.0, 0.2); // Color for thin lines
uniform vec4 gGridColorThick = vec4(1.0, 1.0, 1.0, 0.5); // Color for thick lines

void main() {
    float Lod0a = mod(WorldPos.z, gGridCellSize);

    vec4 Color;
    

    f_color = vec4(1.0,1.0,1.0,1.0);
}
'''
                           )


# defualt view angles
rot_x = rot_y = rot_z = 0.0

# default translation
tx = ty = tz = 0.0

# default scale 
sx=sy=sz=1.0

# Start above the floor (y=3.0) and slightly back (z=3.0) looking down at the origin
camx=0.0
camy=3.0
camz=0.0
eye = np.array([camx,camy,camz], dtype=np.float32)
target = np.array([0.0, 0.0, 0.0], dtype=np.float32)

#default model matrix
view = get_view_matrix(eye, target)
pros = get_perspective_matrix(np.radians(45.0), width / height, 0.1, 100.0)

gvP = pros @ view

grid_vao = ctx.vertex_array(grid_program, [], index_buffer=None)
grid_program['gCameraPos'].write(eye.astype('f4').tobytes('F'))
grid_program['gVP'].write(gvP.astype('f4').tobytes('F'))

@window.event
def on_draw():
    ctx.clear(0.0, 0.0, 0.0, 1.0)
    grid_vao.render(moderngl.TRIANGLES, 6)
    print("Current camera position:", (camx, camy, camz))
    # print("Current target position:", tuple(target))

@window.event
def on_key_press(symbol, modifiers):
    global camx, camy, camz
    if symbol == pyglet.window.key.W:
        camz -= 0.1
    elif symbol == pyglet.window.key.S:
        camz += 0.1
    elif symbol == pyglet.window.key.A:
        camx -= 0.1
    elif symbol == pyglet.window.key.D:
        camx += 0.1
    elif symbol == pyglet.window.key.Q:
        camy += 0.1
    elif symbol == pyglet.window.key.E:
        camy -= 0.1
    view = get_view_matrix(np.array([camx, camy, camz], dtype=np.float32), target)
    gvP = pros @ view
    eye = np.array([camx, camy, camz], dtype=np.float32)

    grid_program['gCameraPos'].write(eye.astype('f4').tobytes('F'))
    grid_program['gVP'].write(gvP.astype('f4').tobytes('F'))

@window.event
def on_mouse_drag(x, y, dx, dy, buttons, modifiers):
    global target
    if buttons & pyglet.window.mouse.LEFT:
        target[0] += dx * 0.01  # Adjust sensitivity as needed
        target[1] -= dy * 0.01  # Adjust sensitivity as needed
        view = get_view_matrix(np.array([camx, camy, camz], dtype=np.float32), target)
        gvP = pros @ view
        grid_program['gVP'].write(gvP.astype('f4').tobytes('F'))

pyglet.app.run()

