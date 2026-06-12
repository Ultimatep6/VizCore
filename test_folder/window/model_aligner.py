import numpy as np
import os
import moderngl
from vizcore.utils import get_total_rot_matrix, get_model_matrix
from vizcore.renderer.camera import Camera
from settings_gui.guiRenderer import GuiRenderer
from settings_gui.elements import Button, Slider

from . import settings

AXIS_RED = np.array([0.9, 0.2, 0.2], dtype=np.float32)
AXIS_GREEN = np.array([0.2, 0.85, 0.2], dtype=np.float32)
AXIS_BLUE = np.array([0.2, 0.4, 0.95], dtype=np.float32)


class ModelAligner:
    def __init__(self, mainWindow):
        self.ctx = mainWindow.ctx
        self.active = False
        self._on_done_cb = None
        self._version_id = ""
        self._orig_verts = None
        self._orig_normals = None
        self._n_indices = 0
        self._vao = None

        self._load_programs(mainWindow)
        self._setup_axis()
        self.renderer = GuiRenderer(mainWindow)

        self._cam = Camera(window_size=(400, 400), eye=np.array([4.0, 3.0, 4.0]),
                           target=np.array([0.0, 0.0, 0.0]), near=0.1, far=5000.0)

        self._sliders = []
        self._btn_done = None
        self._btn_reset = None
        self._btn_close = None
        self._build_controls()

        self._model_radius = 0.0

        self._panel_rect = (0, 0, 100, 100)
        self._view_rect = (0, 0, 100, 100)
        self._sidebar_rect = (0, 0, 100, 100)

    def _load_programs(self, mainWindow):
        self.model_program = mainWindow.load_program(
            vertex_shader=os.path.join(settings.SHADER_DIR, "sim_model.vert"),
            fragment_shader=os.path.join(settings.SHADER_DIR, "sim_model.frag"),
        )
        self.axis_program = mainWindow.load_program(
            vertex_shader=os.path.join(settings.SHADER_DIR, "sim_arrow.vert"),
            fragment_shader=os.path.join(settings.SHADER_DIR, "sim_arrow.frag"),
            defines={
                "SEGMENTS": 16,
                "MAX_INSTANCES": 3,
                "SHAFT_RADIUS": 0.04,
                "SHAFT_HEIGHT": 0.6,
                "HEAD_RADIUS": 0.10,
                "HEAD_HEIGHT": 0.2,
            },
        )

    def _setup_axis(self):
        self.axis_vao = self.ctx.vertex_array(self.axis_program, [])
        self._axis_mats = np.zeros((3, 4, 4), dtype=np.float32)
        self._axis_colors = np.array(
            [AXIS_RED, AXIS_GREEN, AXIS_BLUE], dtype=np.float32
        )
        self._axis_vert_count = 12 * 16

    def _build_controls(self):
        slider_defs = [
            ("Rot X", -180, 180, 0),
            ("Rot Y", -180, 180, 0),
            ("Rot Z", -180, 180, 0),
            ("Pos X", -5, 5, 0),
            ("Pos Y", -5, 5, 0),
            ("Pos Z", -5, 5, 0),
            ("Scale", 0.1, 10.0, 1.0),
        ]
        self._sliders = [
            Slider(0, 0, 150, 48, label=label,
                   min_val=min_v, max_val=max_v, initial=init)
            for label, min_v, max_v, init in slider_defs
        ]
        self._btn_done = Button(0, 0, 120, 32, "Done",
                                color=(0.2, 0.6, 0.3),
                                hover_color=(0.3, 0.7, 0.4),
                                press_color=(0.15, 0.5, 0.25),
                                on_click=self._on_done)
        self._btn_reset = Button(0, 0, 120, 32, "RESET",
                                 color=(0.35, 0.35, 0.4),
                                 hover_color=(0.45, 0.45, 0.5),
                                 on_click=self._on_reset)
        self._btn_close = Button(0, 0, 120, 32, "CLOSE",
                                 color=(0.5, 0.25, 0.25),
                                 hover_color=(0.6, 0.35, 0.35),
                                 on_click=self._on_close)

    def _compute_layout(self, w, h):
        pad = 20
        pw = int(w * 0.88)
        ph = int(h * 0.85)
        px = (w - pw) // 2
        py = (h - ph) // 2
        self._panel_rect = (px, py, pw, ph)

        vp_w = int(pw * 0.68)
        vp_h = ph - pad * 2
        self._view_rect = (px + pad, py + pad, vp_w, vp_h)

        sb_x = px + pad + vp_w + pad
        sb_w = pw - vp_w - pad * 3
        self._sidebar_rect = (sb_x, py + pad, sb_w, ph - pad * 2)

        self._cam.update_aspect_ratio(vp_w, vp_h)

        # Layout sliders from top of sidebar
        sl = self._sidebar_rect
        slider_w = sl[2] - 20
        slider_x = sl[0] + 10
        y = sl[1] + sl[3] - 30
        for i, s in enumerate(self._sliders):
            s.x = slider_x
            s.y = y - 48
            s.w = slider_w
            s.h = 48
            y -= 48 + 8

        # Buttons bottom of sidebar
        btn_w = min(120, sl[2] - 20)
        btn_x = sl[0] + (sl[2] - btn_w) // 2
        bottom_y = sl[1] + 20
        self._btn_done.x = btn_x
        self._btn_done.y = bottom_y
        self._btn_done.w = btn_w
        self._btn_done.h = 32
        self._btn_reset.x = btn_x
        self._btn_reset.y = bottom_y + 42
        self._btn_reset.w = btn_w
        self._btn_reset.h = 32
        self._btn_close.x = btn_x
        self._btn_close.y = bottom_y + 84
        self._btn_close.w = btn_w
        self._btn_close.h = 32

    def _position_camera_for_model(self):
        if self._orig_verts is None:
            return
        center = (self._orig_verts.min(axis=0) + self._orig_verts.max(axis=0)) / 2
        radius = np.max(self._orig_verts.max(axis=0) - self._orig_verts.min(axis=0)) / 2
        dist = max(radius * 2.5, 1.0)
        self._cam.far = dist * 3 + radius * 2
        self._cam.eye = np.array([dist, dist * 0.75, dist], dtype=np.float32)
        self._cam.target = center.astype(np.float32)

    def load_model(self, version_id, verts, normals, indices):
        self._version_id = version_id
        self._orig_verts = verts.copy()
        self._orig_normals = normals.copy()
        self._n_indices = len(indices) * 3 if indices.ndim == 2 else len(indices)

        vbo_verts = self.ctx.buffer(verts.astype("f4").tobytes())
        vbo_normals = self.ctx.buffer(normals.astype("f4").tobytes())
        ibo = self.ctx.buffer(indices.astype("i4").tobytes())
        self._vao = self.ctx.vertex_array(
            self.model_program,
            [(vbo_verts, "3f", "in_vert"), (vbo_normals, "3f", "in_normal")],
            ibo,
        )

        self._model_radius = np.max(
            verts.max(axis=0) - verts.min(axis=0)
        ) / 2
        r = self._model_radius
        for i in range(3, 6):
            self._sliders[i].min_val = -r
            self._sliders[i].max_val = r
        inits = [0, 0, 0, 0, 0, 0, 1.0]
        for i, s in enumerate(self._sliders):
            s.value = inits[i]

        self._position_camera_for_model()

    def show(self):
        self.active = True

    def close(self):
        self.active = False
        self._vao = None
        self._version_id = ""
        self._orig_verts = None
        self._orig_normals = None
        self._model_radius = 0.0

    def _rotation_matrix(self):
        rx = np.radians(self._sliders[0].value)
        ry = np.radians(self._sliders[1].value)
        rz = np.radians(self._sliders[2].value)
        return get_total_rot_matrix(rx, ry, rz)[:3, :3]

    def _on_done(self):
        if self._vao is None:
            return
        R = self._rotation_matrix()
        s = self._sliders[6].value
        d = np.array([self._sliders[3].value,
                      self._sliders[4].value,
                      self._sliders[5].value], dtype=np.float32)

        aligned_verts = s * (R @ self._orig_verts.T).T + d
        aligned_normals = (R @ self._orig_normals.T).T
        norms = np.linalg.norm(aligned_normals, axis=1, keepdims=True)
        norms = np.where(norms > 1e-8, norms, 1.0)
        aligned_normals /= norms

        if self._on_done_cb:
            self._on_done_cb(self._version_id, aligned_verts, aligned_normals)
        self.close()

    def _on_reset(self):
        if self._model_radius > 0:
            r = self._model_radius
            for i in range(3, 6):
                self._sliders[i].min_val = -r
                self._sliders[i].max_val = r
        inits = [0, 0, 0, 0, 0, 0, 1.0]
        for i, s in enumerate(self._sliders):
            s.value = inits[i]
        self._position_camera_for_model()

    def _on_close(self):
        self.close()

    def render(self, w, h):
        if not self.active:
            return
        self._compute_layout(w, h)

        # Dim overlay
        self.renderer.quad(0, 0, w, h, (0.05, 0.05, 0.08))

        # Panel background
        px, py, pw, ph = self._panel_rect
        self.renderer.quad(px, py, pw, ph, (0.12, 0.12, 0.16))
        self.renderer.outline(px, py, pw, ph, (0.3, 0.3, 0.4))

        # 3D viewport
        old_vp = self.ctx.viewport
        vx, vy, vw, vh = self._view_rect
        self.ctx.viewport = (vx, vy, vw, vh)

        self.ctx.clear(0.05, 0.05, 0.08, 1.0)
        self.ctx.enable(moderngl.DEPTH_TEST)

        vp = self._cam.get_vp()

        # Axis in viewport (scale to model size, fallback 0.6 if no model)
        axis_scale = self._model_radius * 0.4 if self._model_radius > 0 else 0.6
        self._axis_mats[0] = get_model_matrix(
            sx=axis_scale, sy=axis_scale, sz=axis_scale, rz=-np.pi / 2
        )
        self._axis_mats[1] = get_model_matrix(
            sx=axis_scale, sy=axis_scale, sz=axis_scale
        )
        self._axis_mats[2] = get_model_matrix(
            sx=axis_scale, sy=axis_scale, sz=axis_scale, rx=np.pi / 2
        )

        self.axis_program["u_vp"] = tuple(vp.astype("f4").T.ravel())
        self.axis_program["u_models"].write(
            self._axis_mats.transpose(0, 2, 1).ravel().astype("f4").tobytes()
        )
        self.axis_program["u_colors"].write(
            self._axis_colors.astype("f4").tobytes()
        )
        self.axis_vao.render(
            moderngl.TRIANGLES, self._axis_vert_count, instances=3
        )

        # Model in viewport
        if self._vao is not None:
            R = self._rotation_matrix()
            s = self._sliders[6].value
            d = np.array([self._sliders[3].value,
                          self._sliders[4].value,
                          self._sliders[5].value], dtype=np.float32)

            self.model_program["u_vp"].write(vp.astype("f4").T.tobytes())
            self.model_program["u_rotation"].write(R.astype("f4").tobytes())
            self.model_program["u_offset"].write(d.astype("f4").tobytes())
            self.model_program["u_scale"].write(np.float32(s))
            self.model_program["u_color"].write(
                np.array([0.3, 0.8, 0.9], dtype="f4").tobytes()
            )
            self._vao.render(moderngl.TRIANGLES, self._n_indices)

        self.ctx.disable(moderngl.DEPTH_TEST)
        self.ctx.viewport = old_vp

        # Sidebar sliders
        for s in self._sliders:
            s.draw(self.renderer)

        # Sidebar buttons
        self._btn_done.draw(self.renderer)
        self._btn_reset.draw(self.renderer)
        self._btn_close.draw(self.renderer)

    def on_mouse_press(self, x, y, button):
        if not self.active:
            return False
        # Check sidebar controls first
        for s in self._sliders:
            if s.hit_test(x, y):
                s.on_mouse_press(x, y, button)
                self._drag_capture = ("slider", s)
                return True
        for btn in (self._btn_done, self._btn_reset, self._btn_close):
            if btn.hit_test(x, y):
                btn.hovered = True
                btn.on_mouse_press(x, y, button)
                self._drag_capture = ("btn", btn)
                return True

        # Check if in viewport → orbit camera
        vx, vy, vw, vh = self._view_rect
        if vx <= x <= vx + vw and vy <= y <= vy + vh:
            self._cam.on_mouse_press(1, x, y)
            self._drag_capture = ("orbit", None)
            self._last_mouse = (x, y)
            return True

        # Click outside panel → close
        px, py, pw, ph = self._panel_rect
        if not (px <= x <= px + pw and vy <= y <= vy + ph):
            self.close()
            return True
        return True

    def on_mouse_release(self, x, y, button):
        if not self.active:
            return
        if not hasattr(self, "_drag_capture") or self._drag_capture is None:
            return
        typ, obj = self._drag_capture
        if typ == "slider":
            obj.on_mouse_release(x, y, button)
        elif typ == "btn":
            obj.on_mouse_release(x, y, button)
        elif typ == "orbit":
            self._cam.on_mouse_release(1)
        self._drag_capture = None

    def on_mouse_drag(self, x, y, dx, dy):
        if not self.active:
            return
        if not hasattr(self, "_drag_capture") or self._drag_capture is None:
            return
        typ, obj = self._drag_capture
        if typ == "slider":
            obj.on_mouse_drag(x, y, dx, dy, 1)
        elif typ == "orbit":
            self._cam.on_mouse_drag(x, y)

    def on_resize(self, w, h):
        self.renderer.width = w
        self.renderer.height = h
