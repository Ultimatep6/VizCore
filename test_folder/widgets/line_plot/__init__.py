import numpy as np

from widgets.widget_base import Widget
from components.axis_grid import AxisGrid
from components.legend import Legend
from settings import LEGEND_BG_ALPHA
from .settings import (
    PLOT_MARGIN,
    PLOT_LABEL_FONT_SCALE,
    PLOT_MAX_POINTS,
    PLOT_UI_SCALE_REF,
    LEGEND_HOVER_WIDTH_MIN,
    LEGEND_HOVER_CURSOR_GAP,
    LEGEND_HOVER_BOTTOM_PAD,
    LEGEND_RIGHT_PAD,
)


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

    def __init__(self, max_points=PLOT_MAX_POINTS, margin=PLOT_MARGIN):
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

        # Hover legend state
        self._hover_x = -1
        self._hover_y = -1
        self._hover_active = False

        # Font scales
        self.label_font_scale = PLOT_LABEL_FONT_SCALE

    def setup(self):
        """Called once. Creates AxisGrid, Legend, and pre-loads the line_plot shader."""
        self._grid = AxisGrid()
        self._legend = Legend(alpha=LEGEND_BG_ALPHA, right_pad=LEGEND_RIGHT_PAD)

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

    def teardown(self):
        """Detach all signals and clear all buffers."""
        for sig in list(self._bound_signals):
            self.detach_signal(sig)
        self._buffers.clear()
        self._bound_signals.clear()

    # --- Input ---

    def on_mouse_move(self, x, y):
        """Track cursor position for hover legend."""
        self._hover_x = x
        self._hover_y = y
        m = self._margin
        w, h = self.size
        self._hover_active = (m <= x <= w - m and m <= y <= h - m)

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
                try:
                    scalar = float(np.asarray(val).flat[0])
                except (TypeError, ValueError):
                    continue
                buf.push(scalar)
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
        Render the plot: axis grid, data lines, hover legend, axis labels.
        """
        w, h = self.size
        m = self._margin

        ui_scale = h / PLOT_UI_SCALE_REF
        plot_w = w - 2 * m
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
        try:
            for i, (name, buf) in enumerate(self._buffers.items()):
                color = self.COLORS[i % len(self.COLORS)]
                buf.draw(ui, self._tile_x + plot_x, self._tile_y + plot_y, plot_w, plot_h,
                         self.y_min, self.y_max, color)
        finally:
            ctx.scissor = None

        # 3. Hover legend (appears near cursor when hovering over plot area)
        if self._hover_active and self._buffers:
            entries = [(self._display_name(name), self.COLORS[i % len(self.COLORS)])
                       for i, (name, buf) in enumerate(self._buffers.items())]

            leg_w = max(LEGEND_HOVER_WIDTH_MIN, self._legend.suggest_width(entries))
            leg_h = len(entries) * self._legend.entry_height + LEGEND_HOVER_BOTTOM_PAD

            leg_x = self._hover_x + LEGEND_HOVER_CURSOR_GAP
            leg_y = self._hover_y + LEGEND_HOVER_CURSOR_GAP

            if leg_x + leg_w > w - m:
                leg_x = self._hover_x - leg_w - LEGEND_HOVER_CURSOR_GAP
            if leg_y + leg_h > h - m:
                leg_y = self._hover_y - leg_h - LEGEND_HOVER_CURSOR_GAP

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

            label_x = m - 5
            ui.text(f"{d_max:.1f}", label_x,
                    plot_y + max_y_off, scale=txt_scale, anchor_x="right")
            ui.text(f"{mid_y:.1f}", label_x,
                    plot_y + plot_h / 2, scale=txt_scale, anchor_x="right")
            ui.text(f"{d_min:.1f}", label_x,
                    plot_y + min_y_off, scale=txt_scale, anchor_x="right")

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
