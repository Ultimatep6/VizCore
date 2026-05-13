import numpy as np
import moderngl
from vizcore.components.base.baseWidget import BaseWidget


class ScalarGauge(BaseWidget):
    """
    A 2D UI gauge widget for visualizing a single scalar value.
    Renders a horizontal progress bar with dynamic color thresholds and text labels.
    """

    def __init__(
        self, rect=None, min_val=0.0, max_val=100.0, threshold=20.0, text_renderer=None
    ):
        super().__init__(rect)

        self.min_val = min_val
        self.max_val = max_val
        self.threshold = threshold

        self._text_renderer = text_renderer
        self._renderer = None
        self.camera = None

        self.signal_names = []
        self.current_values = {}
        self._vbos = {}
        self.gauge_hitboxes = {}

        self.gauge_configs = {}
        self.observed_min = {}
        self.observed_max = {}

        self.rect = rect if rect else [50, 50, 200, 30]

    @property
    def required_shape(self):
        """Ensures the widget only accepts scalar values or (1,) shape arrays."""
        return [(1,)]

    def bind_external_signal(self, data_bus, signal: list):
        """Binds the widget to specific 1D scalar signals on the data bus."""
        self.data_bus = data_bus
        for s in signal:
            if s not in self.signal_names:
                self.signal_names.append(s)
                self.current_values[s] = 0.0
                self.gauge_configs[s] = {
                    "min_val": self.min_val,
                    "max_val": self.max_val,
                    "threshold": self.threshold,
                }

    def bind_renderer(self, renderer):
        """Binds the main renderer and initializes GPU buffers."""
        self._renderer = renderer
        if not self._text_renderer:
            self._text_renderer = getattr(renderer, "text_renderer", None)
        self._build_buffers()

    def bind_camera(self, camera):
        self.camera = camera

    @property
    def use_camera(self) -> bool:
        return True

    def get_camera_config(self) -> dict:
        return {
            "eye": np.array([0.0, 0.0, 1.0], dtype=np.float32),
            "target": np.array([0.0, 0.0, 0.0], dtype=np.float32),
            "fov_y_deg": 45,
            "enable_keyboard": False,
            "near": 0.01,
            "far": 100.0,
        }

    def get_context_menu(self, local_x, local_y):
        ry = self.camera.height - local_y
        for sig, hbx in getattr(self, "gauge_hitboxes", {}).items():
            x, y, w, h = hbx
            if x <= local_x <= x + w and y <= ry <= y + h:
                self.selected_gauge = sig
                return [f"Remove {sig}"]
        self.selected_gauge = None
        return None

    def on_context_menu(self, action_label):
        if action_label.startswith("Remove "):
            sig = action_label[7:]
            if sig in self.signal_names:
                self.signal_names.remove(sig)

    def _build_buffers(self):
        """Creates VBOs for rendering the 2D bar."""
        quad_verts = np.array(
            [0.0, 0.0, 1.0, 0.0, 0.0, 1.0, 1.0, 1.0],
            dtype="f4",
        )
        self._vbos["quad"] = self._renderer.ctx.buffer(quad_verts.tobytes())

        border_verts = np.array([0.0, 0.0, 1.0, 0.0, 1.0, 1.0, 0.0, 1.0], dtype="f4")
        self._vbos["border"] = self._renderer.ctx.buffer(border_verts.tobytes())

    def update(self):
        """Fetches the latest scalar values from the DataBus."""
        if hasattr(self, "data_bus"):
            for sig in self.signal_names:
                val = self.data_bus.latest(sig)
                if val is not None:
                    self.current_values[sig] = float(np.asarray(val).flatten()[0])

    def _update_observed_range(self, sig, val):
        """
        Initializes and expands the observed range for a signal.

        On first observation the range is seeded to always include 0 so there
        is a defined base position from the start. A minimum spread of 1.0 is
        enforced to prevent degenerate zero-width ranges.
        """
        if sig not in self.observed_min:
            self.observed_min[sig] = min(0.0, val)
            self.observed_max[sig] = max(0.0, val)
        else:
            self.observed_min[sig] = min(self.observed_min[sig], val)
            self.observed_max[sig] = max(self.observed_max[sig], val)

        # Guarantee a minimum spread so fill math never degenerates
        if self.observed_max[sig] - self.observed_min[sig] < 1.0:
            mid = (self.observed_min[sig] + self.observed_max[sig]) / 2.0
            self.observed_min[sig] = mid - 0.5
            self.observed_max[sig] = mid + 0.5

    def _compute_fill(self, val, obs_min, obs_max, bar_origin, bar_length):
        """
        Returns (fill_origin, fill_length) for a bar given the current value,
        observed range, and bar geometry.

        The base (zero crossing) is placed proportionally within [obs_min, obs_max].
        Positive values fill rightward/upward from base; negative values fill leftward/downward.
        """
        total_range = obs_max - obs_min
        base_ratio = max(0.0, min(1.0, (0.0 - obs_min) / total_range))
        base_px = bar_origin + base_ratio * bar_length

        val_ratio = max(0.0, min(1.0, (val - obs_min) / total_range))
        val_px = bar_origin + val_ratio * bar_length

        if val >= 0.0:
            return base_px, max(0.0, val_px - base_px)
        else:
            return val_px, max(0.0, base_px - val_px)

    def draw(self, renderer):
        """Renders the 2D gauge overlays."""
        self.gauge_hitboxes.clear()

        if not self.signal_names or "quad" not in self._vbos or not self.camera:
            return

        renderer.ctx.disable(moderngl.DEPTH_TEST)

        is_vertical_layout = self.camera.height > self.camera.width
        num_signals = len(self.signal_names)

        renderer.set_uniform(
            "ui", "u_resolution", (self.camera.width, self.camera.height)
        )

        for i, sig in enumerate(self.signal_names):
            val = self.current_values.get(sig, 0.0)
            self._update_observed_range(sig, val)

            obs_min = self.observed_min[sig]
            obs_max = self.observed_max[sig]

            fill_color = (0.85, 0.2, 0.2) if val <= self.threshold else (0.2, 0.85, 0.2)

            if not is_vertical_layout:
                w = max(10.0, self.camera.width * 0.8)
                available_h = self.camera.height * 0.8
                h_per_bar = available_h / num_signals
                h = max(5.0, h_per_bar * 0.5)

                bar_x = (self.camera.width - w) / 2
                y = (
                    self.camera.height
                    - (self.camera.height * 0.1)
                    - (i + 1) * h_per_bar
                    + (h_per_bar - h) / 2
                )
                self.gauge_hitboxes[sig] = (bar_x, y, w, h)

                # Background
                renderer.set_uniform("ui", "u_pos", (bar_x, y))
                renderer.set_uniform("ui", "u_size", (w, h))
                renderer.set_uniform("ui", "u_color", (0.15, 0.15, 0.15))
                renderer.draw(
                    "ui",
                    [(self._vbos["quad"], "2f", "in_vert")],
                    mode=moderngl.TRIANGLE_STRIP,
                )

                # Fill
                fill_x, fill_w = self._compute_fill(val, obs_min, obs_max, bar_x, w)
                renderer.set_uniform("ui", "u_pos", (fill_x, y))
                renderer.set_uniform("ui", "u_size", (fill_w, h))
                renderer.set_uniform("ui", "u_color", fill_color)
                renderer.draw(
                    "ui",
                    [(self._vbos["quad"], "2f", "in_vert")],
                    mode=moderngl.TRIANGLE_STRIP,
                )

                # Border
                renderer.set_uniform("ui", "u_pos", (bar_x, y))
                renderer.set_uniform("ui", "u_size", (w, h))
                renderer.set_uniform("ui", "u_color", (0.5, 0.5, 0.5))
                renderer.draw(
                    "ui",
                    [(self._vbos["border"], "2f", "in_vert")],
                    mode=moderngl.LINE_LOOP,
                )

                if self._text_renderer:
                    text_y = y + h + max(2.0, h_per_bar * 0.1)
                    label_text = f"{sig.split('.')[-1]}: {val:.1f}"
                    text_scale = min(0.45, max(0.2, (h_per_bar * 0.3) / 10.0))
                    self._text_renderer.render_text(
                        label_text,
                        bar_x,
                        text_y,
                        color=(1.0, 1.0, 1.0),
                        scale=text_scale,
                    )

            else:
                h = max(10.0, self.camera.height * 0.8)
                available_w = self.camera.width * 0.8
                w_per_bar = available_w / num_signals
                w = max(5.0, w_per_bar * 0.4)

                bar_y = (self.camera.height - h) / 2
                x = self.camera.width * 0.1 + i * w_per_bar + (w_per_bar - w) / 2

                self.gauge_hitboxes[sig] = (x, bar_y, w, h)

                # Background
                renderer.set_uniform("ui", "u_pos", (x, bar_y))
                renderer.set_uniform("ui", "u_size", (w, h))
                renderer.set_uniform("ui", "u_color", (0.15, 0.15, 0.15))
                renderer.draw(
                    "ui",
                    [(self._vbos["quad"], "2f", "in_vert")],
                    mode=moderngl.TRIANGLE_STRIP,
                )

                # Fill
                fill_y, fill_h = self._compute_fill(val, obs_min, obs_max, bar_y, h)
                renderer.set_uniform("ui", "u_pos", (x, fill_y))
                renderer.set_uniform("ui", "u_size", (w, fill_h))
                renderer.set_uniform("ui", "u_color", fill_color)
                renderer.draw(
                    "ui",
                    [(self._vbos["quad"], "2f", "in_vert")],
                    mode=moderngl.TRIANGLE_STRIP,
                )

                # Border
                renderer.set_uniform("ui", "u_pos", (x, bar_y))
                renderer.set_uniform("ui", "u_size", (w, h))
                renderer.set_uniform("ui", "u_color", (0.5, 0.5, 0.5))
                renderer.draw(
                    "ui",
                    [(self._vbos["border"], "2f", "in_vert")],
                    mode=moderngl.LINE_LOOP,
                )

                if self._text_renderer:
                    label_text = f"{sig.split('.')[-1]}"
                    val_text = f"{val:.1f}"
                    text_scale = min(0.35, max(0.15, (w_per_bar * 0.4) / 15.0))

                    text_y_label = bar_y + h + max(5.0, self.camera.height * 0.02)
                    text_y_val = bar_y - max(15.0, self.camera.height * 0.05)

                    self._text_renderer.render_text(
                        label_text,
                        x - w * 0.1,
                        text_y_label,
                        color=(1.0, 1.0, 1.0),
                        scale=text_scale,
                    )
                    self._text_renderer.render_text(
                        val_text,
                        x - w * 0.1,
                        text_y_val,
                        color=(0.8, 0.9, 0.8),
                        scale=text_scale,
                    )

        renderer.ctx.enable(moderngl.DEPTH_TEST)
