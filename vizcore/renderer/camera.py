import numpy as np
from vizcore.utils import *


class Camera:
    def __init__(
        self,
        window_size: tuple,
        target: np.ndarray = np.zeros(3),
        eye: np.ndarray = np.zeros(3),
        fov_y_deg: int = 45,
        near: float = 0.1,
        far: float = 100.0,
        move_speed: float = 0.1,
        mouse_sensitivity: float = 0.005,
        enable_keyboard: bool = True,
        invert_y: bool = False,
    ):
        self.target = np.array(target, dtype=np.float32)
        self.eye = np.array(eye, dtype=np.float32)
        self.move_speed = move_speed
        self.mouse_sensitivity = mouse_sensitivity
        self.window_size = window_size
        self.fov_y_deg = fov_y_deg
        self.aspect = window_size[0] / window_size[1]
        self.near = near
        self.far = far
        self.enable_keyboard = enable_keyboard
        self.invert_y = invert_y

        self.last_mouse_pos = None
        self._drag_start_pos = None
        self.is_dragging = False

    def get_perspective(self):
        return get_perspective_matrix(
            fov_y_deg=self.fov_y_deg,
            aspect=self.aspect,
            near=self.near,
            far=self.far,
        )

    def update_aspect_ratio(self, width: int, height: int):
        """Update camera aspect ratio when window size changes."""
        self.window_size = (width, height)
        self.aspect = width / height if height > 0 else 1.0

    @property
    def projection(self):
        """Property for compatibility - returns perspective matrix."""
        return self.get_perspective()

    @property
    def view(self):
        """Property for compatibility - returns view matrix."""
        return self.get_view()

    @property
    def width(self) -> int:
        """Window width."""
        return self.window_size[0]

    @property
    def height(self) -> int:
        """Window height."""
        return self.window_size[1]

    def get_view(self):
        return get_view_matrix(eye=self.eye, target=self.target)

    def get_vp(self):
        return self.get_perspective() @ self.get_view()

    def translate_camera(self, translate_mat: np.ndarray):
        self.eye = translate_mat @ self.eye

    def _forward(self) -> np.ndarray:
        v = self.target - self.eye
        return v / (np.linalg.norm(v) + 1e-6)

    def _right(self) -> np.ndarray:
        r = np.cross(self._forward(), np.array([0, 1, 0], dtype=np.float32))
        return r / (np.linalg.norm(r) + 1e-6)

    def _up(self) -> np.ndarray:
        return np.array([0, 1, 0], dtype=np.float32)

    def on_key_press(self, keys, keys_pressed: set):
        if not self.enable_keyboard:
            return
        delta = np.zeros(3, dtype=np.float32)
        # World-space movement
        if keys.W in keys_pressed:
            delta[0] += self.move_speed
        if keys.S in keys_pressed:
            delta[0] -= self.move_speed
        if keys.D in keys_pressed:
            delta[2] += self.move_speed
        if keys.A in keys_pressed:
            delta[2] -= self.move_speed
        if keys.E in keys_pressed:
            delta[1] += self.move_speed
        if keys.Q in keys_pressed:
            delta[1] -= self.move_speed
        self.eye += delta
        self.target += delta

    def on_mouse_press(self, button: int, x: int = 0, y: int = 0):
        if button == 1:
            self.is_dragging = True
            self._drag_start_pos = (x, y)

    def on_mouse_release(self, button: int):
        if button == 1:
            self.is_dragging = False
            self._drag_start_pos = None
            self.last_mouse_pos = None

    def on_mouse_drag(self, x: int, y: int):
        if not self.is_dragging:
            return

        if self._drag_start_pos is None:
            self._drag_start_pos = (x, y)
            return

        dx = x - self._drag_start_pos[0]
        dy = y - self._drag_start_pos[1]

        self._drag_start_pos = (x, y)

        if self.invert_y:
            dy = -dy

        eye_to_target = self.target - self.eye
        right = np.cross(eye_to_target, np.array([0, 1, 0], dtype=np.float32))
        right /= np.linalg.norm(right) + 1e-6

        Rx = get_rot_matrix(-dy * self.mouse_sensitivity, right, dim=True)
        Ry = get_rot_matrix(-dx * self.mouse_sensitivity, Y_AXIS, dim=True)

        self.target = self.eye + (Ry @ Rx) @ eye_to_target
