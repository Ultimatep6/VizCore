from vizcore.meshes.cone import generate_cone
from vizcore.meshes.cylinder import generate_cylinder
from vizcore.utils import rotation_x, rotation_y, rotation_z, rotation_matrix_from_vectors
from vizcore.bus.ring_buffer import RingBuffer
from vizcore.widget.baseWidget import BaseWidget

import numpy as np
# import pyglet
# import moderngl


# ─────────────────────────────────────────────
#  KinematicFrame
# ─────────────────────────────────────────────

class KinematicFrame(BaseWidget):
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

    def __init__(self, shaft_radius=0.04, shaft_height=0.7,
                 head_radius=0.10, head_height=0.3, segments=32,
                 label_scale=0.003,buffer_size=256, channels=0,
                 margin=0.1, title="",
                 text_renderer=None, renderer=None): # the length of the arrow adds to 1
        
        super().__init__()  # Initialize BaseWidget
        self.channels = channels
        self._default_buffer_size = buffer_size
        # The names of the signals attached to this frame, in order of their corresponding dynamic arrows
       
        self._vbos = {}
        self._local = {}  # Store latest local data for each signal (e.g., rotation + scale for dynamic arrows)
        self.signal_names = []  # Name of signals, strictly for dynamic arrows and for vector inputs.

        # Visual parameters
        self.margin = margin
        self.title = title

        # Geometry parameters
        self._shaft_height = shaft_height
        self._head_height  = head_height
        self._label_scale   = label_scale

        self.arrows = self.channels + 3  # total arrows = basis (3) + dynamic (channels)

        self.arrow_verts, self.arrow_inds = self._build_arrow(
            shaft_radius, shaft_height, head_radius, head_height, segments
        )

        self._text_renderer = text_renderer
        self._renderer = renderer
        self.values = {}
    
    def load_shaders(self, shader_manager):
        shader_manager.load_shader(
            "dynamic_arrow",
            vertex_path="vizcore/widget/shaders/dynamic_arrow.vert",
            fragment_path="vizcore/widget/shaders/arrow.frag"
        )
        shader_manager.load_shader(
            "static_arrow",
            vertex_path="vizcore/widget/shaders/static_arrow.vert",
            fragment_path="vizcore/widget/shaders/arrow.frag"
        )
    
    
    def accepts_signal(self, data_bus, signal_name):
        # Kinematic frame only accepts 3D signals
        latest_val = data_bus.latest(signal_name)
        if latest_val is not None:
            arr_val = np.asarray(latest_val)
            if arr_val.shape == (3,):
                return True
        return False

    def update(self):
        # Pull latest values from the data bus for each signal and update both local and GPU buffer in one pass
        if hasattr(self, 'signal_names') and hasattr(self, 'data_bus'):
            transforms = []
            local_z = np.array([0, 0, 1], dtype='f4')
            
            for i, signalName in enumerate(self.signal_names):
                value = self.data_bus.latest(signalName)
                if value is not None:
                    latest = np.asarray(value, dtype='f4')
                    self._local[signalName].push(latest)
                else:
                    latest = np.zeros(3, dtype='f4')
                    self._local[signalName].push(latest)
                idx = self.signal_to_index[signalName]
                self.signal_buffer[idx] = latest  # Update the correct row directly
                
                # Calculate the transform matrix for this signal instance
                mag = np.float32(np.linalg.norm(latest))
                rot_mat = np.eye(3, dtype='f4')
                if mag > 1e-8:
                    val_normalized = latest / mag
                    rot_mat = rotation_matrix_from_vectors(local_z, val_normalized).astype('f4')
                
                # GLSL mat3 expects column-major order (transpose before flatten)
                rot_flat = rot_mat.T.flatten()
                instance_entry = np.concatenate([rot_flat, [mag]], dtype='f4')
                transforms.append(instance_entry)
                
            # Write the entire buffer to the GPU once
            self._vbos['externalSignals'].write(self.signal_buffer.tobytes())
            if transforms:
                self._vbos['signalTransforms'].write(np.concatenate(transforms).tobytes())

        angles = []
        for angleName in ['eulerian_x', 'eulerian_y', 'eulerian_z']:
            angle = self.data_bus.latest(angleName)
            if angle is not None:
                self._local[angleName].push(angle)
            else:
                raise ValueError(f"Missing data for Euler angle '{angleName}'. Ensure the data bus is providing this signal.")
            angles.append(self._local[angleName].latest())
        self.eulerian_buffer[:] = angles
        self._vbos['eulerian_angles'].write(self.eulerian_buffer.tobytes())
                
                
    def bind_external_signal(self, data_bus, signal:list):
        """
        Bind the signal name and the size of its data to the local storage of the widget. 
        """
        if hasattr(self, 'signal_names'):
            for sig in signal:
                if sig not in self.signal_names:
                    self._local[sig] = RingBuffer(3)  # Create local buffer for this signal (x,y,z)
                    self.signal_names.append(sig)  # Add signal name to list of attached signals
                    
                    if not hasattr(self, 'signal_to_index'):
                        self.signal_to_index = {}
                    
                    self.signal_to_index[sig] = len(self.signal_names) - 1  # Map signal name to its index in the buffer
                
                else:
                    self._local[sig] = RingBuffer(3)  # Create local buffer for this signal (x,y,z), overwriting existing buffer
        else:
            raise AttributeError("Widget does not have 'signal_names' attribute. Ensure the widget is initialized with a list to store signal names.")
        
        # Initialize Euler angle buffers
        for angleName in ['eulerian_x', 'eulerian_y', 'eulerian_z']:
            if angleName not in self._local:
                self._local[angleName] = RingBuffer(1)
        
        self.data_bus = data_bus

        # Re-bind renderer if it was already bound to update VBO allocations
        if hasattr(self, '_renderer') and self._renderer is not None:
            self.bind_renderer(self._renderer)

    def bind_renderer(self, renderer):
        """Binds all the external signals to the renderer and pre-allocates GPU buffers."""
        self._renderer = renderer
        self._text_renderer = getattr(renderer, 'text_renderer', None)
        self.signal_to_index = {sig: i for i, sig in enumerate(self.signal_names)}
        
        # Build static geometry buffers immediately when renderer is attached
        self._build_verts()
        
        # Pre-allocate buffer based on self.channels if external signals are not yet bound
        num_signals = max(self.channels, len(self.signal_names))
        
        self.signal_buffer = np.zeros((num_signals, 3), dtype='f4')
        buffer_size = self.signal_buffer.nbytes if self.signal_buffer.nbytes > 0 else 12
        self._vbos['externalSignals'] = renderer.ctx.buffer(reserve=buffer_size)
        if self.signal_buffer.nbytes > 0:
            self._vbos['externalSignals'].write(self.signal_buffer.tobytes())
            
        # Per-instance matrix buffer (10 floats per dynamic arrow: 9 for mat3, 1 for float)
        transform_size = num_signals * 10 * 4 # 10 floats * 4 bytes
        self._vbos['signalTransforms'] = renderer.ctx.buffer(reserve=max(transform_size, 40))

        self.eulerian_buffer = np.zeros(3, dtype='f4')
        buffer_size = self.eulerian_buffer.nbytes if self.eulerian_buffer.nbytes > 0 else 12
        self._vbos['eulerian_angles'] = renderer.ctx.buffer(reserve=buffer_size)
        if self.eulerian_buffer.nbytes > 0:
            self._vbos['eulerian_angles'].write(self.eulerian_buffer.tobytes())

        self.load_shaders(renderer.shader_manager)

    def bind_camera(self, camera):
        self.camera = camera

    # Need to add camera class for the different things
    def draw(self, renderer=None):
        """
        Draw the frame + axis labels.
        model, view, projection: 4x4 float32 numpy arrays (row-major).
        """
        x,y,z = self._local['eulerian_x'].latest(), self._local['eulerian_y'].latest(), self._local['eulerian_z'].latest()
        model = rotation_z(z) @ rotation_y(y) @ rotation_x(x)  # Apply rotations in ZYX order (yaw, pitch, roll) --- CONVENTION
        mvp = self.camera.projection @ self.camera.view @ model

        packed_mvp = mvp.astype('f4').T.tobytes()
        renderer.set_uniform("static_arrow", "mvp", packed_mvp)
        renderer.set_uniform("dynamic_arrow", "mvp", packed_mvp)

        renderer.draw("static_arrow", [(self._vbos["basisVerts"], "3f 3f", "in_vert", "in_color")], self._vbos["basisIdx"])  # Ensure static shader is compiled before creating VAO
        
        # Only draw dynamic arrows if we actually created the VBOs
        if "signalVerts" in self._vbos and "signalIdx" in self._vbos and len(self.signal_names) > 0:
            content = [
                (self._vbos["signalVerts"], "3f 3f", "in_vert", "in_color"),
                (self._vbos["signalTransforms"], "9f 1f /i", "in_rotation", "in_scale")
            ]
            # Draw shared dynamic geometry N times via instancing
            renderer.draw("dynamic_arrow", content, self._vbos["signalIdx"], instances=len(self.signal_names))

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
            
            view, projection = self.camera.view, self.camera.projection

            self._text_renderer.render_label("X", x_tip, view, projection,
                                            color=self.RED,
                                            scale=self._label_scale)
            self._text_renderer.render_label("Y", y_tip, view, projection,
                                            color=self.BLUE,
                                            scale=self._label_scale)
            self._text_renderer.render_label("Z", z_tip, view, projection,
                                            color=self.GREEN,
                                            scale=self._label_scale)
            
            for signal in self.signal_names:
                val = self._local[signal].latest()
                tip = world_tip_dir(val, tip_len)
                color = self.colors.get(signal, self.YELLOW)
                if isinstance(color, np.ndarray):
                    color = color.flatten()
                self._text_renderer.render_label(signal[0].upper(), tip, view, projection,
                                            color=color,
                                            scale=self._label_scale)

    def _build_verts(self):
    
        # Bake each arrow's orientation into its vertices at CPU time
        x_verts = self._transform(self.arrow_verts, rotation_y(-np.pi / 2))  # +Z → +X
        y_verts = self._transform(self.arrow_verts, rotation_x( np.pi / 2))  # +Z → +Y
        z_verts = self.arrow_verts.copy()                                       # +Z stays

        # Use signal_names (the names of bound signals) as the source of truth for extra arrows
        if len(self.signal_names) > 0:
            add_verts = {signal: (self.arrow_verts.copy(), self.YELLOW) for signal in self.signal_names}
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
        
        n_x = len(x_verts)
        n_y = len(y_verts)
        n_v = len(add_colored)

        basis_verts = np.concatenate([x_colored, y_colored, z_colored], axis=0)
        basis_inds = np.concatenate([
            self.arrow_inds,
            self.arrow_inds + n_x,
            self.arrow_inds + n_x + n_y
        ], axis=0).astype(np.uint32).ravel()

        # Static buffers for basis arrows (X,Y,Z) -- They won't change, so we can upload once and reuse
        if self._renderer is not None:
            self._vbos['basisVerts'] = self._renderer.ctx.buffer(basis_verts.tobytes())
            self._vbos['basisIdx'] = self._renderer.ctx.buffer(basis_inds.tobytes())
        else:
            self._vbos['basisVerts'] = basis_verts
            self._vbos['basisIdx'] = basis_inds
        
        if len(add_colored) > 0:
            signal_verts = np.concatenate(list(add_colored.values()), axis=0)
            signal_inds = np.concatenate([
                self.arrow_inds + (i * len(self.arrow_verts)) for i in range(n_v)
            ], axis=0).astype(np.uint32).ravel()
        else:
            signal_verts = np.zeros((0, 6), dtype='f4')
            signal_inds = np.zeros(0, dtype='u4')

        # Static buffers for dynamic arrows -- The vertex data (geometry + color) is static, but the instance data (rotation + scale) will be updated each frame
        if self._renderer is not None:
            self._vbos["signalVerts"] = self._renderer.ctx.buffer(reserve=max(signal_verts.nbytes, 12))
            if signal_verts.nbytes > 0:
                self._vbos["signalVerts"].write(signal_verts.tobytes())
            
            self._vbos["signalIdx"] = self._renderer.ctx.buffer(reserve=max(signal_inds.nbytes, 12))
            if signal_inds.nbytes > 0:
                self._vbos["signalIdx"].write(signal_inds.tobytes())
        else:
            self._vbos["signalVerts"] = signal_verts
            self._vbos["signalIdx"] = signal_inds
        


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
