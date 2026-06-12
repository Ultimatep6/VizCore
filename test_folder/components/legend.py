from settings import (
    LEGEND_BG_ALPHA,
    LEGEND_BG_COLOR,
    LEGEND_BORDER_COLOR,
    LEGEND_FONT_SCALE,
    LEGEND_ENTRY_HEIGHT,
    LEGEND_SWATCH_SIZE,
    LEGEND_LEFT_PAD,
    LEGEND_SWATCH_TEXT_GAP,
)


class Legend:
    """
    Reusable legend component for chart widgets.

    Draws a semi-transparent background panel, a border outline, and
    one coloured swatch + text label per entry.

    Usage in Widget.draw()::

        legend = Legend()
        legend.draw(ui, x, y, w, h, [
            ("sensors/imu/accel_x", (0.2, 0.85, 0.2)),
            ("sensors/imu/accel_y", (0.2, 0.5, 0.85)),
        ])
    """

    def __init__(
        self,
        alpha=LEGEND_BG_ALPHA,
        bg_color=LEGEND_BG_COLOR,
        border_color=LEGEND_BORDER_COLOR,
        font_scale=LEGEND_FONT_SCALE,
        entry_height=LEGEND_ENTRY_HEIGHT,
        swatch_size=LEGEND_SWATCH_SIZE,
        left_pad=LEGEND_LEFT_PAD,
        swatch_text_gap=LEGEND_SWATCH_TEXT_GAP,
        right_pad=15,
    ):
        """
        Args:
            alpha: Background opacity in [0, 1].
            bg_color: (r, g, b) background colour.
            border_color: (r, g, b) border colour.
            font_scale: Text label scale factor.
            entry_height: Vertical space per legend entry in pixels.
            swatch_size: Colour indicator box size in pixels.
            left_pad: Pixels from left edge to colour swatch.
            swatch_text_gap: Pixels between colour swatch and text label.
            right_pad: Minimum pixels between end of text and right box edge.
        """
        self.alpha = alpha
        self.bg_color = bg_color
        self.border_color = border_color
        self.font_scale = font_scale
        self.entry_height = entry_height
        self.swatch_size = swatch_size
        self.left_pad = left_pad
        self.swatch_text_gap = swatch_text_gap
        self.right_pad = right_pad

    def suggest_width(self, entries):
        """
        Return the recommended box width in pixels for *entries*.

        Computes the width from the longest label so the right-pad
        margin is consistent regardless of text length.
        """
        if not entries:
            return 0
        text_start = self.left_pad + self.swatch_size + self.swatch_text_gap
        char_width = 14 * self.font_scale
        max_len = max(len(label) for label, _ in entries)
        return int(text_start + max_len * char_width + self.right_pad)

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
            swatch_x = x + self.left_pad

            # Colour indicator box
            ui.quad(
                swatch_x,
                swatch_y,
                self.swatch_size,
                self.swatch_size,
                color,
            )

            # Text label
            text_x = swatch_x + self.swatch_size + self.swatch_text_gap
            text_y = swatch_y + 2
            ui.text(
                label,
                text_x,
                text_y,
                color=color,
                scale=self.font_scale,
            )
