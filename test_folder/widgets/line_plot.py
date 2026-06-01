import numpy as np

from widget_base import Widget
from components.axis_grid import AxisGrid
from components.legend import Legend


class LinePlot(Widget):
    """
    A transparent line-plot widget for visualising 1D scalar signals.

    Composes AxisGrid, Legend, and per-signal LineBuffer instances.
    Supports auto-scaling Y range with smooth tracking.

    Signal display names in the legend use "/" as a path separator
    (e.g. "sensors/imu/accel_x") for readability.

    Class attributes:
        title: "Line Plot"
        transparent: True  (no solid background)
        required_shape: [(1,)]  (accepts only scalar-shaped signals)
    """

    title = "Line Plot"
    transparent = True
    required_shape = [(1,)]

    def __init__(self, max_points=1000, margin=50):
        """
        Args:
            max_points: Number of data points to buffer per signal.
            margin: Pixel margin around the plot area for axis labels.
        """
        super().__init__()
        self._max_points = max_points
        self._margin = margin

        # Per-signal storage: signal_name -> LineBuffer
        self._buffers = {}

        # Auto-scaling state
        self.y_min = -1.0
        self.y_max = 1.0
        self._data_min = None
        self._data_max = None
        self._smooth_min = None
        self._smooth_max = None

        # Reusable components (created in setup())
        self._grid = None
        self._legend = None

        # Legend dimensions
        self._legend_w = 200
        self._legend_h = 100
        self._legend_x_offset = 10
        self._legend_y_offset = 30

        # Font scales
        self.label_font_scale = 0.5
        self.legend_font_scale = 0.5

    def setup(self):
        """Called once. Creates AxisGrid, Legend, and pre-loads the line_plot shader."""
        self._grid = AxisGrid()
        self._legend = Legend(alpha=0.85, font_scale=self.legend_font_scale)

        # Force early loading of the line_plot shader
        if self._renderer is not None:
            from components.line_buffer import LineBuffer
            _dummy = LineBuffer(self._renderer, max_points=2)

    # --- Helpers ---

    def _display_name(self, signal_name):
        """Convert a dot-separated signal path to "/" notation for the legend."""
        return signal_name.replace(".", "/")

    # --- Signal lifecycle ---

    def on_attach_signal(self, signal_name):
        """Create a LineBuffer when a new signal is attached."""
        if signal_name not in self._buffers:
            buf = self.create_line_buffer(self._max_points)
            self._buffers[signal_name] = buf

    def on_detach_signal(self, signal_name):
        """Remove the LineBuffer when a signal is detached."""
        self._buffers.pop(signal_name, None)

    # --- Per-frame update ---

    def update(self):
        """
        Pull latest data for each bound signal and compute Y range
        from the full buffer contents.
        """
        if not self._buffers:
            return

        current_min = 1e30
        current_max = -1e30
        any_data = False

        for name, buf in self._buffers.items():
            val = self.read(name)
            if val is not None:
                buf.push(float(np.asarray(val).flat[0]))
                dmin, dmax = buf.range
                if dmin is not None:
                    any_data = True
                    if dmin < current_min:
                        current_min = dmin
                    if dmax > current_max:
                        current_max = dmax

        if not any_data:
            return

        self._data_min = current_min
        self._data_max = current_max

        padding = max(abs(current_max - current_min) * 0.1, 0.001)
        self.y_min = current_min - padding
        self.y_max = current_max + padding

    # --- Per-frame draw ---

    def draw(self, ui):
        """
        Render the plot: axis grid, data lines, legend, axis labels.
        """
        w, h = self.size
        m = self._margin

        # Compute layout
        ui_scale = h / 600.0
        leg_w = self._legend_w * ui_scale if self._buffers else 0
        leg_h = self._legend_h * ui_scale if self._buffers else 0

        plot_w = w - 2 * m - (leg_w + 30 * ui_scale)
        plot_h = h - 2 * m
        plot_x = m
        plot_y = m

        # 1. Axis grid
        self._grid.draw(
            ui, plot_x, plot_y, plot_w, plot_h,
            self.y_min, self.y_max,
            self._data_min, self._data_max,
        )

        # 2. Data lines (scissor-clipped to plot area)
        ctx = self._renderer.ctx
        ctx.scissor = (self._tile_x + int(plot_x),
                       self._tile_y + int(plot_y),
                       int(plot_w), int(plot_h))
        for i, (name, buf) in enumerate(self._buffers.items()):
            color = self.COLORS[i % len(self.COLORS)]
            buf.draw(ui, plot_x, plot_y, plot_w, plot_h,
                     self.y_min, self.y_max, color)
        ctx.scissor = None

        # 3. Legend
        if self._buffers:
            leg_x = w - m - leg_w - (self._legend_x_offset * ui_scale)
            leg_y = h - m - leg_h - (self._legend_y_offset * ui_scale)

            entries = []
            for i, (name, buf) in enumerate(self._buffers.items()):
                color = self.COLORS[i % len(self.COLORS)]
                entries.append((self._display_name(name), color))

            self._legend.draw(ui, leg_x, leg_y, leg_w, leg_h, entries)

        # 4. Axis value labels
        txt_scale = self.label_font_scale * ui_scale

        d_max = self._data_max if self._data_max is not None else self.y_max
        d_min = self._data_min if self._data_min is not None else self.y_min

        y_span = self.y_max - self.y_min
        if y_span != 0:
            max_y_off = (d_max - self.y_min) / y_span * plot_h
            min_y_off = (d_min - self.y_min) / y_span * plot_h
            mid_y = (d_max + d_min) / 2.0

            ui.text(f"{d_max:.1f}", m - 50 * txt_scale,
                    plot_y + max_y_off - 8 * txt_scale, scale=txt_scale)
            ui.text(f"{mid_y:.1f}", m - 50 * txt_scale,
                    plot_y + plot_h / 2 - 4 * txt_scale, scale=txt_scale)
            ui.text(f"{d_min:.1f}", m - 50 * txt_scale,
                    plot_y + min_y_off - 8 * txt_scale, scale=txt_scale)

    # --- Context menu ---

    def get_context_menu(self):
        """
        Return LinePlot-specific context menu entries.

        Adds "Attach Signal" (hierarchical tree of schema-compatible signals)
        and "Remove Signal" (one entry per bound signal).
        """
        entries = []

        compat = self.get_compatible_signals()
        if compat:
            entries.append(("Attach Signal", self._build_signal_tree(compat)))

        if self._bound_signals:
            remove_entries = []
            for path in self._bound_signals:
                display = self._display_name(path)
                remove_entries.append((
                    f"Remove {display}",
                    lambda p=path: self.detach_signal(p),
                ))
            entries.append(("Remove Signal", remove_entries))

        return entries
