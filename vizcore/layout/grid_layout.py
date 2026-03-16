class GridLayout:
    """
    Primary layout engine.

    Responsibilities:
        - Divide screen into cells
        - Assign widgets to cells
        - Compute widget rectangles

    Requirements:
        - Support resizing
        - Maintain widget proportions
    """
    def __init__(self, rows, cols, width, height):
        self.rows = rows
        self.cols = cols
        self.width = width
        self.height = height
        self.widgets = {}  # (row, col): widget

    def assign_widget(self, widget, row, col):
        self.widgets[(row, col)] = widget

    def compute_rect(self, row, col):
        cell_width = self.width / self.cols
        cell_height = self.height / self.rows
        x = col * cell_width
        y = row * cell_height
        return (x, y, cell_width, cell_height)

    def on_window_resize(self, width, height):
        self.width = width
        self.height = height
        # Optionally recompute widget rectangles or notify widgets

    def get_widget_rects(self):
        rects = {}
        for (row, col), widget in self.widgets.items():
            rects[widget] = self.compute_rect(row, col)
        return rects