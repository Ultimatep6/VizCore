from vizcore.meshes.cone import generate_cone
from vizcore.meshes.cylinder import generate_cylinder
from vizcore.utils import rotation_x, rotation_y, translation, perspective
import numpy as np
import pyglet
import moderngl


# ─────────────────────────────────────────────
#  KinematicFrame
# ─────────────────────────────────────────────

class KinematicFrame:
    RED = [0.9, 0.2, 0.2]
    GREEN = [0.2, 0.85, 0.2]
    BLUE = [0.2, 0.4, 0.95]
    YELLOW = [0.95, 0.95, 0.2]

    """
    A 3-axis coordinate frame (X=red, Y=green, Z=blue) rendered
    as three orthogonal arrows sharing a single VBO/IBO.

    Usage:
        frame = KinematicFrame(ctx, shaft_radius=0.04, shaft_height=0.6,
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

    def __init__(self, ctx, shaft_radius=0.04, shaft_height=0.7,
                 head_radius=0.10, head_height=0.3, segments=32,
                 text_renderer=None, label_scale=0.003,
                 velocity=True): # the length of the arrow adds to 1
        self.ctx = ctx

        self._shaft_height = shaft_height
        self._head_height  = head_height
        self._text_renderer = text_renderer
        self._label_scale   = label_scale

        arrow_verts, arrow_inds = self._build_arrow(
            shaft_radius, shaft_height, head_radius, head_height, segments
        )

        # Bake each arrow's orientation into its vertices at CPU time
        x_verts = self._transform(arrow_verts, self._rot_y(-np.pi / 2))  # +Z → +X
        y_verts = self._transform(arrow_verts, self._rot_x( np.pi / 2))  # +Z → +Y
        z_verts = arrow_verts.copy()                                       # +Z stays

        if velocity and 
            velocity_verts = arrow_verts.copy()

        # Interleave color per vertex
        x_colored = self._colorize(x_verts, self.RED)    # red
        y_colored = self._colorize(y_verts, self.GREEN)   # green
        z_colored = self._colorize(z_verts, self.BLUE)   # blue
        velocity_verts = self._colorize(velocity_verts, self.YELLOW)   # yellow

        n_x = len(x_verts)
        n_y = len(y_verts)
        n_v = len(velocity_verts)

        all_verts = np.concatenate([x_colored, y_colored, z_colored], axis=0)
        all_verts = np.concatenate([all_verts, velocity_verts], axis=0) if velocity else all_verts
        all_inds  = np.concatenate([
            arrow_inds,
            arrow_inds + n_x,
            arrow_inds + n_x + n_y,
            arrow_inds + n_x + n_y + n_v if velocity else np.array([], dtype=np.uint32)
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

    def attach_buffer_stream(self, buffer, stream):
        raise NotImplementedError("Buffer streaming not yet implemented for KinematicFrame")

    def render(self, model: np.ndarray, view: np.ndarray, projection: np.ndarray):
        """
        Draw the frame + axis labels.
        model, view, projection: 4x4 float32 numpy arrays (row-major).
        """
        mvp = projection @ view @ model
        self._prog["mvp"].write(mvp.astype("f4").T.tobytes())
        self._vao.render(moderngl.TRIANGLES)

        if self._text_renderer is not None:
            # Axis tip positions in world space = model * tip_point
            shaft_h = self._shaft_height
            head_h  = self._head_height
            tip_len = shaft_h + head_h

            def world_tip_dir(local_axis, tip_len, offset=1.1, scale=1.0):
                """
                Compute world-space arrow tip position using direction vector.
                
                local_axis: [1,0,0] for X, [0,1,0] for Y, [0,0,1] for Z
                tip_len: self._shaft_height + self._head_height
                offset: 1.1 = 10% past tip to avoid overlap
                """
                # 1. Frame origin (pure translation)
                origin = model[:3, 3]
                
                # 2. World-space axis direction (pure rotation, w=0)
                axis_local = np.array([*local_axis, 0.0], dtype=np.float32)
                axis_world = model @ axis_local
                direction = axis_world[:3] / (np.linalg.norm(axis_world[:3]) + 1e-8)
                
                # 3. Tip position = origin + direction * distance
                return origin + direction * tip_len * offset


            # Option 2: Robust direction-based (replace world_tip entirely)
            x_tip = world_tip_dir([-1,0,0], tip_len)
            z_tip = world_tip_dir([0,-1,0], tip_len)
            y_tip = world_tip_dir([0,0,1], tip_len)

            self._text_renderer.render_label("X", x_tip, view, projection,
                                            color=self.RED,
                                            scale=self._label_scale)
            self._text_renderer.render_label("Y", y_tip, view, projection,
                                            color=self.BLUE,
                                            scale=self._label_scale)
            self._text_renderer.render_label("Z", z_tip, view, projection,
                                            color=self.GREEN,
                                            scale=self._label_scale)


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

    frame = KinematicFrame(ctx,
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