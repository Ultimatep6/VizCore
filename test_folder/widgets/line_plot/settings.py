# LinePlot-specific settings.
# Shared settings (legend panel, line colours) are in the root settings.py.

# ── Plot area ─────────────────────────────────────────────────────────────
# Pixels between the tile edge and the plot area (for axis labels).
PLOT_MARGIN = 50

# Text scale factor for axis value labels.
PLOT_LABEL_FONT_SCALE = 0.6

# Maximum number of data points buffered per signal.
PLOT_MAX_POINTS = 1000

# Reference tile height for UI-scaling calculations.
# Scales = current_height / PLOT_UI_SCALE_REF.
PLOT_UI_SCALE_REF = 600.0

# ── Hover legend ──────────────────────────────────────────────────────────
# Minimum width in pixels of the hover-legend box (expands to fit text).
LEGEND_HOVER_WIDTH_MIN = 120

# Pixels between the end of the longest label text and the right box edge.
LEGEND_RIGHT_PAD = 20

# Pixels between the cursor position and the hover-legend edge.
LEGEND_HOVER_CURSOR_GAP = 12

# Extra padding in pixels at the bottom of the hover-legend box.
LEGEND_HOVER_BOTTOM_PAD = 8
