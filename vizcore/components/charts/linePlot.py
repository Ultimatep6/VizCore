import numpy as np
import pyglet
import moderngl

from vizcore.components.base.baseWidget import BaseWidget
from vizcore.bus.data_bus import DataBus
from vizcore.bus.ring_buffer import RingBuffer


class LinePlot(BaseWidget):
    """
    A simple line plot for visualizing 1D data.
    Expected signal format: A 1D array of numeric values.

    Usage:
        line_plot = LinePlot()
        frame.render()
    """

    def __init__(
        self,
        rect=None,
        channels=1,
        text_renderer=None,
    ):
        super().__init__(rect)

        self.channels = channels

        self.signal_names = []
        self._local = {}
        self._vbos = {}

        self._text_renderer = text_renderer
        self._renderer = None

        # Line plot specfic
        self.points_per_channel = 1000

        # Plot range properties
        self.y_min = -1.0
        self.y_max = 1.0

        self._legend = True
        self._legend_width = 200
        self._legend_height = 100

        self._legend_y_offset = 30
        self._legend_x_offset = 10

        self._rect_axis_margin = 50

        # Text scaling attributes
        self.label_font_scale = 0.5
        self.legend_font_scale = 0.5

        self.colors = [
            (0.2, 0.85, 0.2),  # Green
            (0.2, 0.5, 0.85),  # Blue
            (0.85, 0.2, 0.2),  # Red
            (0.85, 0.85, 0.2),  # Yellow
            (0.85, 0.2, 0.85),  # Magenta
            (0.2, 0.85, 0.85),  # Cyan
        ]

    @property
    def required_shape(self):
        # Line plot only accepts 1D signals (scalars or (1,) arrays)
        return [(1,)]

    def bind_external_signal(self, data_bus, signal: list):
        if not hasattr(self, "signal_names"):
            raise ValueError(
                "LinePlot widget missing 'signal_names' attribute. Ensure to call super().__init__() in your constructor."
            )

        for signal_name in signal:
            if signal_name not in self.signal_names:
                self.signal_names.append(signal_name)

            if self.accepts_signal(data_bus, signal_name):
                # Ensure the RingBuffer size matches points_per_channel precisely
                size = self.points_per_channel
                self._local[signal_name] = RingBuffer(size)

                if not hasattr(self, "signal_to_index"):
                    self.signal_to_index = {}

                self.signal_to_index[signal_name] = len(self.signal_names) - 1

        # If the renderer is already bound, we need to re-initialize buffers to accommodate new signals
        if self._renderer:
            self._reallocate_buffers()

        self.data_bus = data_bus

    def _reallocate_buffers(self):
        """Pre-allocates GPU buffers with headroom to avoid frequent reallocations."""
        # Provision for up to 10 signals initially to avoid repeated frame-flicker during startup
        capacity = max(self.channels, len(self.signal_names), 10)

        # 1. Update Signal Buffer (Main data storage)
        old_buffer = getattr(self, "signal_buffer", None)

        # Only re-allocate if current capacity is exceeded
        if old_buffer is None or old_buffer.shape[0] < len(self.signal_names):
            print(f"--- [LinePlot] Reallocating GPU Buffers (Capacity: {capacity}) ---")
            self.signal_buffer = np.zeros(
                (capacity, self.points_per_channel), dtype="f4"
            )

            # Copy old data across to maintain history during the shift
            if old_buffer is not None:
                rows_to_copy = min(old_buffer.shape[0], capacity)
                self.signal_buffer[:rows_to_copy, :] = old_buffer[:rows_to_copy, :]

            # Update the VBO itself
            if "externalSignals" in self._vbos:
                self._vbos["externalSignals"].release()
            self._vbos["externalSignals"] = self._renderer.ctx.buffer(
                reserve=self.signal_buffer.nbytes
            )

            # 2. Update Indices Buffer (shared X-axis mapping)
            # We tile the indices for the FULL capacity to avoid mismatched draw sizes
            indices = np.tile(np.arange(self.points_per_channel, dtype="f4"), capacity)
            if "indices" in self._vbos:
                self._vbos["indices"].release()
            self._vbos["indices"] = self._renderer.ctx.buffer(indices.tobytes())

        # Always sync the current state to CPU for safety
        self._vbos["externalSignals"].write(self.signal_buffer.tobytes())

    def bind_renderer(self, renderer):
        self._renderer = renderer
        self._text_renderer = getattr(renderer, "text_renderer", None)

        self._build_axis()
        self._build_legend()
        self._reallocate_buffers()
        self.load_shaders(renderer.shader_manager)

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

    def load_shaders(self, shader_manager):
        shader_manager.load_shader(
            "line_plot",
            vertex_path="vizcore/shaders/line_plot.vert",
            fragment_path="vizcore/shaders/line_plot.frag",
        )

    def update(self):
        if not (hasattr(self, "signal_names") and hasattr(self, "data_bus")):
            raise ValueError(
                "LinePlot widget missing 'signal_names' or 'data_bus' attribute. Ensure to call super().__init__() in your constructor and bind the data bus before updating."
            )

        # Check for new signals in the data bus that match our requested signals but aren't local yet
        # This handles the case where a signal starts being pushed AFTER the initial bind
        for name in self.signal_names:
            if name not in self._local:
                if self.accepts_signal(self.data_bus, name):
                    self._local[name] = RingBuffer(self.points_per_channel)
                    if not hasattr(self, "signal_to_index"):
                        self.signal_to_index = {}
                    self.signal_to_index[name] = self.signal_names.index(name)

        for i, signal_name in enumerate(self.signal_names):
            if signal_name in self._local:
                val = self.data_bus.latest(signal_name)
                if val is not None:
                    latest = np.asarray(val, dtype="f4")
                    self._local[signal_name].push(latest)
                else:
                    latest = np.zeros(1, dtype="f4")
                    self._local[signal_name].push(latest)

                if (
                    hasattr(self, "signal_to_index")
                    and signal_name in self.signal_to_index
                ):
                    idx = self.signal_to_index[signal_name]

                    # Fetch the full signal history up to points_per_channel
                    # We reverse the history so [0] is newest, and fill into the buffer from RIGHT to LEFT.
                    # This ensures the 'current' time for all signals is aligned at X=points_per_channel-1.
                    hist = self._local[signal_name].history(self.points_per_channel)
                    if len(hist) > 0:
                        hist_arr = np.array(hist, dtype="f4").flatten()
                        length = len(hist_arr)

                        # Correct alignment: newest data at the far right of the plot window
                        # The buffer represents [Oldest Data -> Newest Data] from index 0 to length-1.
                        # We shift the valid data to the right to maintain time synchronization.
                        self.signal_buffer[idx, : self.points_per_channel - length] = (
                            0.0  # Pad leading zeros
                        )
                        self.signal_buffer[idx, self.points_per_channel - length :] = (
                            hist_arr
                        )

        # Dynamically evaluate the min and max limits from the available data.
        # This guarantees the graph boundaries explicitly hug the highest/lowest data points!
        if self.signal_buffer.size > 0 and len(self.signal_names) > 0:
            current_max = np.max(self.signal_buffer)
            current_min = np.min(self.signal_buffer)

            if not hasattr(self, "data_max"):
                self.data_max = current_max
                self.data_min = current_min
            else:
                # Instant attack to instantly encompass newly high/low values
                if current_max > self.data_max:
                    self.data_max = current_max
                else:  # Slow decay backwards internally to smooth tracking
                    self.data_max = self.data_max * 0.95 + current_max * 0.05

                if current_min < self.data_min:
                    self.data_min = current_min
                else:
                    self.data_min = self.data_min * 0.95 + current_min * 0.05

            # Add a 10% vertical padding so the data doesn't clip directly through the borders
            padding = max(abs(self.data_max - self.data_min) * 0.1, 0.001)

            # The actual frame boundaries used to scale the OpenGL coordinates (-1.2 to +1.2 etc)
            new_y_max = self.data_max + padding
            new_y_min = self.data_min - padding

            # Detect differences in visual min/max boundaries
            d_max_diff = abs(self.data_max - getattr(self, "_last_d_max", 0))
            d_min_diff = abs(self.data_min - getattr(self, "_last_d_min", 0))

            # Only rewrite structure if the span shifts OR the datalines drift to prevent misalignment
            if (
                not hasattr(self, "y_max")
                or abs(new_y_max - self.y_max) > 0.001
                or abs(new_y_min - self.y_min) > 0.001
                or d_max_diff > 0.001
                or d_min_diff > 0.001
            ):
                self.y_max = new_y_max
                self.y_min = new_y_min
                self._last_d_max = self.data_max
                self._last_d_min = self.data_min
                self._build_axis()

        self._vbos["externalSignals"].write(self.signal_buffer.tobytes())

    def _build_axis(self):
        """
        Creates the axes outlines: Dotted bounds, zero-line, etc.
        If the VBO exists, it simply overwrites it to avoid memory leaks.
        """
        y_span = self.y_max - self.y_min
        y_zero = (0.0 - self.y_min) / y_span if y_span != 0 else 0.5

        # Pull actual peak data references, default to full scale boundaries
        d_max = getattr(self, "data_max", self.y_max)
        d_min = getattr(self, "data_min", self.y_min)

        # Calculate exactly where the peak points lie on the 0...1 normalized height span
        y_data_max = (d_max - self.y_min) / y_span if y_span != 0 else 1.0
        y_data_min = (d_min - self.y_min) / y_span if y_span != 0 else 0.0

        verts = []
        # Y Axis Left Border (solid)
        verts.extend([0.0, 0.0, 0.0, 1.0])
        # Y Axis Right Plot Border (solid)
        verts.extend([1.0, 0.0, 1.0, 1.0])
        # Zero Line (solid)
        verts.extend([0.0, y_zero, 1.0, y_zero])

        # Dotted lines strictly mapped to highest and lowest signal values (1.0 vs -1.0)
        curr_x = 0.0
        dash_len = 0.015
        gap_len = 0.015
        while curr_x < 1.0:
            nxt_x = min(curr_x + dash_len, 1.0)
            verts.extend([curr_x, y_data_max, nxt_x, y_data_max])  # Top dot
            verts.extend([curr_x, y_data_min, nxt_x, y_data_min])  # Bottom dot
            curr_x += dash_len + gap_len

        axis_verts = np.array(verts, dtype="f4")
        if "axis" in self._vbos:
            try:
                self._vbos["axis"].write(axis_verts.tobytes())
            except Exception:
                self._vbos["axis"] = self._renderer.ctx.buffer(axis_verts.tobytes())
        else:
            self._vbos["axis"] = self._renderer.ctx.buffer(axis_verts.tobytes())

    def _get_layout(self):
        """Calculates standardized, proportionally sized layouts for all rendering operations"""
        ui_scale = self.camera.height / 600.0  # Dynamic scaler per display stretch
        m = self._rect_axis_margin * ui_scale

        leg_w = self._legend_width * ui_scale if self._legend else 0
        leg_h = self._legend_height * ui_scale if self._legend else 0

        # The plotting region ends BEFORE the legend width plus some spacing!
        plot_width = self.camera.width - 2 * m - (leg_w + 30 * ui_scale)
        plot_height = self.camera.height - 2 * m

        return ui_scale, m, plot_width, plot_height, leg_w, leg_h

    def _draw_axis(self, renderer, m, plot_w, plot_h):
        renderer.set_uniform(
            "ui", "u_resolution", (self.camera.width, self.camera.height)
        )
        renderer.set_uniform("ui", "u_color", (0.8, 0.8, 0.8))

        # We shrink the drawn width so it cleanly sits beside the legend!
        renderer.set_uniform("ui", "u_pos", (m, m))
        renderer.set_uniform("ui", "u_size", (plot_w, plot_h))

        renderer.draw(
            "ui", [(self._vbos["axis"], "2f", "in_vert")], mode=moderngl.LINES
        )

    def draw(self, renderer):
        # Disable Depth Testing as the LinePlot is a 2D composite consisting of overlapping UI elements.
        # This resolves Z-fighting that masks the legend texts and parameter colors!
        renderer.ctx.disable(moderngl.DEPTH_TEST)

        ui_scale, m, plot_w, plot_h, leg_w, leg_h = self._get_layout()

        self._draw_axis(renderer, m, plot_w, plot_h)
        self._draw_legend(renderer, ui_scale, m, leg_w, leg_h)

        # 1. Render Line Plot Data restricted to plot_w !
        if (
            "externalSignals" in self._vbos
            and "indices" in self._vbos
            and len(self.signal_names) > 0
        ):
            renderer.set_uniform("line_plot", "u_min", self.y_min)
            renderer.set_uniform("line_plot", "u_max", self.y_max)
            renderer.set_uniform("line_plot", "u_margin", float(m))

            # Bound the plot physically to plot_w limits via custom uniform!
            renderer.set_uniform("line_plot", "u_plot_width", float(plot_w))
            renderer.set_uniform(
                "line_plot", "u_resolution", (self.camera.width, self.camera.height)
            )
            renderer.set_uniform(
                "line_plot", "u_points_per_channel", float(self.points_per_channel)
            )

            content = [
                (self._vbos["externalSignals"], "1f", "in_y_val"),
                (self._vbos["indices"], "1f", "in_index"),
            ]

            for i, name in enumerate(self.signal_names):
                color = self.colors[i % len(self.colors)]
                renderer.set_uniform("line_plot", "u_color", color)
                renderer.draw(
                    "line_plot",
                    content,
                    mode=moderngl.LINE_STRIP,
                    vertices=self.points_per_channel,
                    first=i * self.points_per_channel,
                )

        # 2. Render Scaled Typography Label Positions dynamically padding to 'm'
        if self._text_renderer:
            txt_scale = self.label_font_scale * ui_scale
            y_mid_val = (self.y_max + self.y_min) / 2.0

            # Use data borders for text mapping
            d_max = getattr(self, "data_max", self.y_max)
            d_min = getattr(self, "data_min", self.y_min)

            # Calculating where the dotted lines are locally
            y_span = self.y_max - self.y_min
            max_y_offset = (
                (d_max - self.y_min) / y_span * plot_h if y_span != 0 else plot_h
            )
            min_y_offset = (
                (d_min - self.y_min) / y_span * plot_h if y_span != 0 else 0.0
            )

            # The Text renderer coordinates 0=Top, height=Bottom
            # We must subtract padding since OpenGL draws UPwards from the bottom
            self._text_renderer.render_text(
                f"{d_max:.1f}",
                m - (40 * txt_scale) - 10,
                self.camera.height - m - max_y_offset + (10 * txt_scale),
                color=(1.0, 1.0, 1.0),
                scale=txt_scale,
            )
            self._text_renderer.render_text(
                f"{y_mid_val:.1f}",
                m - (40 * txt_scale) - 10,
                self.camera.height / 2,
                color=(1.0, 1.0, 1.0),
                scale=txt_scale,
            )
            self._text_renderer.render_text(
                f"{d_min:.1f}",
                m - (50 * txt_scale) - 10,
                self.camera.height - m - min_y_offset + (10 * txt_scale),
                color=(1.0, 1.0, 1.0),
                scale=txt_scale,
            )

            # 3. Legend text mapped onto colored bounding rects
            if self._legend and len(self.signal_names) > 0:
                # Dynamically calculate the font scale so labels don't explode out of the legend
                # We base it on the height of the legend box divided by number of entries
                max_entries = 5  # Safety limit for scaling
                leg_txt_scale = (
                    self.legend_font_scale
                    * ui_scale
                    * (leg_h / (max_entries * 25.0 * ui_scale))
                )
                leg_txt_scale = min(
                    leg_txt_scale, 0.45 * ui_scale
                )  # Cap at a reasonable size

                # Y=0 is at the top of the screen for text.
                leg_top_y = m + (self._legend_y_offset * ui_scale)
                # Increased spacing from the color box (from +35 to +40) to make it less snug
                leg_text_x = (
                    self.camera.width
                    - m
                    - leg_w
                    - (self._legend_x_offset * ui_scale)
                    + (40 * ui_scale)
                )

                for i, name in enumerate(self.signal_names):
                    # Vertical positioning
                    entry_spacing = 25 * ui_scale
                    y_pos = leg_top_y + (18 * ui_scale) + (i * entry_spacing)

                    # Align text baseline precisely with the square's center (shifted slightly down for visual balance)
                    text_y_alignment = y_pos + (4 * ui_scale)

                    color = self.colors[i % len(self.colors)]
                    self._text_renderer.render_text(
                        name,
                        leg_text_x,
                        text_y_alignment,
                        color=color,
                        scale=leg_txt_scale,
                    )

        # Re-establish Depth Testing for standard 3D context elements
        renderer.ctx.enable(moderngl.DEPTH_TEST)

    def _build_legend(self):
        """
        Creates a closed unit rectangle outline for the Legend bounding box [0, 1].
        We use the 'ui' shader uniformly scale this unit box precisely to the legend parameters
        dynamically per-frame.
        """
        if not self._legend:
            return

        legend_verts = np.array(
            [
                0.0,
                0.0,  # Bottom Left
                1.0,
                0.0,  # Bottom Right
                1.0,
                1.0,  # Top Right
                0.0,
                1.0,  # Top Left
            ],
            dtype="f4",
        )

        # We allocate these once and leave them on the GPU
        self._vbos["legend_box"] = self._renderer.ctx.buffer(legend_verts.tobytes())

    def _draw_legend(self, renderer, ui_scale, m, leg_w, leg_h):
        if not self._legend or "legend_box" not in self._vbos:
            return

        pos_x = self.camera.width - m - leg_w - (self._legend_x_offset * ui_scale)
        pos_y = self.camera.height - m - leg_h - (self._legend_y_offset * ui_scale)

        renderer.set_uniform(
            "ui", "u_resolution", (self.camera.width, self.camera.height)
        )
        renderer.set_uniform("ui", "u_pos", (pos_x, pos_y))
        renderer.set_uniform("ui", "u_size", (leg_w, leg_h))

        # 1. Fill solid background to occlude anything under it
        renderer.set_uniform("ui", "u_color", (0.12, 0.12, 0.12))
        renderer.draw(
            "ui",
            [(self._vbos["legend_box"], "2f", "in_vert")],
            mode=moderngl.TRIANGLE_FAN,
        )

        # 2. Draw border frame
        renderer.set_uniform("ui", "u_color", (0.5, 0.5, 0.5))
        renderer.draw(
            "ui", [(self._vbos["legend_box"], "2f", "in_vert")], mode=moderngl.LINE_LOOP
        )

        # 3. Render tiny colored boxes beside the target data line
        box_size = 14 * ui_scale
        # Slightly more internal padding from the left edge (from +15 to +18)
        start_x = pos_x + 18 * ui_scale

        for i, name in enumerate(self.signal_names):
            color = self.colors[i % len(self.colors)]

            # The UI renderer coordinates consider Y=0 at the Bottom.
            # pos_y evaluates the overall bottom floor coordinate, leg_h climbs to the top of bounds
            box_y = pos_y + leg_h - (25 * ui_scale) - (i * 25 * ui_scale)

            renderer.set_uniform("ui", "u_pos", (start_x, box_y))
            renderer.set_uniform("ui", "u_size", (box_size, box_size))
            renderer.set_uniform("ui", "u_color", color)
            renderer.draw(
                "ui",
                [(self._vbos["legend_box"], "2f", "in_vert")],
                mode=moderngl.TRIANGLE_FAN,
            )


