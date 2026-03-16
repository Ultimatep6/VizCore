import numpy as np
from vizcore.widgets.base_widget import BaseWidget
from vizcore.bus.ring_buffer import RingBuffer

class LinePlot(BaseWidget):
    """
    Scrolling line plot.

    Responsibilities:
        - Display time series signals
        - Maintain GPU ring buffer

    Features:
        - Multiple channels
        - Automatic scrolling
    """
    def __init__(self, rect, channels=1, buffer_size=512, margin=10):
        super().__init__(rect)
        self.channels = channels
        self.buffer_size = buffer_size
        self.buffers = [RingBuffer(buffer_size) for _ in range(channels)]
        self.values = [np.zeros(buffer_size, dtype='f4') for _ in range(channels)]
        self.margin = margin

    def update(self, data=None):
        # Pull latest values from the data bus for each signal
        if hasattr(self, 'signal_names') and hasattr(self, 'data_bus'):
            for i, name in enumerate(self.signal_names):
                value = self.data_bus.latest(name)
                if value is not None:
                    self.buffers[i].push(value)
                # Only update self.values if buffer has valid data
                self.values[i] = np.array(self.buffers[i].history(), dtype='f4')

    def draw(self, renderer):
        for i, values in enumerate(self.values):
            if len(values) < 2:
                continue
            x = np.linspace(-1.0, 1.0, len(values))
            v_min, v_max = np.min(values), np.max(values)
            y = 2.0 * (values - v_min) / (v_max - v_min + 1e-6) - 1.0
            points = np.column_stack((x, y)).flatten().astype('f4')
            renderer.draw_line_plot(
                points,
                rect=self.rect,
                color=(0, 150 + i*50, 255 - i*50, 255),
                margin = self.margin
            )

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