import numpy as np
import os
import moderngl

from . import settings


class Blips:
    def __init__(self, mainWindow) -> None:
        self.program = mainWindow.load_program(
            vertex_shader=os.path.join(settings.SHADER_DIR, "blip.vert"),
            fragment_shader=os.path.join(settings.SHADER_DIR, "blip.frag"),
            defines={
                "MAX_INSTANCES": settings.MAX_BLIPS,
                "BLIP_RADIUS": settings.BLIP_RADIUS,
            },
        )
        self.vao = mainWindow.ctx.vertex_array(self.program, [])
        self._positions = np.zeros((settings.MAX_BLIPS, 4), dtype=np.float32)
        self._count = 0

    def set_positions(self, positions: np.ndarray):
        N = positions.shape[0]
        self._positions[:N, :3] = positions
        self._positions[:N, 3] = 1.0
        self._count = N

    def set_active(self, blip_idx: int, active: bool):
        self._positions[blip_idx, 3] = 1.0 if active else 0.0

    def render(self, vp, camera_pos):
        self.program["u_vp"].write(vp.astype("f4").T.tobytes())
        self.program["u_camera_pos"].write(camera_pos.astype("f4").tobytes())
        self.program["u_translations"].write(
            self._positions.tobytes()
        )
        self.vao.render(moderngl.TRIANGLES, 36, instances=self._count)

    def pick(self, x, y, vp, camera_pos, viewport_size):
        w, h = viewport_size
        ndc_x = 2.0 * x / w - 1.0
        ndc_y = 1.0 - 2.0 * y / h
        near = np.array([ndc_x, ndc_y, -1.0, 1.0])
        far = np.array([ndc_x, ndc_y, 1.0, 1.0])
        inv_vp = np.linalg.inv(vp)
        near_w = inv_vp @ near
        near_w /= near_w[3]
        far_w = inv_vp @ far
        far_w /= far_w[3]
        ray_origin = near_w[:3]
        ray_dir = far_w[:3] - ray_origin
        ray_dir /= np.linalg.norm(ray_dir)
        positions = self._positions[:self._count, :3]
        r = settings.BLIP_RADIUS
        best_t = float('inf')
        best_idx = None
        for i, center in enumerate(positions):
            oc = ray_origin - center
            a = np.dot(ray_dir, ray_dir)
            b = 2.0 * np.dot(oc, ray_dir)
            c = np.dot(oc, oc) - r * r
            disc = b * b - 4.0 * a * c
            if disc < 0:
                continue
            t = (-b - np.sqrt(disc)) / (2.0 * a)
            if 0 < t < best_t:
                best_t = t
                best_idx = i
        return best_idx
