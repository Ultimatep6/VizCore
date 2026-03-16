import numpy as np

class Camera:
    """
    Implements camera transformations for 3D scenes.

    Responsibilities:
        - View matrix calculation
        - Projection matrix calculation
        - Camera movement

    Supported modes:
        - Orbit camera
        - Free camera
    """
    def __init__(self, mode='orbit', position=None, target=None, up=None, fov=60.0, aspect=1.0, near=0.1, far=1000.0):
        self.mode = mode
        self.position = np.array(position if position is not None else [0, 0, 5], dtype=np.float32)
        self.target = np.array(target if target is not None else [0, 0, 0], dtype=np.float32)
        self.up = np.array(up if up is not None else [0, 1, 0], dtype=np.float32)
        self.fov = fov
        self.aspect = aspect
        self.near = near
        self.far = far

    def view_matrix(self):
        # Simple look-at implementation
        f = self.target - self.position
        f = f / np.linalg.norm(f)
        u = self.up / np.linalg.norm(self.up)
        s = np.cross(f, u)
        s = s / np.linalg.norm(s)
        u = np.cross(s, f)

        m = np.identity(4, dtype=np.float32)
        m[0, :3] = s
        m[1, :3] = u
        m[2, :3] = -f
        m[:3, 3] = -self.position
        return m

    def projection_matrix(self):
        # Perspective projection
        f = 1.0 / np.tan(np.radians(self.fov) / 2)
        m = np.zeros((4, 4), dtype=np.float32)
        m[0, 0] = f / self.aspect
        m[1, 1] = f
        m[2, 2] = (self.far + self.near) / (self.near - self.far)
        m[2, 3] = (2 * self.far * self.near) / (self.near - self.far)
        m[3, 2] = -1.0
        return m

    def move(self, direction):
        # Move camera in free mode
        if self.mode == 'free':
            self.position += np.array(direction, dtype=np.float32)

    def orbit(self, delta_theta, delta_phi, radius=None):
        # Orbit camera around target
        if self.mode == 'orbit':
            if radius is None:
                radius = np.linalg.norm(self.position - self.target)
            theta = np.arctan2(self.position[0], self.position[2]) + delta_theta
            phi = np.arccos(self.position[1] / radius) + delta_phi
            self.position[0] = radius * np.sin(phi) * np.sin(theta)
            self.position[1] = radius * np.cos(phi)
            self.position[2] = radius * np.sin(phi) * np.cos(theta)