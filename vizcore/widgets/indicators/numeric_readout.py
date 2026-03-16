from vizcore.widgets.base_widget import BaseWidget

class NumericReadout(BaseWidget):
    """
    Displays numeric telemetry values.

    Responsibilities:
        - Show precise signal values

    Features:
        - Configurable precision
    """
    def __init__(self, rect, precision=2):
        super().__init__(rect)
        self.precision = precision
        self.value = None

    def update(self, data):
        self.value = data

    def draw(self, renderer):
        # Example: draw the value as text at the widget's rectangle
        text = f"{self.value:.{self.precision}f}" if self.value is not None else "--"
        renderer.draw_text(text, self.rect.x, self.rect.y, self.rect.width, self.rect.height)

    def resize(self, rect):
        super().resize(rect)