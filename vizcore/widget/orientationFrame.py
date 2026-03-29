from vizcore.meshes.cone import generate_cone
from vizcore.meshes.cylinder import generate_cylinder
from vizcore.utils import rotation_x, rotation_y, translation, perspective
import numpy as np
import pyglet
import moderngl


# ─────────────────────────────────────────────
#  OrientationFrame
# ─────────────────────────────────────────────

class OrientationFrame:
    """
    A 3-axis coordinate frame (X=red, Y=green, Z=blue) rendered
    as three orthogonal arrows sharing a single VBO/IBO.

    Usage:
        frame = OrientationFrame(ctx, shaft_radius=0.04, shaft_height=0.6,
                                      head_radius=0.10, head_height=0.2)
        frame.render(mvp)
    """

    VERTEX_SHADER = """
    #version 330

    in vec3 in_vert;
    in vec3 in_color;

    uniform mat4 mvp;

    out vec3 v_color;

    void main() {
        gl_Position = mvp * vec4(in_vert, 1.0);
        v_color = in_color;
    }
    """

    FRAGMENT_SHADER = """
    #version 330

    in vec3 v_color;
    out vec4 f_color;

    void main() {
        f_color = vec4(v_color, 1.0);
    }
    """

    def __init__(self, ctx, shaft_radius=0.04, shaft_height=0.6,
                 head_radius=0.10, head_height=0.2, segments=32):
        self.ctx = ctx

        arrow_verts, arrow_inds = self._build_arrow(
            shaft_radius, shaft_height, head_radius, head_height, segments
        )

        # Bake each arrow's orientation into its vertices at CPU time
        x_verts = self._transform(arrow_verts, self._rot_y(-np.pi / 2))  # +Z → +X
        y_verts = self._transform(arrow_verts, self._rot_x( np.pi / 2))  # +Z → +Y
        z_verts = arrow_verts.copy()                                       # +Z stays

        # Interleave color per vertex
        x_colored = self._colorize(x_verts, [0.9, 0.2, 0.2])    # red
        y_colored = self._colorize(y_verts, [0.2, 0.85, 0.2])   # green
        z_colored = self._colorize(z_verts, [0.2, 0.4, 0.95])   # blue

        n_x = len(x_verts)
        n_y = len(y_verts)

        all_verts = np.concatenate([x_colored, y_colored, z_colored], axis=0)
        all_inds  = np.concatenate([
            arrow_inds,
            arrow_inds + n_x,
            arrow_inds + n_x + n_y,
        ], axis=0).astype(np.uint32).ravel()

        self._prog = ctx.program(
            vertex_shader=self.VERTEX_SHADER,
            fragment_shader=self.FRAGMENT_SHADER,
        )

        vbo = ctx.buffer(all_verts.astype("f4").tobytes())
        ibo = ctx.buffer(all_inds.tobytes())

        # 3f pos + 3f color = 6 floats per vertex
        self._vao = ctx.vertex_array(
            self._prog,
            [(vbo, "3f 3f", "in_vert", "in_color")],
            index_buffer=ibo,
        )

    def render(self, mvp: np.ndarray):
        """
        Draw the frame.
        mvp: 4x4 float32 numpy array (row-major, will be transposed for OpenGL).
        """
        self._prog["mvp"].write(mvp.astype("f4").T.tobytes())
        self._vao.render(moderngl.TRIANGLES)

    # ── private helpers ──────────────────────────────────────────

    @staticmethod
    def _build_arrow(shaft_radius, shaft_height, head_radius, head_height, segments):
        cyl_verts, cyl_inds   = generate_cylinder(shaft_radius, shaft_height, segments)
        cone_verts, cone_inds = generate_cone(head_radius, head_height, segments)

        cone_verts = cone_verts.copy()
        cone_verts[:, 2] += shaft_height   # sit cone on top of cylinder

        offset = len(cyl_verts)
        verts = np.concatenate([cyl_verts, cone_verts], axis=0)
        inds  = np.concatenate([cyl_inds, cone_inds + offset], axis=0)
        return verts, inds

    @staticmethod
    def _transform(verts, matrix):
        ones = np.ones((len(verts), 1), dtype=np.float32)
        h    = np.concatenate([verts, ones], axis=1)
        return (matrix @ h.T).T[:, :3].astype(np.float32)

    @staticmethod
    def _colorize(verts, color):
        colors = np.tile(color, (len(verts), 1)).astype(np.float32)
        return np.concatenate([verts, colors], axis=1)

    @staticmethod
    def _rot_x(a):
        c, s = np.cos(a), np.sin(a)
        return np.array([[1,0,0,0],[0,c,-s,0],[0,s,c,0],[0,0,0,1]], dtype=np.float64)

    @staticmethod
    def _rot_y(a):
        c, s = np.cos(a), np.sin(a)
        return np.array([[c,0,s,0],[0,1,0,0],[-s,0,c,0],[0,0,0,1]], dtype=np.float64)



# ─────────────────────────────────────────────
#  App
# ─────────────────────────────────────────────
if __name__ == "__main__":
    width, height = 800, 600

    window = pyglet.window.Window(width, height, "Orientation Frame")
    window.switch_to()

    ctx = moderngl.create_context()
    ctx.enable(moderngl.DEPTH_TEST)
    ctx.viewport = (0, 0, width, height)

    frame = OrientationFrame(ctx,
        shaft_radius=0.04,
        shaft_height=0.6,
        head_radius=0.10,
        head_height=0.2,
        segments=32,
    )

    camera_tilt  = rotation_x(np.radians(25))
    camera_trans = translation(0, -0.3, -3)
    view         = camera_trans @ camera_tilt
    projection   = perspective(np.radians(60), width / height, 0.1, 100)

    angle_x = 0.0
    angle_y = 0.0

    @window.event
    def on_draw():
        global angle_x, angle_y
        ctx.clear(0.1, 0.1, 0.1)

        angle_y += 0.01
        angle_x += 0.004

        model = rotation_y(angle_y) @ rotation_x(angle_x)
        mvp   = projection @ view @ model

        frame.render(mvp)

    @window.event
    def on_resize(w, h):
        ctx.viewport = (0, 0, w, h)

    pyglet.app.run()