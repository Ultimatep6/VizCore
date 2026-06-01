class Legend:
    """
    Reusable legend component for chart widgets.

    Draws a semi-transparent background panel, a border outline, and
    one coloured swatch + text label per entry.

    Usage in Widget.draw()::

        legend = Legend(alpha=0.85)
        legend.draw(ui, x, y, w, h, [
            ("sensors/imu/accel_x", (0.2, 0.85, 0.2)),
            ("sensors/imu/accel_y", (0.2, 0.5, 0.85)),
        ])
    """

    def __init__(
        self,
        alpha=0.85,
        bg_color=(0.12, 0.12, 0.12),
        border_color=(0.5, 0.5, 0.5),
        font_scale=0.5,
        entry_height=25,
        swatch_size=14,
    ):
        """
        Args:
            alpha: Background opacity in [0, 1].
            bg_color: (r, g, b) background colour.
            border_color: (r, g, b) border colour.
            font_scale: Text label scale factor.
            entry_height: Vertical space per legend entry in pixels.
            swatch_size: Colour indicator box size in pixels.
        """
        self.alpha = alpha
        self.bg_color = bg_color
        self.border_color = border_color
        self.font_scale = font_scale
        self.entry_height = entry_height
        self.swatch_size = swatch_size

    def draw(self, ui, x, y, w, h, entries):
        """
        Render the legend panel.

        Args:
            ui: DrawingContext from Widget.draw().
            x, y, w, h: Legend bounding box in pixel coords.
            entries: List of (display_label, (r, g, b)) pairs.
        """
        if not entries:
            return

        # Background panel
        ui.quad(x, y, w, h, self.bg_color, self.alpha)

        # Border
        ui.outline(x, y, w, h, self.border_color)

        # Per-entry swatch + label
        for i, (label, color) in enumerate(entries):
            swatch_y = y + h - self.entry_height - (i * self.entry_height)
            swatch_x = x + 18

            # Colour indicator box
            ui.quad(
                swatch_x,
                swatch_y,
                self.swatch_size,
                self.swatch_size,
                color,
            )

            # Text label
            text_x = swatch_x + self.swatch_size + 8
            text_y = swatch_y + 2
            ui.text(
                label,
                text_x,
                text_y,
                color=color,
                scale=self.font_scale,
            )
