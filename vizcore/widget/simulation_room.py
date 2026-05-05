"""Simulation room widget for displaying 3D models and scene."""

import numpy as np
import moderngl
from vizcore.widget.baseWidget import BaseWidget
from vizcore.renderer.camera import Camera
from vizcore.meshes import MeshRegistry
from vizcore.utils import rotation_x, rotation_y, rotation_z, combine_meshes
from vizcore.bus.data_bus import DataBus


class SimulationRoom(BaseWidget):
    """
    A 3D scene widget for visualizing models and simulation data.

    Features:
        - Displays a 3D grid (optional)
        - Displays world axes (X, Y, Z) at origin
        - Supports loading and displaying 3D models via mesh registry
        - Basic camera controls (orbit, zoom, pan)
        - Can bind signals to control object transforms
    """

    def __init__(self, show_grid=True, show_axes=True, **kwargs):
        super().__init__(**kwargs)
        self.show_grid = show_grid
        self.show_axes = show_axes

        # Camera for the 3D scene
        self.camera = None

        # Grid and axes mesh data (will be generated in bind_renderer)
        self.grid_mesh = None
        self.axes_meshes = {}  # {'X': mesh_data, 'Y': ..., 'Z': ...}

        # Objects in the scene: name -> {'mesh': mesh_data, 'position': vec3, 'rotation': vec3, 'color': vec3, 'scale': vec3}
        self.objects = {}

        # Mouse state for camera control (matches simple_viewer pattern)
        self.mouse_dx = 0
        self.mouse_dy = 0
        self.mouse_scroll = 0
        self._orbit_angle_y = 0.0  # yaw
        self._orbit_angle_x = 0.2  # pitch (slight tilt like simple_viewer)
        self._camera_distance = 5.0
        self._tile_index = None  # Will be set when bound to a tile

    @property
    def required_shape(self):
        # This widget doesn't require any specific signal by default
        # It can be extended to accept signals for object transforms
        return None

    def bind_renderer(self, renderer):
        """Set up the renderer and create meshes for grid and axes."""
        super().bind_renderer(renderer)
        # Get width and height from the application window via the renderer
        width, height = self._renderer.application.window.width, self._renderer.application.window.height
        self.camera = Camera(width, height)

        # Load shaders for this widget
        self.load_shaders(renderer.shader_manager)

        # Create grid mesh (if enabled)
        if self.show_grid:
            self.grid_mesh = self._create_grid_mesh(size=10, spacing=1)

        # Create axes meshes (if enabled)
        if self.show_axes:
            self.axes_meshes = self._create_axes_meshes()

    def load_shaders(self, shader_manager):
        """Load and compile shaders for the simulation room.
        We use the same static_arrow shader as the KinematicFrame for drawing meshes.
        """
        shader_manager.load_shader(
            "static_arrow",
            vertex_path="vizcore/widget/shaders/static_arrow.vert",
            fragment_path="vizcore/widget/shaders/arrow.frag"
        )

    def bind_camera(self, camera):
        """This widget manages its own camera, so we ignore the passed camera."""
        # We could use the passed camera to set initial state, but for now we create our own
        pass

    def _create_grid_mesh(self, size=10, spacing=1):
        """Create a simple grid mesh in the XZ plane."""
        vertices = []
        indices = []
        vertex_index = 0

        # Lines along X axis
        for z in range(-size, size + 1, spacing):
            vertices.extend([
                [-size, 0, z],  # start
                [size, 0, z]    # end
            ])
            indices.extend([
                [vertex_index, vertex_index + 1]
            ])
            vertex_index += 2

        # Lines along Z axis
        for x in range(-size, size + 1, spacing):
            vertices.extend([
                [x, 0, -size],  # start
                [x, 0, size]    # end
            ])
            indices.extend([
                [vertex_index, vertex_index + 1]
            ])
            vertex_index += 2

        return {
            'vertices': np.array(vertices, dtype=np.float32),
            'indices': np.array(indices, dtype=np.uint32)
        }

    def _create_axes_meshes(self):
        """Create arrow meshes for X, Y, Z axes."""
        # Get the base arrow mesh (points along +Z)
        base_arrow = MeshRegistry.get_mesh('arrow')
        if base_arrow['vertices'].size == 0:
            return {}

        axes = {}
        # X axis: red, rotate +90 around Y to point from -Z to +X? Wait, we want +X.
        # Our arrow points along +Z. To point along +X, we rotate -90 around Y (or +90 around Y depending on coordinate system).
        # Let's define: 
        #   +X: right
        #   +Y: up
        #   +Z: forward (out of screen towards viewer? Actually in OpenGL, camera looks down -Z by default? 
        #   We'll need to be consistent with our camera.

        # For simplicity, we'll assume:
        #   The arrow mesh points along +Z in its local space.
        #   To point along +X: rotate 90 degrees around Y (so +Z goes to +X)
        #   To point along +Y: rotate -90 degrees around X (so +Z goes to +Y)
        #   To point along +Z: no rotation

        # X axis (red)
        axes['X'] = {
            'mesh': base_arrow,
            'rotation': rotation_y(np.radians(90)),  # +90 around Y
            'color': np.array([0.9, 0.2, 0.2], dtype=np.float32)  # RED
        }
        # Y axis (green)
        axes['Y'] = {
            'mesh': base_arrow,
            'rotation': rotation_x(np.radians(-90)),  # -90 around X
            'color': np.array([0.2, 0.85, 0.2], dtype=np.float32)  # GREEN
        }
        # Z axis (blue)
        axes['Z'] = {
            'mesh': base_arrow,
            'rotation': np.eye(4, dtype=np.float32),  # no rotation
            'color': np.array([0.2, 0.4, 0.95], dtype=np.float32)  # BLUE
        }

        return axes

    def update(self):
        """Update camera based on mouse input (matches simple_viewer pattern)."""
        if not self._renderer:
            return
        
        # Get the VizCore window (same pattern as simple_viewer)
        viz_window = self._renderer.application
        
        # Check if mouse is over this widget's tile
        mouse_x = getattr(viz_window, 'mouse_x', 0)
        mouse_y = getattr(viz_window, 'mouse_y', 0)
        
        # Check if mouse is over our tile
        tile_x = getattr(self, '_tile_x', None)
        if tile_x is None:
            print("DEBUG: No tile bound")
            return  # Not bound to a tile yet
            
        # Check if mouse is within tile bounds
        if not (tile_x <= mouse_x <= tile_x + self._tile_width and 
                self._tile_y <= mouse_y <= self._tile_y + self._tile_height):
            print(f"DEBUG: Mouse not over tile. mouse=({mouse_x}, {mouse_y}), tile=({tile_x}, {self._tile_y}, {self._tile_width}, {self._tile_height})")
            return  # Mouse not over this widget
        
        # Handle left mouse drag for orbit
        mouse_left = getattr(viz_window, 'mouse_left_pressed', False)
        mouse_dx = getattr(viz_window, 'mouse_dx', 0)
        mouse_dy = getattr(viz_window, 'mouse_dy', 0)
        
        print(f"DEBUG: mouse_left={mouse_left}, mouse_dx={mouse_dx}, mouse_dy={mouse_dy}, orbit_y={self._orbit_angle_y:.3f}, orbit_x={self._orbit_angle_x:.3f}, dist={self._camera_distance:.2f}")
        
        if mouse_left and (mouse_dx != 0 or mouse_dy != 0):
            sensitivity = 0.01
            self._orbit_angle_y += mouse_dx * sensitivity
            self._orbit_angle_x += mouse_dy * sensitivity
            # Clamp vertical rotation
            self._orbit_angle_x = max(-np.pi/2 + 0.1, min(np.pi/2 - 0.1, self._orbit_angle_x))
        
        # Handle mouse wheel for zoom
        mouse_scroll = getattr(viz_window, 'mouse_scroll', 0)
        if mouse_scroll != 0:
            print(f"DEBUG: scroll={mouse_scroll}")
            zoom_sensitivity = 0.5
            self._camera_distance -= mouse_scroll * zoom_sensitivity
            self._camera_distance = max(1.0, min(20.0, self._camera_distance))
            # Reset scroll after handling
            viz_window.mouse_scroll = 0
        
        # Update camera projection if size changed
        if self.camera:
            viewport = self._renderer.ctx.viewport
            width = viewport[2]
            height = viewport[3]
            if width > 0 and height > 0:
                self.camera.update_projection(width, height)

        # Update objects that have signal bindings
        self._update_objects_from_signals()

    def _update_objects_from_signals(self):
        """Update object transforms based on bound signals."""
        if not self.data_bus:
            return
            
        for obj_name, obj_data in self.objects.items():
            # Check if this object has a position signal bound
            if 'position_signal' in obj_data:
                signal_name = obj_data['position_signal']
                signal_value = self.data_bus.latest(signal_name)
                if signal_value is not None:
                    # Convert to numpy array and ensure it's 3D
                    pos_array = np.asarray(signal_value, dtype='f4')
                    if pos_array.size >= 3:
                        obj_data['position'] = pos_array[:3]  # Take first 3 components
            
            # Check if this object has a rotation signal bound
            if 'rotation_signal' in obj_data:
                signal_name = obj_data['rotation_signal']
                signal_value = self.data_bus.latest(signal_name)
                if signal_value is not None:
                    # Convert to numpy array
                    rot_array = np.asarray(signal_value, dtype='f4')
                    if rot_array.size >= 3:
                        obj_data['rotation'] = rot_array[:3]  # Take first 3 components as Euler angles

    def bind_camera(self, camera):
        """This widget manages its own camera, so we ignore the passed camera."""
        # We could use the passed camera to set initial state, but for now we create our own
        pass

    def draw(self, renderer):
        """Draw the grid, axes, and any objects in the scene."""
        if renderer is None:
            renderer = self._renderer
        if not renderer:
            return

        # Enable depth test for 3D rendering
        renderer.ctx.enable(moderngl.DEPTH_TEST)

        # Set up camera
        if self.camera:
            # Update camera aspect ratio based on current viewport
            # The viewport is set by the window before calling draw
            viewport = renderer.ctx.viewport
            width = viewport[2]
            height = viewport[3]
            if width > 0 and height > 0:
                self.camera.update_projection(width, height)

            # Get view and projection matrices
            view_matrix = self.camera.view
            projection_matrix = self.camera.projection

            # Calculate camera position from orbit angles and distance
            # Spherical coordinates to Cartesian:
            # x = distance * cos(pitch) * sin(yaw)
            # y = distance * sin(pitch)
            # z = distance * cos(pitch) * cos(yaw)
            cos_pitch = np.cos(self._orbit_angle_x)
            camera_pos = np.array([
                self._camera_distance * cos_pitch * np.sin(self._orbit_angle_y),
                self._camera_distance * np.sin(self._orbit_angle_x),
                self._camera_distance * cos_pitch * np.cos(self._orbit_angle_y)
            ], dtype='f4')
            target = np.array([0.0, 0.0, 0.0], dtype='f4')
            up = np.array([0.0, 1.0, 0.0], dtype='f4')

            # Recalculate view matrix based on camera position
            view_matrix = self._look_at(camera_pos, target, up)

            # Combine model, view, projection
            # For now, no model transformation (identity)
            model_matrix = np.eye(4, dtype='f4')
            mvp = projection_matrix @ view_matrix @ model_matrix

        # Draw grid
        if self.show_grid and self.grid_mesh:
            self._draw_mesh(self.grid_mesh['vertices'], self.grid_mesh['indices'], color=[0.5, 0.5, 0.5], renderer=renderer, mvp=mvp if self.camera else None)

        # Draw axes
        if self.show_axes:
            for axis_name, axis_data in self.axes_meshes.items():
                mesh = axis_data['mesh']
                color = axis_data['color']
                # For axes, we apply the rotation to align the arrow
                # We'll create a model matrix that includes the rotation
                model_matrix = axis_data['rotation']  # This is already a 4x4 rotation matrix
                # Then we combine with view and projection
                if self.camera:
                    mvp_axis = projection_matrix @ view_matrix @ model_matrix
                else:
                    mvp_axis = None
                self._draw_mesh(mesh['vertices'], mesh['indices'], color=color, renderer=renderer, mvp=mvp_axis)

        # Draw objects in the scene
        for obj_name, obj_data in self.objects.items():
            mesh = obj_data['mesh']
            color = obj_data['color']
            
            # Get position - either from stored value or from signal if bound
            if 'position_signal' in obj_data and self.data_bus:
                # Use signal value if available
                signal_value = self.data_bus.latest(obj_data['position_signal'])
                if signal_value is not None:
                    pos_array = np.asarray(signal_value, dtype='f4')
                    if pos_array.size >= 3:
                        position = pos_array[:3]
                    else:
                        position = obj_data.get('position', np.array([0.0, 0.0, 0.0], dtype='f4'))
                else:
                    position = obj_data.get('position', np.array([0.0, 0.0, 0.0], dtype='f4'))
            else:
                position = obj_data.get('position', np.array([0.0, 0.0, 0.0], dtype='f4'))
            
            # Get rotation - either from stored value or from signal if bound
            if 'rotation_signal' in obj_data and self.data_bus:
                # Use signal value if available
                signal_value = self.data_bus.latest(obj_data['rotation_signal'])
                if signal_value is not None:
                    rot_array = np.asarray(signal_value, dtype='f4')
                    if rot_array.size >= 3:
                        rotation = rot_array[:3]  # Treat as Euler angles
                    else:
                        rotation = obj_data.get('rotation', np.array([0.0, 0.0, 0.0], dtype='f4'))
                else:
                    rotation = obj_data.get('rotation', np.array([0.0, 0.0, 0.0], dtype='f4'))
            else:
                rotation = obj_data.get('rotation', np.array([0.0, 0.0, 0.0], dtype='f4'))
            
            scale = obj_data.get('scale', np.array([1.0, 1.0, 1.0], dtype='f4'))
            
            # Create model matrix: scale * rotation * translation
            # Start with scale (4x4)
            model_matrix = np.eye(4, dtype='f4')
            model_matrix[0, 0] = scale[0]
            model_matrix[1, 1] = scale[1]
            model_matrix[2, 2] = scale[2]
            
            # Handle rotation - could be Euler angles (3,) or rotation matrix (3,3) or (4,4)
            if rotation.size == 3 and rotation.ndim == 1:
                # Euler angles (pitch, yaw, roll) - convert to rotation matrix
                # Apply in ZYX order (yaw, pitch, roll) to match KinematicFrame convention
                rot_x = rotation_x(rotation[0])  # pitch
                rot_y = rotation_y(rotation[1])  # yaw  
                rot_z = rotation_z(rotation[2])  # roll
                rotation_matrix = rot_z @ rot_y @ rot_x
            elif rotation.shape == (3, 3):
                # 3x3 rotation matrix - convert to 4x4
                rotation_matrix = np.eye(4, dtype='f4')
                rotation_matrix[0:3, 0:3] = rotation
            elif rotation.shape == (4, 4):
                # Already a 4x4 matrix
                rotation_matrix = rotation
            else:
                # Fallback to identity
                rotation_matrix = np.eye(4, dtype='f4')
            
            # Apply rotation
            model_matrix = rotation_matrix @ model_matrix
            
            # Apply translation
            model_matrix[0, 3] = position[0]
            model_matrix[1, 3] = position[1]
            model_matrix[2, 3] = position[2]
            
            # Combine with view and projection
            if self.camera:
                mvp_obj = projection_matrix @ view_matrix @ model_matrix
            else:
                mvp_obj = None
                
            self._draw_mesh(mesh['vertices'], mesh['indices'], color=color, renderer=renderer, mvp=mvp_obj)

        # Disable depth test after 3D rendering (so 2D UI on top works correctly)
        renderer.ctx.disable(moderngl.DEPTH_TEST)

    def _look_at(self, eye, target, up):
        """Create a view matrix from eye position looking at target."""
        forward = target - eye
        forward_norm = np.linalg.norm(forward)
        if forward_norm > 0:
            forward = forward / forward_norm
        else:
            forward = np.array([0, 0, 1], dtype='f4')

        right = np.cross(forward, up)
        right_norm = np.linalg.norm(right)
        if right_norm > 0:
            right = right / right_norm
        else:
            right = np.array([1, 0, 0], dtype='f4')

        up = np.cross(right, forward)

        # Create view matrix (inverse of camera transform)
        view = np.eye(4, dtype='f4')
        view[0:3, 0] = right
        view[0:3, 1] = up
        view[0:3, 2] = -forward  # Negative because camera looks backward
        view[0:3, 3] = -np.dot(right, eye)
        view[1:3, 3] = -np.dot(up, eye)
        view[2:3, 3] = np.dot(forward, eye)
        return view

    def _draw_mesh(self, vertices, indices, color=None, mvp=None, renderer=None):
        """Draw a mesh given vertices and indices."""
        if renderer is None:
            renderer = self._renderer

        if vertices.size == 0 or indices.size == 0:
            return

        # Prepare vertex data: interleave position and color like KinematicFrame does
        if color is not None:
            # Tile the color to match number of vertices
            color_data = np.tile(color, (len(vertices), 1)).astype('f4')
        else:
            # Default to white
            color_data = np.ones((len(vertices), 3), dtype='f4')
        
        # Interleave position and color: [x,y,z, r,g,b, x,y,z, r,g,b, ...]
        interleaved = np.zeros((len(vertices), 6), dtype='f4')
        interleaved[:, 0:3] = vertices.astype('f4')  # position
        interleaved[:, 3:6] = color_data              # color
        
        # Create VBO for interleaved vertex data
        vbo = renderer.ctx.buffer(interleaved.tobytes())
        
        # Create IBO for indices
        ibo = renderer.ctx.buffer(indices.astype('i4').tobytes())

        # Use the static_arrow shader (expects in_vert, in_color, and mvp uniform)
        # Follow the exact pattern from KinematicFrame.draw()
        renderer.draw("static_arrow", 
                     [(vbo, "3f 3f", "in_vert", "in_color")], 
                     ibo)

        # Set MVP uniform if we have one (after drawing, but this should still work)
        if mvp is not None:
            # The static_arrow shader expects a uniform "mvp"
            renderer.set_uniform("static_arrow", "mvp", mvp.astype('f4').T.tobytes())

        # Cleanup
        vbo.release()
        ibo.release()