if __name__ == "__main__":
    # Control System Simulation State
    sim_state = {
        "target": 0.0,
        "current": 0.0,
        "velocity": 0.0,
        "last_switch": 0.0,
        "response_added": False,
        "start_time": 0.0,
    }

    def mock_update(dt):
        t = pyglet.clock.get_default().time()
        if sim_state["start_time"] == 0.0:
            sim_state["start_time"] = t

        elapsed = t - sim_state["start_time"]

        # 1. Generate Step Input (Control Signal)
        if t - sim_state["last_switch"] > 4.0:
            sim_state["target"] = 1.5 if sim_state["target"] == 0.0 else 0.0
            sim_state["last_switch"] = t

        # 2. Simulate System Response
        kp, kd = 15.0, 2.5
        error = sim_state["target"] - sim_state["current"]
        acceleration = (kp * error) - (kd * sim_state["velocity"])
        sim_state["velocity"] += acceleration * dt
        sim_state["current"] += sim_state["velocity"] * dt

        # 3. Always push target, but only add/push response after 6 seconds
        tester.push_data("step_target", [np.round(sim_state["target"], 4)])

        if elapsed > 6.0:
            if not sim_state["response_added"]:
                print("--- Automatically Adding System Response Signal ---")
                # Dynamically bind the new signal to the running widget
                line_plot.bind_external_signal(tester.data_bus, ["system_response"])
                sim_state["response_added"] = True

            tester.push_data("system_response", [np.round(sim_state["current"], 4)])

    from vizcore.widget_tester import WidgetTester

    tester = WidgetTester()

    # Pre-seed ONLY the step input
    tester.push_data("step_target", [0.0])

    line_plot = LinePlot(channels=1)  # Start with 1 channel capacity
    line_plot.bind_external_signal(tester.data_bus, ["step_target"])
    tester.set_widget(line_plot)
    tester.run(mock_update_fn=mock_update)
