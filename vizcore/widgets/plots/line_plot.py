import numpy as np
from vizcore.widgets.base_widget import BaseWidget
from vizcore.bus.ring_buffer import RingBuffer
from vizcore.layout.rect import Rect


TITLE_BAR_HEIGHT = 100  # pixels reserved at top for title
X_AXIS_LABEL_HEIGHT = 40  # pixels reserved at bottom for x-axis label
Y_AXIS_LABEL_WIDTH = 50   # pixels reserved at left for y-axis label

class LinePlot(BaseWidget):
    """
    Scrolling line plot.

    Responsibilities:
        - Display time series signals
        - Maintain GPU ring buffer

    Features:
        - Multiple channels
        - Automatic scrolling
        - Axis titles (x and y) with proper rotation
        - Title bar
    """
    def __init__(self, channels=1, buffer_size=512, margin=10, title=None, 
                 x_label=None, y_label=None):
        """
        Initialize LinePlot widget.
        
        Args:
            channels: Number of data channels to plot
            buffer_size: Size of ring buffer for each channel
            margin: Margin around plot area in pixels
            title: Title text displayed at top of widget
            x_label: Label for X-axis (horizontal, centered at bottom)
            y_label: Label for Y-axis (vertical, rotated 90°, centered on left)
        """
        super().__init__()
        self.channels = channels
        self.buffer_size = buffer_size
        self.margin = margin
        self.title = title
        self.x_label = x_label
        self.y_label = y_label
        self.buffers = [RingBuffer(buffer_size) for _ in range(channels)]
        self.values = [np.zeros(buffer_size, dtype='f4') for _ in range(channels)]
        self._vbos = {}

    def bind_renderer(self, renderer):
        """Call once after widget is created to pre-allocate GPU buffers."""
        for i in range(self.channels):
            points = np.zeros(self.buffer_size * 2, dtype='f4')  # x,y interleaved
            self._vbos[i] = renderer.ctx.buffer(points.tobytes())

    def update(self, data=None):
        # Pull latest values from the data bus for each signal
        if hasattr(self, 'signal_names') and hasattr(self, 'data_bus'):
            for i, name in enumerate(self.signal_names):
                value = self.data_bus.latest(name)
                if value is not None:
                    self.buffers[i].push(value)
                # Only update self.values if buffer has valid data
                self.values[i] = np.array(self.buffers[i].history(), dtype='f4')

    def draw_lines(self, renderer):
        for i, values in enumerate(self.values):
            if len(values) < 2:
                continue

            # Normalize values to [-1, 1] for plotting, and create interleaved x,y points
            x = np.linspace(-1.0, 1.0, len(values))
            v_min, v_max = np.min(values), np.max(values)
            y = 2.0 * (values - v_min) / (v_max - v_min + 1e-6) - 1.0
            points = np.column_stack((x, y)).flatten().astype('f4')

            # Calculate plot area, accounting for title and axis labels
            top_padding = TITLE_BAR_HEIGHT if self.title else 0
            bottom_padding = X_AXIS_LABEL_HEIGHT if self.x_label else 0
            left_padding = Y_AXIS_LABEL_WIDTH if self.y_label else 0
            
            # Define the rectangle for the line plot area
            plot_rect = Rect(
                self.rect.x + left_padding,
                self.rect.y + bottom_padding,
                self.rect.width - left_padding,
                self.rect.height - top_padding - bottom_padding
            )

            # Send to GPU and draw using renderer
            if i in self._vbos:
                self._vbos[i].write(points.tobytes())
                renderer.draw_line_plot_vbo(
                    self._vbos[i], len(points) // 2,
                    rect=plot_rect, color=(0, 150 + i*50, 255 - i*50, 255),
                    margin=self.margin
                )
            else:
                renderer.draw_line_plot(
                    points, rect=plot_rect,
                    color=(0, 150 + i*50, 255 - i*50, 255),
                    margin=self.margin
                )

    def draw_text(self, renderer):
        if not self.rect:
            return
            
        # Draw title at top
        if self.title:
            cx = self.rect.x + self.rect.width // 2
            y = self.rect.y + self.rect.height - 40
            tw, th = renderer.text_title.measure(self.title)
            pad = 6
            # Dark background box behind title
            renderer.draw_rect(
                cx - tw // 2 - pad, y - pad,
                tw + pad * 2, th + pad * 2,
                color=(0.1, 0.1, 0.1, 1.0)
            )
            renderer.draw_title(self.title, cx, y)

        # Draw X-axis label at bottom center
        if self.x_label:
            cx = self.rect.x + self.rect.width // 2
            y = self.rect.y + 10  # 10 pixels from bottom
            renderer.draw_text_centered(self.x_label, cx, y)

        # Draw Y-axis label on left side (rotated 90 degrees)
        if self.y_label:
            # Position at vertical center of the widget
            cy = self.rect.y + self.rect.height // 2
            x = self.rect.x + 15  # 15 pixels from left edge
            
            # Draw rotated text (90 degrees counterclockwise)
            renderer.draw_axis_label_y(self.y_label, x, cy)

    def draw(self, renderer):
        self.draw_lines(renderer)
        self.draw_text(renderer)

    def resize(self, rect):
        super().resize(rect)

    def bind_signal(self, data_bus, signal):
        """
        Bind this plot to one or more signals from the data bus.
        Accepts a single signal name (str) or a list of signal names.
        """
        if isinstance(signal, str):
            self.signal_names = [signal]
        else:
            self.signal_names = list(signal)
        self.data_bus = data_bus