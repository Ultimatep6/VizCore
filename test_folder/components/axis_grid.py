class AxisGrid:
    """
    Reusable 2D axis grid for chart widgets.

    Draws a bounding rectangle, a zero-line (if the Y range crosses
    zero), and optional dotted data-marker lines at the current data
    extents.

    Usage in Widget.draw()::

        grid = AxisGrid()
        grid.draw(ui, x, y, w, h, y_min, y_max, data_min, data_max)
    """

    def __init__(
        self,
        border_color=(0.8, 0.8, 0.8),
        zero_color=(0.5, 0.5, 0.5),
        marker_color=(0.4, 0.4, 0.4),
        line_thickness=1.0,
    ):
        """
        Args:
            border_color: (r, g, b) colour for the plot bounding box.
            zero_color: (r, g, b) colour for the zero reference line.
            marker_color: (r, g, b) colour for data-extent marker lines.
            line_thickness: Thickness of axis lines in pixels.
        """
        self.border_color = border_color
        self.zero_color = zero_color
        self.marker_color = marker_color
        self.line_thickness = line_thickness

    def draw(self, ui, x, y, w, h, y_min, y_max, data_min=None, data_max=None):
        """
        Render the axis grid.

        Args:
            ui: DrawingContext from Widget.draw().
            x, y, w, h: Plot region bounding box in pixel coords.
            y_min, y_max: Full Y-axis range (used for zero-line).
            data_min, data_max: Current data extents for marker lines
                (optional — pass None to skip markers).
        """
        # Bounding box: bottom, top, left, right edges
        t = self.line_thickness
        ui.h_line(y, x, x + w, self.border_color, thickness=t)           # bottom
        ui.h_line(y + h, x, x + w, self.border_color, thickness=t)       # top
        ui.v_line(x, y, y + h, self.border_color, thickness=t)           # left
        ui.v_line(x + w, y, y + h, self.border_color, thickness=t)       # right

        # Zero line (if zero is within the visible range)
        y_span = y_max - y_min
        if y_span != 0 and y_min <= 0.0 <= y_max:
            zero_norm = (0.0 - y_min) / y_span
            zero_px = y + zero_norm * h
            ui.h_line(zero_px, x, x + w, self.zero_color, alpha=0.7, thickness=t)

        # Data extents marker lines (dotted appearance via alpha)
        if data_min is not None and data_max is not None and y_span != 0:
            for val, label in [(data_max, "max"), (data_min, "min")]:
                if y_min <= val <= y_max:
                    norm = (val - y_min) / y_span
                    px = y + norm * h
                    ui.h_line(px, x, x + w, self.marker_color, alpha=0.4, thickness=t)
