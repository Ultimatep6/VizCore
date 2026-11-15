# Visualization settings for the GUI/widget system.
# All pixel values use fixed screen pixels (unscaled by ui_scale).

# ── Legend panel ──────────────────────────────────────────────────────────
# Background opacity of the legend panel in [0, 1].
LEGEND_BG_ALPHA = 0.85

# Background colour (r, g, b) of the legend panel.
LEGEND_BG_COLOR = (0.12, 0.12, 0.12)

# Border colour (r, g, b) of the legend panel.
LEGEND_BORDER_COLOR = (0.5, 0.5, 0.5)

# Text scale factor for legend signal labels.
LEGEND_FONT_SCALE = 0.5

# Vertical space in pixels per legend entry row.
LEGEND_ENTRY_HEIGHT = 25

# Colour-indicator swatch size in pixels.
LEGEND_SWATCH_SIZE = 14

# Pixels from the left edge of the legend box to the colour swatch.
LEGEND_LEFT_PAD = 10

# Pixels between the colour swatch and the text label.
LEGEND_SWATCH_TEXT_GAP = 6

# ── Widget line colours ──────────────────────────────────────────────────
# List of (r, g, b) colour tuples assigned cyclically to attached signals.
WIDGET_LINE_COLORS = [
    (0.2,  0.85, 0.2),    # Green
    (0.2,  0.5,  0.85),   # Blue
    (0.85, 0.2,  0.2),    # Red
    (0.85, 0.85, 0.2),    # Yellow
    (0.85, 0.2,  0.85),   # Magenta
    (0.2,  0.85, 0.85),   # Cyan
]
