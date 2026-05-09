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

        self.last_mouse_pos = None
        self.is_dragging = False

    def get_perspective(self):
        return get_perspective_matrix(
            fov_y_deg=self.fov_y_deg,
            aspect=self.aspect,
            near=self.near,
            far=self.far,
        )

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
        delta = np.zeros(3, dtype=np.float32)
        # World-space movement
        if keys.W in keys_pressed:
            delta[0] += self.move_speed
        if keys.S in keys_pressed:
            delta[0] -= self.move_speed
        if keys.D in keys_pressed:
            delta[2] -= self.move_speed
        if keys.A in keys_pressed:
            delta[2] += self.move_speed
        if keys.E in keys_pressed:
            delta[1] += self.move_speed
        if keys.Q in keys_pressed:
            delta[1] -= self.move_speed
        self.eye += delta
        self.target += delta

    def _axis_angle_rotation(self, axis: np.ndarray, angle: float) -> np.ndarray:
        c, s = np.cos(angle), np.sin(angle)
        x, y, z = axis
        return np.array(
            [
                [c + x * x * (1 - c), x * y * (1 - c) - z * s, x * z * (1 - c) + y * s],
                [y * x * (1 - c) + z * s, c + y * y * (1 - c), y * z * (1 - c) - x * s],
                [z * x * (1 - c) - y * s, z * y * (1 - c) + x * s, c + z * z * (1 - c)],
            ],
            dtype=np.float32,
        )

    def on_mouse_press(self, button: int):
        if button == 1:
            self.is_dragging = True

    def on_mouse_release(self, button: int):
        if button == 1:
            self.is_dragging = False
            self.last_mouse_pos = None

    def on_mouse_drag(self, x: int, y: int):
        if not self.is_dragging:
            return

        if self.last_mouse_pos is not None:
            dx = x - self.last_mouse_pos[0]
            dy = y - self.last_mouse_pos[1]

            eye_to_target = self.target - self.eye
            right = np.cross(eye_to_target, np.array([0, 1, 0], dtype=np.float32))
            right /= np.linalg.norm(right) + 1e-6

            Rx = self._axis_angle_rotation(right, -dy * self.mouse_sensitivity)
            Ry = self._axis_angle_rotation(
                np.array([0, 1, 0]), -dx * self.mouse_sensitivity
            )

            self.target = self.eye + (Ry @ Rx) @ eye_to_target

        self.last_mouse_pos = (x, y)
