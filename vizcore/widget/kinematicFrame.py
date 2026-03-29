from vizcore.meshes.cone import generate_cone
from vizcore.meshes.cylinder import generate_cylinder
from vizcore.utils import rotation_x, rotation_y, translation, perspective, rotation_matrix_from_vectors
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

    with open("vizcore/widget/shaders/dynamic_arrow.vert", "r") as vert_file:
        DYNAMIC_VERT = vert_file.read()
    with open("vizcore/widget/shaders/static_arrow.vert", "r") as vert_file:
        STATIC_VERT = vert_file.read()
    with open("vizcore/widget/shaders/arrow.frag", "r") as frag_file:
        FRAG_SHADER = frag_file.read()

    def __init__(self, ctx, shaft_radius=0.04, shaft_height=0.7,
                 head_radius=0.10, head_height=0.3, segments=32,
                 buffer_size=256, channels=0,
                 text_renderer=None, label_scale=0.003,): # the length of the arrow adds to 1
        self.ctx = ctx

        self._shaft_height = shaft_height
        self._head_height  = head_height
        self._text_renderer = text_renderer
        self._label_scale   = label_scale

        self.arrow_verts, self.arrow_inds = self._build_arrow(
            shaft_radius, shaft_height, head_radius, head_height, segments
        )

        self.channels = channels
        self.signal_names = []
        self._buffer_size = buffer_size
        self.values = {}

    def _build_verts(self):
    
        # Bake each arrow's orientation into its vertices at CPU time
        x_verts = self._transform(self.arrow_verts, self._rot_y(-np.pi / 2))  # +Z → +X
        y_verts = self._transform(self.arrow_verts, self._rot_x( np.pi / 2))  # +Z → +Y
        z_verts = self.arrow_verts.copy()                                       # +Z stays

        if len(self.values) > 0:
            add_verts = {signal: (self.arrow_verts.copy(), np.random.rand(1,3)) for signal in self.values.keys()}
        else:
            add_verts = {}

        # Interleave color per vertex
        x_colored = self._colorize(x_verts, self.RED)    # red
        y_colored = self._colorize(y_verts, self.GREEN)   # green
        z_colored = self._colorize(z_verts, self.BLUE)   # blue
        add_colored = {signal: self._colorize(verts, color) for signal, (verts, color) in add_verts.items()}

        self.colors = {
            "X": self.RED,
            "Y": self.GREEN,
            "Z": self.BLUE,
        }
        self.colors.update({signal: color for signal, (verts, color) in add_verts.items()})

        print(self.colors)
        

        n_x = len(x_verts)
        n_y = len(y_verts)
        n_v = len(add_colored)

        basis_verts = np.concatenate([x_colored, y_colored, z_colored], axis=0)
        basis_inds = np.concatenate([
            self.arrow_inds,
            self.arrow_inds + n_x,
            self.arrow_inds + n_x + n_y
        ], axis=0).astype(np.uint32).ravel()

        basis_vbo = self.ctx.buffer(basis_verts.astype("f4").tobytes())
        basis_ibo = self.ctx.buffer(basis_inds.tobytes())

        signal_verts = np.concatenate(list(add_colored.values()), axis=0)
        signal_inds = np.concatenate([
            self.arrow_inds + (i * len(self.arrow_verts)) for i in range(n_v)
        ], axis=0).astype(np.uint32).ravel()


        signal_vbo = self.ctx.buffer(signal_verts.astype("f4").tobytes())
        signal_ibo = self.ctx.buffer(signal_inds.tobytes())

        # Define programs
        self._static_prog = self.ctx.program(
            vertex_shader=self.STATIC_VERT,
            fragment_shader=self.FRAG_SHADER,
        )

        self._dynamic_prog = self.ctx.program(
            vertex_shader=self.DYNAMIC_VERT,
            fragment_shader=self.FRAG_SHADER,
        )

        self.rotation_matrices = np.tile(np.eye(3, dtype='f4'), (n_v, 1, 1))  # shape (num_instances, 3, 3)
        self.scale_vectors = np.ones((n_v, 3), dtype='f4')  # shape (num_instances, 3)
        # normalize the scale_vectors row wise
        self.scale_vectors = np.linalg.norm(self.scale_vectors, axis=1, keepdims=True) + 1e-8

        print(f"Shape of rotation_matrices: {self.rotation_matrices.shape}, scale_vectors: {self.scale_vectors.shape}")
        
        self.buffers = {
            'rotation': self.ctx.buffer(reserve=self.rotation_matrices.reshape(-1, 9).nbytes),
            'scaling': self.ctx.buffer(reserve=self.scale_vectors.astype('f4').tobytes().__len__()),
        }

        self.update_ctx_buffers()  # initialize rotation and scale buffers

        self._vao_basis = self.ctx.vertex_array(
            self._static_prog,
            [(basis_vbo, "3f 3f", "in_vert", "in_color")],
            index_buffer=basis_ibo,
        )

        self._vao_signal = self.ctx.vertex_array(
            self._dynamic_prog,
            [
                (signal_vbo, "3f 3f", "in_vert", "in_color"),
                (self.buffers['rotation'], "9f/i", "in_rotation"),
                (self.buffers['scaling'], "1f/i", "in_scale"),
            ],
            index_buffer=signal_ibo,
        )

    def update_ctx_buffers(self):
        self.buffers['rotation'].write(self.rotation_matrices.reshape(-1, 9).astype('f4').tobytes())
        self.buffers['scaling'].write(self.scale_vectors.astype('f4').tobytes())

    def attach_signal(self, bus, signal):
        raise NotImplementedError("Buffer streaming not yet implemented for KinematicFrame")
        # self.bus = bus
        if signal not in bus.signals:
            raise ValueError(f"Signal '{signal}' not found in data bus")
        elif signal in self.signal_names:
            pass
        else:
            self.signal_names.append(signal)
            self.buffers.append(CircularBuffer(self.buffer_size))

    def update(self, data=None):
        # Pull latest values from the data bus for each signal
        if hasattr(self, 'signal_names') and hasattr(self, 'data_bus'):
            for i, name in enumerate(self.signal_names):
                value = self.data_bus.latest(name)
                if value is not None:
                    self.buffers[i].push(value)
                # Only update self.values if buffer has valid data
                self.values[i] = np.array(self.buffers[i].history(), dtype='f4')

    def render(self, model: np.ndarray, view: np.ndarray, projection: np.ndarray):
        """
        Draw the frame + axis labels.
        model, view, projection: 4x4 float32 numpy arrays (row-major).
        """
        mvp = projection @ view @ model

        local_z = np.array([0, 0, 1], dtype='f4')  # Arrow points along +Z in local space
        for i, (name, val) in enumerate(self.values.items()):
            val_normalized = val / (np.linalg.norm(val) + 1e-8)
            rot_mat = rotation_matrix_from_vectors(local_z, val_normalized)
            scal = np.linalg.norm(val)  # Magnitude, not normalized direction
            self.scale = scal.astype('f4')
            self.rotation_matrices[i] = rot_mat.astype('f4')

        self.update_ctx_buffers()  # upload any changes to rotation/scale

        self._static_prog["mvp"].write(mvp.astype("f4").T.tobytes())
        self._dynamic_prog["mvp"].write(mvp.astype("f4").T.tobytes())

        self._vao_basis.render(moderngl.TRIANGLES)
        self._vao_signal.render(moderngl.TRIANGLES, instances=len(self.signal_names)) 

        if self._text_renderer is not None:
            # Axis tip positions in world space = model * tip_point
            shaft_h = self._shaft_height
            head_h  = self._head_height
            tip_len = shaft_h + head_h

            def world_tip_dir(local_axis, tip_len, offset=1.1):
                """
                Compute world-space tip position for any vector (not just basis vectors).
                local_axis: direction in local space (e.g., [1,0,0] for X)
                tip_len: arrow length
                offset: multiplier to extend tip past the arrow length
                """
                origin = model[:3, 3]
                # Extract rotation part of model (upper-left 3x3)
                rot = model[:3, :3]
                direction = np.dot(rot, np.array(local_axis, dtype=np.float32))
                norm = np.linalg.norm(direction)
                if norm < 1e-8:
                    direction = np.array([0, 0, 1], dtype=np.float32)
                    norm = 1.0
                direction = direction / norm
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
            
            for signal, val in self.values.items():
                tip = -world_tip_dir(val, tip_len)
                color = self.colors.get(signal, self.YELLOW)
                if isinstance(color, np.ndarray):
                    color = color.flatten()
                self._text_renderer.render_label(signal[0].upper(), tip, view, projection,
                                            color=color,
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
        channels=1,
        text_renderer=None,  # set to TextRenderer instance if you want labels
    )

    frame.signal_names = ["dynamic_signal"]  # example signal name for dynamic arrow

    camera_tilt  = rotation_x(np.radians(25))
    camera_trans = translation(0, -0.3, -3)
    view         = camera_trans @ camera_tilt
    projection   = perspective(np.radians(60), width / height, 0.1, 100)

    mod = rotation_x(np.radians(45)) @ rotation_y(np.radians(30))  # example model transform

    mod = np.eye(4, dtype=np.float32)  # identity model matrix

    vel = np.array([-0.5, 0.5, 0.0], dtype=np.float32)
    a = 0.01  # acceleration magnitude
    frame.values = {"dynamic_signal": vel}  # initialize with zero velocity

    frame._build_verts()  # build geometry and upload to GPU

    anglex = 0.0
    angley = 0.0

    @window.event
    def on_draw():
        global vel, anglex, angley
        ctx.clear(0.1, 0.1, 0.1)

        anglex += 0.01
        angley += 0.015

        mod = rotation_x(anglex) @ rotation_y(angley)

        # frame.values['dynamic_signal'] += np.array([-a,0,a]).astype(np.float32)  # random walk velocity
        # print(f"Current velocity: {frame.values['dynamic_signal']}")

        frame.render(mod, view, projection)

    @window.event
    def on_resize(w, h):
        ctx.viewport = (0, 0, w, h)

    pyglet.app.run()