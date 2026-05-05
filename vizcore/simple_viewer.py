#!/usr/bin/env python3
"""Simple standalone OBJ viewer with mouse controls."""

import moderngl
import pyglet
import numpy as np
from vizcore.meshes import load_mesh

# Shader sources
VERTEX_SHADER = """#version 330
in vec3 in_position;
in vec3 in_color;

uniform mat4 mvp;

out vec3 v_color;

void main() {
    gl_Position = mvp * vec4(in_position, 1.0);
    v_color = in_color;
}
"""

FRAGMENT_SHADER = """#version 330
in vec3 v_color;
out vec4 f_color;

void main() {
    f_color = vec4(v_color, 1.0);
}
"""


class SimpleViewer(pyglet.window.Window):
    def __init__(self):
        super().__init__(1024, 768, "Simple OBJ Viewer", resizable=True)
        self.ctx = moderngl.create_context()
        self.ctx.enable(moderngl.DEPTH_TEST)
        
        # Camera state
        self.camera_orbit_y = 0.0
        self.camera_orbit_x = 0.2  # Slight tilt
        self.camera_distance = 5.0
        
        # Mouse state
        self.mouse_dragging = False
        self.last_mouse_x = 0
        self.last_mouse_y = 0
        
        # Load mesh
        print("Loading cube...")
        self.mesh_data = load_mesh('test_models/test_cube.obj')
        print(f"Loaded: {self.mesh_data['vertices'].shape[0]} vertices, {self.mesh_data['indices'].shape[0]} triangles")
        
        # Create shader program
        self.program = self.ctx.program(vertex_shader=VERTEX_SHADER, fragment_shader=FRAGMENT_SHADER)
        
        # Create VBOs
        self._create_buffers()
        
        print("Ready!")
        print("Controls: Left-click drag to rotate, Mouse wheel to zoom")
    
    def _create_buffers(self):
        """Create GPU buffers from mesh data."""
        vertices = self.mesh_data['vertices']
        indices = self.mesh_data['indices']
        
        # Create vertex colors (default: white with some lighting variation)
        n_verts = len(vertices)
        colors = np.ones((n_verts, 3), dtype='f4')
        colors[:, 1] = 0.7 * np.linspace(0.5, 1.0, n_verts)  # Gradient for depth
        
        # Interleave position and color
        interleaved = np.zeros((n_verts, 6), dtype='f4')
        interleaved[:, 0:3] = vertices
        interleaved[:, 3:6] = colors
        
        # Create buffers
        self.vbo = self.ctx.buffer(interleaved.tobytes())
        self.ibo = self.ctx.buffer(indices.astype('i4').tobytes())
        
        # Create VAO
        self.vao = self.ctx.vertex_array(
            self.program,
            [(self.vbo, '3f 3f', 'in_position', 'in_color')],
            self.ibo
        )
    
    def _get_mvp(self):
        """Calculate Model-View-Projection matrix."""
        width, height = self.get_size()
        aspect = width / max(height, 1)
        
        # Projection
        fov = np.radians(45)
        near = 0.1
        far = 100.0
        f = 1.0 / np.tan(fov / 2)
        projection = np.array([
            [f / aspect, 0, 0, 0],
            [0, f, 0, 0],
            [0, 0, (far + near) / (near - far), (2 * far * near) / (near - far)],
            [0, 0, -1, 0]
        ], dtype='f4')
        
        # View (camera position)
        cos_x = np.cos(self.camera_orbit_x)
        cam_x = self.camera_distance * cos_x * np.sin(self.camera_orbit_y)
        cam_y = self.camera_distance * np.sin(self.camera_orbit_x)
        cam_z = self.camera_distance * cos_x * np.cos(self.camera_orbit_y)
        
        # Look at
        eye = np.array([cam_x, cam_y, cam_z], dtype='f4')
        target = np.array([0, 0, 0], dtype='f4')
        up = np.array([0, 1, 0], dtype='f4')
        
        # Forward, Right, Up
        forward = target - eye
        forward = forward / np.linalg.norm(forward)
        right = np.cross(forward, up)
        right = right / np.linalg.norm(right)
        up = np.cross(right, forward)
        
        # View matrix
        view = np.eye(4, dtype='f4')
        view[0, 0:3] = right
        view[1, 0:3] = up
        view[2, 0:3] = -forward
        view[0, 3] = -np.dot(right, eye)
        view[1, 3] = -np.dot(up, eye)
        view[2, 3] = np.dot(forward, eye)
        
        # Model (identity)
        model = np.eye(4, dtype='f4')
        
        # Combined
        mvp = projection @ view @ model
        return mvp.astype('f4')
    
    def on_resize(self, width, height):
        self.ctx.viewport = (0, 0, width, height)
    
    def on_mouse_press(self, x, y, button, modifiers):
        if button == pyglet.window.mouse.LEFT:
            self.mouse_dragging = True
            self.last_mouse_x = x
            self.last_mouse_y = y
    
    def on_mouse_release(self, x, y, button, modifiers):
        if button == pyglet.window.mouse.LEFT:
            self.mouse_dragging = False
    
    def on_mouse_drag(self, x, y, dx, dy, buttons, modifiers):
        if self.mouse_dragging and buttons & pyglet.window.mouse.LEFT:
            self.camera_orbit_y += dx * 0.01
            self.camera_orbit_x += dy * 0.01
            # Clamp vertical rotation
            self.camera_orbit_x = max(-np.pi/2 + 0.1, min(np.pi/2 - 0.1, self.camera_orbit_x))
            self.last_mouse_x = x
            self.last_mouse_y = y
    
    def on_mouse_scroll(self, x, y, scroll_x, scroll_y):
        self.camera_distance -= scroll_y * 0.5
        self.camera_distance = max(1.0, min(20.0, self.camera_distance))
    
    def on_draw(self):
        self.clear()
        # Set background color using scissor/clear
        self.ctx.clear(0.1, 0.1, 0.1, 1.0)
        
        # Set MVP uniform
        mvp = self._get_mvp()
        self.program['mvp'].write(mvp.T.tobytes())
        
        # Draw
        self.vao.render(moderngl.TRIANGLES)


if __name__ == '__main__':
    viewer = SimpleViewer()
    pyglet.app.run()